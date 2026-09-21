import os
import sys
from faster_whisper import WhisperModel
from tqdm import tqdm

try:
    import nvidia.cublas
    import nvidia.cudnn
    import nvidia.cuda_runtime
    NVIDIA_PACKAGES_AVAILABLE = True
except ImportError:
    # not installed on a CPU-only build — GPU transcription simply won't be offered
    NVIDIA_PACKAGES_AVAILABLE = False

if NVIDIA_PACKAGES_AVAILABLE and sys.platform == "win32":
    cuda_dll_dirs = [
        os.path.join(list(nvidia.cublas.__path__)[0], "bin"),
        os.path.join(list(nvidia.cudnn.__path__)[0], "bin"),
        os.path.join(list(nvidia.cuda_runtime.__path__)[0], "bin"),
    ]
    os.environ["PATH"] = os.pathsep.join(cuda_dll_dirs) + os.pathsep + os.environ["PATH"]

MODEL_SIZE = "large-v3-turbo"


def is_gpu_available():
    """
    This function is about checking whether a usable NVIDIA GPU is available for transcription.
    The variable used in this code are:
    (none)

    The flow process of this codes are as follows:
    1. If the CUDA runtime pip packages aren't installed (e.g. CPU-only build), report unavailable
    2. Otherwise ask ctranslate2 how many CUDA devices it can see

    The result of this function are as follows:
    available: True if a CUDA-capable GPU with the required runtime libraries is usable
    """

    # 1. If the CUDA runtime pip packages aren't installed, GPU is not usable regardless of hardware
    if not NVIDIA_PACKAGES_AVAILABLE:
        return False

    # 2. Otherwise ask ctranslate2 how many CUDA devices it can see
    import ctranslate2
    return ctranslate2.get_cuda_device_count() > 0


def format_timestamp(seconds):
    """
    This function is about converting seconds into a [mm:ss] timestamp string.
    The variable used in this code are:
    seconds: time in seconds (float) to convert

    The flow process of this codes are as follows:
    1. Split seconds into whole minutes and remaining seconds
    2. Format both as zero-padded 2-digit numbers

    The result of this function are as follows:
    timestamp: string in [mm:ss] format
    """

    # 1. Split seconds into whole minutes and remaining seconds
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)

    # 2. Format both as zero-padded 2-digit numbers
    return f"[{minutes:02d}:{remaining_seconds:02d}]"


def _run_pass(model, audio_path, vad_filter, progress_callback):
    """
    This function is about running one transcription pass and collecting its timestamped lines.
    The variable used in this code are:
    model: loaded WhisperModel instance
    audio_path: path to the audio file to transcribe
    vad_filter: whether to use Silero VAD to skip non-speech audio before transcribing
    progress_callback: optional function called with a 0-100 float as transcription progresses;
    if not given, a tqdm progress bar is printed to the console instead

    The flow process of this codes are as follows:
    1. Run model.transcribe with the given vad_filter setting, tracking total duration
    2. Prefix each segment's text with its [mm:ss] start timestamp, reporting 0-100% progress

    The result of this function are as follows:
    transcript_parts: list of "[mm:ss] text" lines, one per segment (empty if no speech found)
    """

    # 1. Run model.transcribe with the given vad_filter setting, tracking total duration
    segments, info = model.transcribe(audio_path, vad_filter=vad_filter, condition_on_previous_text=False)
    total_duration = round(info.duration) or 1

    # 2. Prefix each segment's text with its [mm:ss] start timestamp, reporting 0-100% progress
    transcript_parts = []
    pbar = None if progress_callback else tqdm(total=total_duration, unit="s", desc="Transcribing")

    for segment in segments:
        line = f"{format_timestamp(segment.start)} {segment.text.strip()}"
        transcript_parts.append(line)
        current = round(segment.end)
        if progress_callback:
            progress_callback(min(100.0, (current / total_duration) * 100.0))
        else:
            pbar.update(current - pbar.n)

    if pbar:
        pbar.close()
    elif progress_callback:
        progress_callback(100.0)

    return transcript_parts


def transcribe_audio(audio_path, output_path, progress_callback=None, device="auto"):
    """
    This function is about loading Whisper Large v3 Turbo and transcribing a WAV file to text.
    The variable used in this code are:
    audio_path: path to the WAV file to transcribe
    output_path: path where the transcript text file will be saved
    progress_callback: optional function called with a 0-100 float as transcription progresses;
    if not given, a tqdm progress bar is printed to the console instead
    device: "auto" (use GPU if available, else CPU), "cuda", or "cpu"

    The flow process of this codes are as follows:
    1. Resolve "auto" to an actual device, then load the model (GPU uses float16, CPU uses
       int8), falling back to CPU if GPU loading fails for any reason
    2. Run a first pass with vad_filter=True (measured best setting for normal speech)
    3. If that pass found no speech at all (e.g. singing, which Silero VAD often misses),
       retry once with vad_filter=False so content isn't silently lost — this retry can
       hallucinate text on true silence, so the caller is told via used_fallback
    4. Write the full transcript to output_path

    The result of this function are as follows:
    transcript: the full transcribed text
    output_path: the path of the saved transcript file
    used_fallback: True if the vad_filter=False retry was needed to get any text
    """

    # 1. Resolve "auto" to an actual device, then load the model with a CPU fallback
    if device == "auto":
        device = "cuda" if is_gpu_available() else "cpu"

    print(f"Loading model on {device} (downloads on first run, then cached)...")
    try:
        compute_type = "float16" if device == "cuda" else "int8"
        model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute_type)
    except Exception as e:
        if device != "cuda":
            raise
        print(f"GPU load failed ({e}). Falling back to CPU...")
        device = "cpu"
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    print("Model loaded. Running transcription...")

    # 2. Run a first pass with vad_filter=True (measured best setting for normal speech)
    transcript_parts = _run_pass(model, audio_path, vad_filter=True, progress_callback=progress_callback)
    used_fallback = False

    # 3. If no speech was found at all, retry once with vad_filter=False
    if not transcript_parts:
        print("No speech detected with VAD on. Retrying with VAD off...")
        transcript_parts = _run_pass(model, audio_path, vad_filter=False, progress_callback=progress_callback)
        used_fallback = True

    # 4. Write the full transcript to output_path
    transcript = "\n".join(transcript_parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    print("Transcription finished.")

    return transcript, output_path, used_fallback
