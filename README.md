# Audio Transcriber
A local Windows desktop tool that records system/speaker audio (Google Meet, Teams, Slack huddles, YouTube — anything playing through your speakers) and transcribes it with Whisper. Uses GPU automatically when available, falls back to CPU otherwise. Runs as a one-click GUI or a CLI, with no data leaving your machine.

![Python Version](https://img.shields.io/badge/python-3.11-blue)
![Platform](https://img.shields.io/badge/platform-windows-lightgrey)
![GPU](https://img.shields.io/badge/GPU-optional-76B900)

# Table of content

- [For Users](#for-users)
  - [Apps Features](#apps-features)
  - [How to Use the Apps](#how-to-use-the-apps)
  - [A Note on Antivirus Warnings](#a-note-on-antivirus-warnings)
- [For Developers](#for-developers)
  - [Project Structure](#project-structure)
  - [Getting Started](#getting-started)
  - [Code Explanation](#code-explanation)
  - [Run the project locally](#run-the-project-locally)
  - [Create a Desktop Shortcut](#create-a-desktop-shortcut)
  - [Contributors](#contributors)


# For Users

## Apps Features

The application consists of five main features.

### 1. System Audio Recording
Records whatever plays through your speakers via WASAPI loopback — Meet, Teams, Slack huddles, YouTube, any app. Does **not** record your microphone.

### 2. GPU-Accelerated Transcription, with CPU Fallback
Transcribes with `faster-whisper` (`large-v3-turbo`). Uses your NVIDIA GPU automatically when one is detected, otherwise runs on CPU — no setup needed either way. If a GPU is available, the GUI shows a GPU/CPU toggle so you can pick manually. A live 0–100% progress bar tracks transcription either way.

### 3. One-Click Desktop GUI
A small popup window (`gui.py`) — Start/Stop button, live elapsed timer, progress bar, and the saved file location. No terminal required once set up.

### 4. Timestamped Transcripts
Every line is tagged with a `[mm:ss]` timestamp matching the recording.

### 5. Small Storage Footprint
Recordings are saved as 64kbps mono MP3 (not raw WAV) — roughly 480KB per minute — auto-deleted-and-replaced right after a successful transcript.


## How to use the Apps

### For non-technical users (easiest way)
No coding or setup needed — just these steps:

1. [**Download AudioTranscriber-CPU.zip**](https://github.com/nugrahazikry/simple-audio-transciber/releases/latest/download/AudioTranscriber-CPU.zip) (~90MB).
2. Right-click the downloaded zip → **Extract All**, then open the extracted folder.
3. Double-click `AudioTranscriber-CPU.exe` inside it. A small window titled "Audio Transcriber" pops up — nothing to install.
4. Click **Start Recording**, then let your meeting or video play.
5. Click **Stop** when finished — it transcribes automatically, no further clicks needed.
6. Once it shows **Done**, the "Last saved" text tells you where your transcript was saved.

> If Windows SmartScreen or your antivirus flags the exe, this is a known false positive with unsigned PyInstaller-built apps, not an actual virus — click **More info → Run anyway**, or see [this note](#a-note-on-antivirus-warnings) below.

The steps below are for running the app from source code instead (for developers).

### Step 1 — Complete the setup
Follow [Getting Started](#getting-started) below to install dependencies.

### Step 2 — Launch the app
Run `python gui.py` (or double-click your [desktop shortcut](#create-a-desktop-shortcut) once set up).

### Step 3 — Record
Click **Start Recording**. Let the meeting/video play — the elapsed timer counts up live.

### Step 4 — Stop and transcribe
Click **Stop**. Transcription starts automatically; the progress bar fills as it runs.

### Step 5 — Get your transcript
Once status shows **Done**, the "Last saved" path points to `output/<date>/<timestamp>/`, containing the `.mp3` and `.txt` transcript.


## A Note on Antivirus Warnings

Windows SmartScreen or your antivirus may flag `AudioTranscriber-CPU.exe` as a virus or "potentially unwanted software." **This is a known false positive**, not an actual detection of malicious code.

**Why it happens:** the exe is built with PyInstaller, which bundles Python and all dependencies into a single file that unpacks and runs itself from a temp folder at launch. That "unpack and execute from temp" pattern is also how real malware droppers behave, so antivirus heuristics flag it generically. The exe isn't code-signed (that costs money and isn't worth it for a small hobby tool), so it has no trust reputation built up either, which makes heuristic engines more cautious by default.

**To run it anyway:**
- If SmartScreen blocks it: click **More info** → **Run anyway**.
- If Windows Defender quarantines it: open **Windows Security** → **Virus & threat protection** → **Protection history**, find the entry, and click **Actions → Allow** (or **Restore**).

If you'd rather verify the source first, every line of this project is open in this repository — nothing is hidden or obfuscated.


# For Developers

## Project Structure
```
audio transciption/
├── main.py              # CLI entry point (Ctrl+C to stop)
├── gui.py                # GUI entry point (tkinter)
├── record_audio.py       # WASAPI loopback recording + WAV-to-MP3 conversion
├── transcribe.py         # faster-whisper transcription (GPU if available, else CPU)
├── requirements.txt      # Python dependencies
├── .env                  # HF_TOKEN — not committed
├── .gitignore
├── README.md
├── venv/                 # virtual environment — not committed
└── output/               # generated recordings & transcripts — not committed
    └── <date>/
        └── <timestamp>/
            ├── <timestamp>_recording.mp3
            └── <timestamp>_transcript.txt
```

## Getting started

### Dependencies and Prerequisites

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.11 | Runtime language |
| faster-whisper | latest | Whisper transcription engine (GPU via ctranslate2) |
| PyAudioWPatch | latest | WASAPI loopback audio recording |
| lameenc | latest | Pure-Python MP3 encoding (no ffmpeg needed) |
| numpy | latest | Audio sample handling (stereo-to-mono downmix) |
| python-dotenv | latest | Loads an optional `HF_TOKEN` from `.env`, if present |
| tqdm | latest | CLI progress bars |
| nvidia-cublas-cu12, nvidia-cudnn-cu12, nvidia-cuda-runtime-cu12 | latest | CUDA runtime libraries — only used if a GPU is detected |
| NVIDIA GPU | CUDA-capable (optional) | Used automatically if present for faster transcription (tested on RTX 3050 Laptop, 4GB VRAM); the app runs fine on CPU otherwise |

### Tech stack

| Layer | Tech stack |
|---|---|
| Audio capture | PyAudioWPatch (WASAPI loopback) |
| Speech-to-text | faster-whisper (`large-v3-turbo`), GPU (float16) or CPU (int8), auto-detected |
| Audio encoding | lameenc (MP3, 64kbps mono) |
| GUI | tkinter (stdlib) |
| Model hosting | Hugging Face Hub (auto-downloaded, cached locally) |

### Model download

The `large-v3-turbo` model downloads automatically the first time you transcribe anything, and is cached afterward — no manual step needed for most people.

If downloads are slow or rate-limited, you can optionally speed them up with a free Hugging Face token: create a `.env` file in the project root with `HF_TOKEN=your_token_here` (get one at [huggingface.co](https://huggingface.co/) → Settings → Access Tokens). This is purely a download-speed optimization, not a requirement to run the app.

> ⚠️ **Never commit your `.env` file.** It's already listed in `.gitignore`.


## Code explanation

### Key files

| Category | File | Description |
|---|---|---|
| Recording | `record_audio.py` | Opens the default WASAPI loopback device, records until stopped (via `stop_event` or Ctrl+C), and converts the result to a small mono MP3 |
| Transcription | `transcribe.py` | Auto-detects a usable GPU (`is_gpu_available()`) and loads `faster-whisper` on GPU or CPU accordingly, with a live fallback to CPU if GPU loading fails; transcribes with tuned settings (`vad_filter=True`, `condition_on_previous_text=False` — measured best after testing 7+ configurations) |
| CLI entry point | `main.py` | Runs record → transcribe → convert-to-MP3 in sequence, controlled via Ctrl+C |
| GUI entry point | `gui.py` | tkinter popup; runs recording/transcription on background threads, coordinated via `queue.Queue` + `root.after()` polling |


## Run the project locally

**Prerequisites:** Python 3.11. An NVIDIA GPU is optional — used automatically if present, CPU otherwise.

**1. Create and activate a virtual environment:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**2. Install dependencies:**
```powershell
pip install -r requirements.txt
```

**3. Download the `large-v3-turbo` model (~1.6GB):**

Happens automatically the first time you transcribe anything — no manual step needed. To pre-download it instead of waiting on first use, run:
```powershell
python -c "from faster_whisper import WhisperModel; WhisperModel('large-v3-turbo', device='cpu')"
```
This saves the model to `~/.cache/huggingface/hub/`, where every future run loads it from instantly, offline, with no re-download.

**4. Run the GUI:**
```powershell
python gui.py
```
Or the CLI:
```powershell
python main.py
```


## Create a Desktop Shortcut

For one-click launch without opening a terminal:

1. Right-click your Desktop → **New → Shortcut**.
2. Target: `<project path>\venv\Scripts\pythonw.exe "<project path>\gui.py"`
3. Start in: `<project path>`
4. Name it "Audio Transcriber" and finish.

`pythonw.exe` runs the script windowlessly (no console flash), reusing your existing `venv` — no separate packaging needed.


## Contributors
Contributors names and contact info:
1. **[Zikry Adjie Nugraha](https://github.com/nugrahazikry)**: Sole developer — built the full application including WASAPI loopback recording, GPU-accelerated transcription pipeline, MP3 conversion, and the tkinter desktop GUI.
