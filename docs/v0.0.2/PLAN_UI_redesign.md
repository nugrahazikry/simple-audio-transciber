# Plan — UI redesign: Modern Recording Deck

Goal: make the window look like the reference image (header, two cards, big recording deck, status bar) without changing recording, transcription, model check, output folder, device choice, or Meet mute behavior.
Status 2026-11-07: all steps U1–U16 ✅ (built, tested, rebuilt, documented). Not committed yet. Owner said "yes please proceed", so D1–D8 were applied as recommended (see Result at the end).
Impact: **High** = touches the whole window layout, or widgets that the recording and transcription logic use.

## Facts checked in the code

1. Framework is **tkinter + ttk** (`gui.py` l.6, l.10) with theme `vista` (l.294). Not CustomTkinter, not Qt.
2. Rounded cards, pill buttons, icons and waveform must be drawn on `tk.Canvas`, like the existing `RoundedButton`. No new library needed.
3. The logic touches these widgets by name: `toggle_button`, `status_label`, `timer_label`, `progress_bar`, `progress_label`, `saved_label`, `wave_canvas`, `model_dot`, `model_label`, `folder_var`, `folder_entry`, `browse_button`, `check_button`, `gpu_radio`, `cpu_radio`, `device_var`, `mic_check`, `mic_var`, `auto_check`, `auto_var`. The new components must keep these names and methods, so handlers stay unchanged.
4. App states in code: `IDLE`, `RECORDING`, `TRANSCRIBING`, `DONE`. The brief lists no DONE state, so DONE needs a design (see D3).
5. The CPU build has no GPU radio. The DEVICE card must look right with one radio.
6. No new dependency, so the PyInstaller build is unaffected.

## Contrast check of the given palette (WCAG AA)

| Pair | Ratio | Result |
|---|---|---|
| Main text `#172554` on deck / background | 12.9 / 13.4 | ✅ |
| White on primary button `#2563EB` | 5.2 | ✅ |
| White on red stop button `#DC2626` | 4.8 | ✅ |
| Secondary text `#64748B` on card `#F7F9FF` | 4.5 | ✅ (just) |
| Secondary text `#64748B` on deck `#E8F1FF` | 4.2 | ❌ needs a darker gray |
| Secondary text `#64748B` on header `#EAF1FF` | 4.2 | ❌ needs a darker gray |
| Green text `#16A34A` ("Model found") on card | 3.1 | ❌ needs a darker green for text |
| Progress fill `#2563EB` on track `#D4DEEF` | 3.8 | ✅ (non-text needs 3.0) |
| Card border `#D7E2F2` on card | 1.2 | ❌ too faint for input boundaries |

Fix: pick darker values for the failing text and input borders, and verify them with the same script before using them.

## Decisions needed from the owner

| # | Question | My recommendation |
|---|---|---|
| D1 | Title bar: keep the native Windows one (with the header drawn below it), or build a custom borderless one like the image? | Keep native. A custom bar in tkinter loses dragging, snapping and taskbar behavior unless rebuilt by hand. High risk. |
| D2 | The image shows a maximize button. The window is fixed size today. Allow resizing? | Keep fixed size 550 × 480. Maximize stays greyed. |
| D3 | Status text: keep today's detailed messages (model download, errors, "Done", "No speech detected"), or use only short words (Idle, Recording, Transcribing, Error)? | Keep a short state word next to the dot and keep today's detail message on a small line below. Nothing is lost. |
| D4 | The image shows no Browse button, the written spec does. | Keep Browse (the function is needed). |
| D5 | Use darker colors where the palette fails AA (table above)? | Yes. |
| D6 | The image has a soft, glassy deck with glow. Tkinter has no blur or transparency. | Use flat fills with at most a simple two-tone gradient. Close, not identical. |
| D7 | Font: "Segoe UI Variable" if installed, else Segoe UI. | Yes. |
| D8 | Indeterminate progress bar before the first transcription percentage arrives (never show a made-up number). | Yes. |

## Visual checklist (from the image and the brief)

1. Header ~55–60 px: blue rounded equalizer icon, "AUDIO TRANSCRIBER" bold, "Local AI Recording" muted.
2. Two equal-height cards: OUTPUT (path, Browse, Check Model, green dot, "Model found") and DEVICE (GPU/CPU radios, "My mic: OFF", "Auto: follow Meet mute").
3. Recording deck `#E8F1FF`, 20–24 px radius: mic circle (64–76 px) left, timer 48–52 px right, `00:00`.
4. Waveform under them across most of the deck: rounded light-blue bars, flat baseline when idle, live bars while recording.
5. Pill button ~220 × 44 centered: blue "START RECORDING" with play icon; red "STOP RECORDING" while recording; disabled while transcribing.
6. Status row: dot + state text on the left, thin 7–9 px progress bar, blue fill on pale track.
7. States: IDLE (gray dot), RECORDING (red dot, active mic), TRANSCRIBING (blue dot, subdued waveform, progress), DONE (green dot), ERROR (red dot and red progress).
8. Window about 550 × 480 at 100%, scales with Windows display scaling, nothing clipped, no scrolling.

## Steps (lowest risk first)

