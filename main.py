import os
import warnings
from datetime import datetime
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

from record_audio import record_system_audio, convert_wav_to_mp3
from transcribe import transcribe_audio

OUTPUT_DIR = "output"


def main():
    """
    This function is about running the full pipeline: record system audio, then transcribe it.
    The variable used in this code are:
    (none)

    The flow process of this codes are as follows:
    1. Create a date folder containing a timestamped session folder under the output folder
    2. Build timestamp-prefixed WAV and transcript file paths inside that session folder
    3. Record system audio until Ctrl+C, saving to the WAV path (best quality for transcription)
    4. Transcribe the WAV file, saving the transcript to the text path
    5. If the transcript file has content, convert the WAV to a smaller MP3 and delete the WAV

    The result of this function are as follows:
    (none, prints progress and file locations to the console)
    """
    date_str = datetime.now().strftime("%Y%m%d")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(OUTPUT_DIR, date_str, timestamp)
    os.makedirs(session_dir, exist_ok=True)

    wav_path = os.path.join(session_dir, f"{timestamp}_recording.wav")
    mp3_path = os.path.join(session_dir, f"{timestamp}_recording.mp3")
    txt_path = os.path.join(session_dir, f"{timestamp}_transcript.txt")

    record_system_audio(wav_path)
    print(f"Saved recording to: {wav_path}")

    print("Transcribing...")
    _, saved_txt_path = transcribe_audio(wav_path, txt_path)
    print(f"Saved transcript to: {saved_txt_path}")

    with open(saved_txt_path, "r", encoding="utf-8") as f:
        transcript_content = f.read().strip()

    if transcript_content:
        convert_wav_to_mp3(wav_path, mp3_path)
        os.remove(wav_path)
        print(f"Transcript verified non-empty. Saved MP3 and deleted WAV: {mp3_path}")
    else:
        print(f"Transcript is empty. Keeping WAV file: {wav_path}")


if __name__ == "__main__":
    main()
