import os
import sys
import nvidia.cublas
import nvidia.cudnn
import nvidia.cuda_runtime
from faster_whisper import WhisperModel
from tqdm import tqdm

if sys.platform == "win32":
    cuda_dll_dirs = [
        os.path.join(list(nvidia.cublas.__path__)[0], "bin"),
        os.path.join(list(nvidia.cudnn.__path__)[0], "bin"),
        os.path.join(list(nvidia.cuda_runtime.__path__)[0], "bin"),
    ]
    os.environ["PATH"] = os.pathsep.join(cuda_dll_dirs) + os.pathsep + os.environ["PATH"]

MODEL_SIZE = "large-v3-turbo"


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
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"[{minutes:02d}:{remaining_seconds:02d}]"


def transcribe_audio(audio_path, output_path, progress_callback=None):
    """
    This function is about loading Whisper Large v3 Turbo and transcribing a WAV file to text.
    The variable used in this code are:
    audio_path: path to the WAV file to transcribe
    output_path: path where the transcript text file will be saved
    progress_callback: optional function called with a 0-100 float as transcription progresses;
    if not given, a tqdm progress bar is printed to the console instead

    The flow process of this codes are as follows:
    1. Load the faster-whisper large-v3-turbo model (GPU, float16 compute type)
    2. Run transcription on the audio file, tracking total duration
    3. Prefix each segment's text with its [mm:ss] start timestamp, reporting 0-100% progress
    4. Write the full transcript to output_path

    The result of this function are as follows:
    transcript: the full transcribed text
    output_path: the path of the saved transcript file
    """
    print("Loading model (downloads on first run, then cached)...")
    model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
    print("Model loaded. Running transcription...")

    segments, info = model.transcribe(audio_path, vad_filter=True, condition_on_previous_text=False)
    total_duration = round(info.duration) or 1

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

    transcript = "\n".join(transcript_parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    print("Transcription finished.")

    return transcript, output_path
