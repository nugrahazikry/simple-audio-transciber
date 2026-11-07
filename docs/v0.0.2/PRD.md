# PRD — Audio Transcriber v0.0.2

Source: `complaints_2.md` (5 client complaints). Status updated 2026-11-07: see the Status column (🚀 counts as done).

## Overview

- Local Windows tool that records speaker audio (WASAPI loopback) and transcribes it with Whisper (`README.md` l.2, `record_audio.py: record_system_audio`).
- v0.0.2 addresses 5 client complaints: speed, sharpness, mic recording, voice on/off button, waveform.
- Version: the code said `VERSION = "1.0.1"` (GitHub's latest release is also 1.0.1). The owner tried `0.0.2`, then chose to keep `1.0.1` (`gui.py:22`, see Q9).

## Problem and Goals

| # | Problem (from client) | Goal |
|---|---|---|
| 1 | App feels heavy on first open | Window usable faster and lighter at launch |
| 2 | Text looks blurry | Text as sharp as other Windows apps |
| 3 | Own voice is not captured | Mic audio included in the transcript when mic is on |
| 4 | No on/off control for voice | User can switch the voice button on/off in the UI |
| 5 | No audio visual | Live waveform shown in the UI |

## Users

- Non-technical Windows users running the `.exe` (`README.md` l.27-28).
- Record meetings (Meet, Teams, Slack) and other audio (`README.md` l.2).

## Requirements

| ID | Requirement | Current behavior (from code) | Acceptance criteria | Priority | Status |
|---|---|---|---|---|---|
| C1 | Lighter first open | `gui.py` imports `transcribe` at top (l.17), which loads `faster_whisper` (`transcribe.py` l.8). `App.__init__` calls `is_gpu_available()` (`gui.py` l.171) and `on_check_model()` (l.232) on the main thread. | Cold start to visible window < [X] s on [machine]. Idle memory after launch < [Y] MB. Both measured before and after. | [P1] | 🔴 |
| C2 | Sharp text | No DPI-awareness call found in `gui.py` (read in full) [unverified as cause]. Fixed pixel sizes: `WINDOW_WIDTH=450` (l.26), `RoundedButton` 150x46 (l.30), `wraplength=410` (l.217). | Text on a [150]% scaled display has no bitmap stretching, confirmed by side-by-side screenshot with a reference app. Status: fixed with DPI awareness; owner confirmed sharp text. | [P1] | ✅ |
| C3 | Record own voice via mic when mic is on | Records only the loopback device (`record_audio.py: record_system_audio` l.61-86). `README.md` l.49: "Does **not** record your microphone." | With mic on, own speech appears in the transcript. With mic off, output is identical to today. Verified by a 1-min test with both sides speaking. Status: manual switch works; Auto (Meet) does not work, parked. | [P1] | 🟡 |
| C4 | On/off option for the voice button in the UI | No such control. Only Start/Stop (`RoundedButton`, `gui.py` l.214), Browse, Check Model, GPU/CPU radios. "Voice button" meaning is unclear (Q2). | "My mic" ON/OFF switch in the window, default OFF, usable during recording. OFF moments record no voice. Auto-detection of meeting mute was tested and does not work (Meet keeps the mic open). | [P2] | ✅ |
| C5 | Audio waveform in the UI | No waveform. UI has timer and progress bar only (`gui.py` l.211, l.220). The capture loop `record_audio.py` l.113 (`stream.read(CHUNK)`) exposes no level data. | While recording, waveform updates at least [N] times per second and visibly reacts to sound. Silent input shows a flat line. Status: live boxed waveform built and tested. | [P2] | ✅ |

### Root-cause hypotheses (unconfirmed — do not treat as fact)

| ID | Hypothesis | Where found | Check that confirms it |
|---|---|---|---|
| H1 | Heavy imports run before the window appears | `gui.py` l.17, `transcribe.py` l.8-11 | Time start-up with `python -X importtime gui.py` |
| H2 | GPU probe blocks start-up | `gui.py` l.171 → `transcribe.py: is_gpu_available` (imports `ctranslate2`) | Time `is_gpu_available()` alone |
| H3 | Model cache check blocks start-up | `gui.py` l.232 → `transcribe.py: is_model_cached` | Time `is_model_cached()` alone |
| H4 | UPX-compressed build is slower to start | `AudioTranscriber-CPU.spec` l.39, l.51 (`upx=True`) | Rebuild with `upx=False`, compare cold start |
| H5 | Large bundle from `collect_all` | `AudioTranscriber-CPU.spec` l.7-10 | Compare bundle size and start time after trimming |
| H6 | Windows DPI scaling stretches the window | No DPI call in `gui.py` | Add DPI awareness in a test run, compare screenshots |
| H7 | Canvas-drawn button text is not anti-aliased | `RoundedButton._draw` (`gui.py` l.62-91) | Zoom screenshot of button vs ttk text |

## Out of Scope

- New features beyond the 5 complaints.
- Changes to Whisper model, VAD settings, or MP3 settings.
- New dependencies (proposals only, see Q8).
- Code signing and antivirus warnings.

## Success Metrics

| Metric | Target | Baseline |
|---|---|---|
| Cold start to visible window (C1) | < [X] s | Old exe: 4.5 s first launch, 0.5 s on 2 repeat launches (1 PC, 3 runs, 2026-11-07). Source `gui.py`: 2.0 s |
| Idle memory after launch (C1) | < [Y] MB | Old exe: 64 MB working set, 529 MB private. Source: 93 MB working set, 555 MB private |
| Text sharpness on scaled display (C2) | Matches reference app | Soft text at 125% scaling (before screenshot). After the fix: sharp, confirmed by owner |
| Mic speech present in transcript (C3) | Yes, in test recording | No (README l.49) |
| Mic on/off control works (C4) | Yes | No control |
| Waveform reacts to sound (C5) | Yes | No waveform |
| Regression: mic off, transcript unchanged (C3) | Pass | — |

## Open Questions

| # | Question | Blocks | Status / Answer |
|---|---|---|---|
| Q1 | C3: Is "own voice" the mic mixed into the system-audio track, or a separate track? | C3, C4 | ✅ Mixed into one track |
| Q2 | C3: Saved to the transcript, to the audio file, or both? Labeled (e.g. "Me")? | C3 | ✅ One mixed WAV feeds one transcript. No "Me" label |
| Q3 | C4: Which "voice button" is meant? Default on or off? | C4 | ✅ Final: manual "My mic" switch, default OFF. Auto-detect failed in test |
| Q4 | C5: Waveform for live input only, or playback too? | C5 | ✅ Live recording only |
| Q5 | C1: What is the target load time, and on which machine? What is "heavy"? | C1 | 🔴 Open |
| Q6 | C1: Allow imports inside functions (breaks "imports at top" rule)? | C1 | ✅ No. Step 8 skipped |
| Q7 | C3: Does the CLI (`main.py`) need mic recording too, or GUI only? | C3 | 🔴 Open |
| Q8 | C5: OK to draw the waveform on a tkinter Canvas (no new library)? | C5 | ✅ Yes, Canvas |
| Q9 | Version: code says 1.0.1; target is "v0.0.2". Which numbering applies? | Release | ✅ Final: keep 1.0.1 (same as GitHub's latest release) |
| Q10 | C2: Which display scaling and Windows version showed the blur? | C2 | 🔴 Open |
