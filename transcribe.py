import os
import shutil
import sys

# must be set before huggingface_hub is imported: error out after 5 min with no bytes received
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "300")

from faster_whisper import WhisperModel
from faster_whisper.utils import download_model
from huggingface_hub.constants import HF_HUB_CACHE
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
MIN_FREE_GB = 2


class ModelSetupError(Exception):
    """Raised when the model can't be downloaded; the message is already user-friendly."""


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


def is_model_cached():
    """
    This function is about checking whether the Whisper model is already downloaded locally.
    The variable used in this code are:
    (none)

    The flow process of this codes are as follows:
    1. Ask faster-whisper to resolve the model with local_files_only=True (no network access)
    2. If that succeeds, everything needed is already on disk; if it raises, a download is needed

    The result of this function are as follows:
    cached: True if the model can be loaded without downloading anything
    """
    # 1. Ask faster-whisper to resolve the model using only local files
    try:
        download_model(MODEL_SIZE, local_files_only=True)
        return True
    except Exception:
        # 2. Any failure here means the model isn't fully cached yet
        return False


def has_enough_disk_space():
    """
    This function is about checking whether the model cache drive has enough free space.
    The variable used in this code are:
    (none)

    The flow process of this codes are as follows:
    1. Make sure the cache folder exists so its drive can be measured
    2. Read the free space on that drive and compare it with MIN_FREE_GB

    The result of this function are as follows:
    enough: True if at least MIN_FREE_GB is free
    free_gb: the free space in GB
    """

    # 1. Make sure the cache folder exists
    os.makedirs(HF_HUB_CACHE, exist_ok=True)

    # 2. Read the free space and compare it with the minimum
    free_gb = shutil.disk_usage(HF_HUB_CACHE).free / 1024**3
    return free_gb >= MIN_FREE_GB, free_gb


def download_model_files():
    """
    This function is about downloading the Whisper model with clear errors for the user.
    The variable used in this code are:
    (none)

    The flow process of this codes are as follows:
    1. Stop with a friendly error if the cache drive has less than MIN_FREE_GB free
    2. Download the model, turning any connection or timeout failure into a friendly error

    The result of this function are as follows:
    (none, raises ModelSetupError on failure)
    """

    # 1. Stop if there is not enough free disk space
    enough, free_gb = has_enough_disk_space()
    if not enough:
        drive = os.path.splitdrive(HF_HUB_CACHE)[0] or HF_HUB_CACHE
        raise ModelSetupError(
            f"Not enough disk space: {MIN_FREE_GB}GB needed, {free_gb:.1f}GB free on {drive}. "
            "Free up space, then try again."
        )

    # 2. Download the model, turning any failure into a friendly error
    try:
        download_model(MODEL_SIZE)
    except Exception as e:
        raise ModelSetupError(
            f"Download failed or stalled. Check your internet connection, then try again. ({type(e).__name__})"
        ) from e


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


def transcribe_audio(audio_path, output_path, progress_callback=None, device="auto", status_callback=None):
    """
    This function is about loading Whisper Large v3 Turbo and transcribing a WAV file to text.
    The variable used in this code are:
    audio_path: path to the WAV file to transcribe
    output_path: path where the transcript text file will be saved
    progress_callback: optional function called with a 0-100 float as transcription progresses;
    if not given, a tqdm progress bar is printed to the console instead
    device: "auto" (use GPU if available, else CPU), "cuda", or "cpu"
    status_callback: optional function called with a short text message when the current phase
    changes (e.g. model loading vs. transcribing) — lets a GUI show what's happening during the
    model-loading step, which can take minutes on first run (~1.6GB download) with no progress
    percentage available; falls back to printing to the console if not given

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
    def report_status(message):
        if status_callback:
            status_callback(message)
        else:
            print(message)

    # 1. Resolve "auto" to an actual device, then load the model with a CPU fallback
    if device == "auto":
        device = "cuda" if is_gpu_available() else "cpu"

    device_name = "GPU" if device == "cuda" else "CPU"
    if is_model_cached():
        report_status(f"Loading model on {device_name} from {HF_HUB_CACHE}...")
    else:
        report_status(f"Downloading model (~1.6GB) to {HF_HUB_CACHE}...")
        download_model_files()
    try:
        compute_type = "float16" if device == "cuda" else "int8"
        model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute_type)
    except Exception as e:
        if device != "cuda":
            raise
        report_status(f"GPU load failed ({e}). Falling back to CPU...")
        device = "cpu"
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    report_status("Model loaded. Running transcription...")

    # 2. Run a first pass with vad_filter=True (measured best setting for normal speech)
    transcript_parts = _run_pass(model, audio_path, vad_filter=True, progress_callback=progress_callback)
    used_fallback = False

    # 3. If no speech was found at all, retry once with vad_filter=False
    if not transcript_parts:
        report_status("No speech detected with VAD on. Retrying with VAD off...")
        transcript_parts = _run_pass(model, audio_path, vad_filter=False, progress_callback=progress_callback)
        used_fallback = True

    # 4. Write the full transcript to output_path
    transcript = "\n".join(transcript_parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    print("Transcription finished.")

    return transcript, output_path, used_fallback
