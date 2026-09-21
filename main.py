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
    4. Transcribe the WAV file, saving the transcript to the text path (retries without VAD if
       the first pass found no speech at all, e.g. singing)
    5. If the transcript file has content, convert the WAV to a smaller MP3 and delete the WAV

    The result of this function are as follows:
    (none, prints progress and file locations to the console)
    """

    # 1. Create a date folder containing a timestamped session folder
    date_str = datetime.now().strftime("%Y%m%d")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(OUTPUT_DIR, date_str, timestamp)
    os.makedirs(session_dir, exist_ok=True)

    # 2. Build timestamp-prefixed WAV and transcript file paths
    wav_path = os.path.join(session_dir, f"{timestamp}_recording.wav")
    mp3_path = os.path.join(session_dir, f"{timestamp}_recording.mp3")
    txt_path = os.path.join(session_dir, f"{timestamp}_transcript.txt")

    # 3. Record system audio until Ctrl+C, saving to the WAV path
    record_system_audio(wav_path)
    print(f"Saved recording to: {wav_path}")

    # 4. Transcribe the WAV file, saving the transcript (retries without VAD if empty)
    print("Transcribing...")
    _, saved_txt_path, used_fallback = transcribe_audio(wav_path, txt_path)
    print(f"Saved transcript to: {saved_txt_path}")

    with open(saved_txt_path, "r", encoding="utf-8") as f:
        transcript_content = f.read().strip()

    # 5. If the transcript has content, convert the WAV to MP3 and delete the WAV
    if transcript_content:
        convert_wav_to_mp3(wav_path, mp3_path)
        os.remove(wav_path)
        if used_fallback:
            print(f"Recovered without VAD (please verify accuracy — silence can hallucinate). Saved MP3 and deleted WAV: {mp3_path}")
        else:
            print(f"Transcript verified non-empty. Saved MP3 and deleted WAV: {mp3_path}")
    else:
        print(f"No speech detected even without VAD. Keeping WAV file: {wav_path}")


if __name__ == "__main__":
    main()