| # | Step (max 20 words) | Files / functions touched | Impact | Verification | Status |
|---|---|---|---|---|---|
| U1 | Get the owner's answers to D1–D8. | None | **Low** — no code change | Answers noted in this file. Owner approved my recommendations for D1–D8 | ✅ |
| U2 | Capture "before" screenshots of every state at 100% and 125% scaling. | None (test script) | **Low** — measure only | Before screenshots of IDLE, RECORDING, TRANSCRIBING, DONE and ERROR captured at 125% (scratch folder) | ✅ |
| U3 | Create the theme file: colors, fonts, sizes, scale helper. Use contrast-verified colors. | New `ui_theme.py` | **Low** — new, unused | Contrast script passes AA for all text pairs; input border `#7A8EAD` passes 3:1 | ✅ |
| U4 | Create canvas widgets: rounded card, pill button with hover, pressed and disabled states. | New `ui_components.py` | **Low** — new, unused | Hover, pressed, disabled and focus looks work (hover and disabled tested by events) | ✅ |
| U5 | Draw icons on canvas: equalizer, microphone, play, stop. No image files. | `ui_components.py` | **Low** — isolated | Icons drawn at 100%, 125% and 150%; edges are slightly jagged (canvas has no anti-aliasing) | ✅ |
| U6 | Build the header bar under the native title bar. | `ui_components.py` | **Low** — no logic | Matches checklist item 1 | ✅ |
| U7 | Build the two cards. Keep every existing widget name and method. | `ui_components.py`, `gui.py: App.__init__` | **High** — folder, model, device, mic and Auto widgets | Browse, Check Model, radios, mic and Auto work (tested with real mouse and keyboard events) | ✅ |
| U8 | Build the recording deck: mic circle, timer, waveform with rounded bars, pill button. | `ui_components.py`, `gui.py` | **High** — timer, button and waveform used by recording | Start and Stop work by click; timer counts; waveform bars follow live audio | ✅ |
| U9 | Build the status bar: dot, state text, rounded progress with determinate and indeterminate modes. Keep percent and "Last saved". | `ui_components.py`, `gui.py` | **High** — progress and messages used by transcription | Moving bar before the first real percent; real percent then shown; no made-up number | ✅ |
| U10 | Rewire `App.__init__` to the new components; handlers stay unchanged. | `gui.py: App.__init__`, `_set_setup_controls`, `_set_text` | **High** — all widgets replaced | Every control from the widget list responds; old widget names kept | ✅ |
| U11 | Add state styling for IDLE, RECORDING, TRANSCRIBING, DONE and error. | `gui.py: start_recording`, `stop_recording`, `poll_queue`, `begin_transcription` | **High** — runs on every state change | Each state matches checklist item 7 (screenshots of all five states) | ✅ |
| U12 | Style radios and checkboxes with the palette. Changed: custom canvas controls, because ttk "clam" draws an X for ticked boxes. | `ui_components.py: ToggleControl`; `gui.py` (ttk styling removed) | **High** — changes the look of every option control | Tick and dot are clear; locked and focus looks work | ✅ |
| U13 | Resize to about 550 × 480 using `_px` scaling; check 100%, 125%, 150%. | `gui.py` | **High** — whole layout | Nothing clipped at 100%, 125% and 150%. Content is about 550 × 468 at 100% (target 480) | ✅ |
| U14 | Test: all controls, all states, then a full record, transcribe and save. | None (test) | **Low** — test only | 30 of 30 control and state checks passed (real mouse and key events). Full run through the new UI: Recording → Transcribing → Done, `.mp3` and `.txt` saved, 4 of 4 keywords found | ✅ |
| U15 | Rebuild the exe and zip; launch and check the states. | Build only | **Low** — separate build folder | Exe shows the new UI; build stays version 1.0.1. Rebuilt; zip 90.7 MB (integrity OK). Exe extracted from the zip launches, a real click on Start gives the red Stop button, red mic and running timer. Full transcription also run in the exe: Transcribing with moving bar, then Done with green bar, files saved | ✅ |
| U16 | Update README and change log for the new look. | `README.md`, `CHANGELOG_v0.0.2.md` | **Low** — text only | README (feature 3, project structure, dependencies, key files) and change log match the final UI | ✅ |

## Risks and how the plan handles them

1. **Breaking a handler:** components keep the old widget names and methods; each state and control is tested (U10, U14).
2. **Scaling bugs:** all sizes go through `_px`; checked at three scalings (U13).
3. **Status messages lost:** kept under D3.
4. **Auto and mic switch regress:** they sit in the DEVICE card with the same variables and callbacks (U7).
5. **Cannot match exactly:** blur, glow and translucency (D6); native title bar if D1 is kept.

## Result (what was built)

**Files:** new `ui_theme.py` (colors, fonts, sizes) and `ui_components.py` (header, cards, recording deck, status bar, buttons, controls); `gui.py` changed in the constructor and state handlers only. `record_audio.py`, `transcribe.py` and `meeting_mic.py` are untouched.

**Decisions as applied**
- D1: native title bar kept; the header is drawn below it. D2: fixed size, maximize stays greyed.
- D3: short state word next to the dot (Idle, Recording, Transcribing, Done, Error), and the old detailed message on a line below when it says more.
- D4: Browse kept. D5: darker colors for failing pairs: muted text `#475569`, green text `#15803D`, red text `#B91C1C`, input border `#7A8EAD`. D6: flat fills. D7: Segoe UI Variable if installed, else Segoe UI. D8: moving bar until a real percent arrives.

**Not replicated exactly**
1. Rounded corners and icons are not anti-aliased (tkinter canvas), so edges look slightly jagged when zoomed.
2. No glass, glow or shadow on the deck; flat fills only.
3. Windows title bar is the standard one, not the custom bar with the app icon from the image.
4. The waveform scrolls with live audio. The idle state is a dotted baseline, not the faded bars at the sides.
5. Window height is about 468 px at 100%, a little under the 480 target.

**How to run:** `.\venv\Scripts\python.exe gui.py` in the project folder.

## Rules for this plan

- Existing framework, architecture, callbacks and behavior stay as they are. Only layout, styling, typography, spacing and visual states change.
- No new features, no new dependency, no mock logic.
- Each step needs the owner's go-ahead before implementation starts.
- All builds stay version 1.0.1.
