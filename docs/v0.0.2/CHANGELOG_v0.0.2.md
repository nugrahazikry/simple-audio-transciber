# Changelog — Audio Transcriber v0.0.2

Date: 2026-11-07. Source of requirements: `complaints_2.md` (5 client complaints). Details: `PRD.md`, `PLAN_v0.0.2.md`.

## Summary by complaint

| ID | Client complaint | Result | Status |
|---|---|---|---|
| C1 | App is heavy on first open | Baseline measured only. No speed change made. | 🔴 open |
| C2 | Text is blurry | Fixed with DPI awareness. Client confirmed. | ✅ done |
| C3 | Record my own voice when the mic is on | Mic is mixed into the recording. Manual switch works. Auto (Meet) does not. | 🟡 partly |
| C4 | On/off option for the voice button | "My mic" ON/OFF switch in the window. | ✅ done |
| C5 | Audio waveform in the UI | Live waveform in a box. | ✅ done |

## Added

1. **Live waveform (C5).** Boxed waveform under the timer. Shows the louder of system audio and your mic. Flat line when idle.
2. **Mic recording (C3).** Your microphone is mixed into the same recording as the system audio, so your voice is in the transcript. If no mic is available, it records system audio only.
3. **"My mic" switch (C4).** Starts OFF. Works during a recording. OFF moments record no voice.
4. **Auto: follow Meet mute.** Reads the mute button of a Google Meet tab in Chrome and sets the mic for you. Unticked by default, because it does not work reliably yet. See Known issues.
5. **Sharp text (C2).** The window now declares DPI awareness, so Windows no longer stretches it. Fixed pixel sizes scale with the display.

6. **New look: Modern Recording Deck.** Light-blue window with a header, two cards (OUTPUT, DEVICE), a large recording deck (mic circle, big timer, rounded waveform, pill Start/Stop button) and a status bar. The button turns red while recording; the status dot and word follow Idle, Recording, Transcribing, Done and Error; a moving progress bar shows until a real percentage arrives. Colors that failed the AA contrast check were darkened. Details and limits: `PLAN_UI_redesign.md`.

## Changed

1. Window version stays `v1.0.1`, the same number as the last GitHub release. "v0.0.2" is only the internal name of this work and of its folders.
2. Window refreshes every 50 ms (was 150 ms) so the waveform moves smoothly.
3. README: mic text updated in place.
4. `requirements.txt`: added `comtypes`.

## Files

| File | Change |
|---|---|
| `gui.py` | Version, DPI awareness, size scaling, waveform, "My mic" switch, Auto checkbox, 50 ms refresh, new window layout and state styling |
| `ui_theme.py`, `ui_components.py` | New. Colors, fonts, sizes and the canvas widgets for the new look. |
| `record_audio.py` | New options `level_callback`, `use_mic`, `mic_on_event`. New helpers for loudness and mic mixing. Default behavior unchanged. |
| `meeting_mic.py` | New. Reads Google Meet's mute button. |
| `requirements.txt` | Added `comtypes` |
| `README.md` | Mic feature text |
| `tools/mic_probe_meet.py` | New. Developer test tool for the Meet button. Not used by the app. |
| `docs/v0.0.2/` | New planning documents: `PRD.md`, `PLAN_v0.0.2.md`, `complaints_2.md`, this change log |

Unchanged: `main.py` (CLI), `transcribe.py`, `AudioTranscriber-CPU.spec`.

## Known issues

1. **Auto does not follow the Meet mute button** in the owner's test. Parked. Use the manual "My mic" switch (untick Auto). `mic_probe_meet.py` can help debug.
2. **Auto limits:** Google Meet in Chrome only, English labels, Meet tab must be visible.
3. **C1 (heavy on first open) not addressed.** Baseline: old exe 4.5 s on first launch, 0.5 s on repeats; 64 MB working set, 529 MB private (1 PC, 3 runs).
4. **Echo on speakers:** your mic also hears the meeting audio, so lines may repeat. Headphones avoid this.
5. **Spacing** is about 20% tighter at 125% display scaling (padding is not scaled). Not tested at 100%.
6. **Idle waveform** line looks dashed because the bars do not touch.
7. **CLI (`main.py`) has no mic recording.** Open question Q7.
8. Teams and Zoom mute are not detected. Use the manual switch.
9. **New look limits:** rounded corners and icons are not anti-aliased, so edges look slightly jagged when zoomed; no glass, glow or shadow; standard Windows title bar; window height about 468 px at 100% (target 480).

## Build

1. Rebuilt after setting Auto unticked by default (checked in the exe: Auto unticked, "My mic" usable while recording). Built from `AudioTranscriber-CPU.spec` (unchanged) with PyInstaller 6.22.3 into `builds/v0.0.2/AudioTranscriber-CPU/` (240 MB). The previous local build (the v1.0.0 release, byte-identical to the GitHub download) was deleted; GitHub keeps both v1.0.0 and v1.0.1.
2. The exe starts and shows "Audio Transcriber v1.0.1". `comtypes` loads inside the exe.
   Zip: `builds/v0.0.2/AudioTranscriber-CPU.zip` (90.7 MB, integrity test OK, exe verified after extracting). Exe and `_internal/` are at the top level of the zip. First launch right after extracting took 3.7 s.
3. Start-up on one PC, 3 runs: 1.2 s first launch, 0.8 s repeats. Memory after 6 s idle: 83 MB working set, 546 MB private (old exe: 64 MB and 529 MB).
4. The first-launch time is not a fair comparison with the old exe (4.5 s): the new files had just been written, so Windows had them cached.
5. In the exe, Start Recording works: timer runs, status shows "Recording...", setup controls lock.
6. Not verified in the exe: sound reaching the waveform, the Meet auto watcher, and a full transcription. The CPU build has no GPU option.

## Tests done (new look)

1. 30 of 30 control and state checks passed, driven by real mouse and keyboard events through the real handlers.
2. Full record, transcribe and save through the new window: states Recording, Transcribing, Done; `.mp3` and `.txt` saved; 4 of 4 keywords found.
3. Layout checked at 100%, 125% and 150% display scaling: nothing clipped.
4. Rebuilt exe launched from the zip; a real click on Start Recording gave the red Stop button, red mic and running timer.

## Tests done (earlier work)

1. Mic mixing on synthetic audio (two tones, different sample rates): both present, length unchanged, loud audio clips safely.
2. Real record, transcribe, and save with a synthetic voice (mic off and on): Done, `.mp3` and `.txt` saved, all keywords found.
3. Mic switch OFF, ON, OFF in one recording: silent while OFF, signal while ON.
4. Screenshots at 125% display scaling.
5. Owner tested the manual switch in a Google Meet call.
