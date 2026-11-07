import ctypes
import os
import queue
import threading
import time
import tkinter as tk
import warnings
from collections import deque
from datetime import datetime
from tkinter import filedialog, messagebox

warnings.filterwarnings("ignore")

from dotenv import load_dotenv

load_dotenv()

from meeting_mic import watch_meet_mic
from record_audio import record_system_audio, convert_wav_to_mp3
from transcribe import ModelSetupError, transcribe_audio, is_gpu_available, is_model_cached
import ui_theme as ui
from ui_components import AppHeader, ConfigSection, RecordingDeck, StatusSection

VERSION = "1.0.1"
OUTPUT_DIR = "output"
DEBOUNCE_SECONDS = 0.5
SHORT_RECORDING_SECONDS = 5
WAVE_BARS = 60
POLL_MS = 50
WAVE_COLORS = {"RECORDING": ui.BAR_ACTIVE, "TRANSCRIBING": ui.BAR_SUBDUED}


class App:
    def __init__(self, root):
        """
        This function is about setting up the GUI window, its widgets, and initial state.
        The variable used in this code are:
        root: the tkinter root window

        The flow process of this codes are as follows:
        1. Store the root window and initialize state (IDLE) and a thread-safe message queue
        2. Detect whether a usable GPU is available (only offer the GPU option if so), and work
           out the screen scale factor so fixed pixel sizes stay proportional on scaled displays
        3. Build the four sections (header, OUTPUT/DEVICE cards, recording deck, status bar) and
           keep the widget names the rest of the code uses
        4. Start polling the message queue for updates from background threads

        The result of this function are as follows:
        (none, builds the running GUI)
        """

        # 1. Store the root window and initialize state and a thread-safe message queue
        self.root = root
        self.root.title(f"Audio Transcriber v{VERSION}")
        self.root.resizable(False, False)

        self.state = "IDLE"
        self.stop_event = None
        self.msg_queue = queue.Queue()
        self.start_time = None
        self.last_recording_seconds = None
        self.last_toggle_click = 0
        self.session_dir = None
        self.output_dir = OUTPUT_DIR
        self.wav_path = None
        self.mic_event = threading.Event()
        self.txt_path = None

        # 2. Detect whether a usable GPU is available
        self.gpu_available = is_gpu_available()
        self.device_var = tk.StringVar(value="cuda" if self.gpu_available else "cpu")
        self.scale = self.root.winfo_fpixels("1i") / 96
        self.theme = ui.Theme(self.root, self.scale)
        self.wave_color = ui.BAR_IDLE

        # 3. Build the four sections
        self.root.configure(bg=ui.BG)
        self.root.minsize(self._px(ui.WINDOW_WIDTH), 1)
        AppHeader(root, self.theme).pack(fill="x")
        page = tk.Frame(root, bg=ui.BG, padx=self._px(ui.PAGE_PAD), pady=self._px(ui.GAP))
        page.pack(fill="both", expand=True)

        self.folder_var = tk.StringVar(value=self._short_path(self.output_dir))
        self.mic_var = tk.BooleanVar(value=False)
        self.auto_var = tk.BooleanVar(value=False)
        commands = {
            "browse": self.on_browse,
            "check_model": self.on_check_model,
            "mic": self.on_mic_toggle,
            "auto": self.on_auto_toggle,
        }
        cards = ConfigSection(page, self.theme, self.folder_var, self.device_var, self.gpu_available, self.mic_var, self.auto_var, commands)
        cards.pack(fill="x")
        self.folder_entry = cards.folder_entry
        self.browse_button = cards.browse_button
        self.check_button = cards.check_button
        self.model_dot = cards.model_dot
        self.model_dot_id = cards.model_dot_id
        self.model_label = cards.model_label
        self.gpu_radio = cards.gpu_radio
        self.cpu_radio = cards.cpu_radio
        self.mic_check = cards.mic_check
        self.auto_check = cards.auto_check
        self._refresh_mic_controls()

        self.deck = RecordingDeck(page, self.theme, self.on_toggle)
        self.deck.pack(fill="x", pady=(self._px(ui.GAP), 0))
        self.timer_label = self.deck.timer_label
        self.wave_canvas = self.deck.wave_canvas
        self.wave_width = self.deck.wave_width
        self.wave_height = self.deck.wave_height
        self.toggle_button = self.deck.toggle_button
        self.wave_levels = deque([0.0] * WAVE_BARS, maxlen=WAVE_BARS)
        self._draw_waveform()

        self.status_section = StatusSection(page, self.theme)
        self.status_section.pack(fill="x", pady=(self._px(ui.GAP), 0))
        self.status_label = self.status_section.status_label
        self.progress_bar = self.status_section.progress_bar
        self.progress_label = self.status_section.progress_label
        self.saved_label = self.status_section.saved_label
        self.on_check_model()

        # 4. Start polling the message queue for updates from background threads
        self.root.after(POLL_MS, self.poll_queue)

    def _apply_visual_state(self, name):
        """
        This function is about restyling the window for the current app state.
        The variable used in this code are:
        name: "IDLE", "RECORDING", "TRANSCRIBING", "DONE" or "ERROR"

        The flow process of this codes are as follows:
        1. Update the status dot, word and progress bar
        2. Update the microphone circle on the recording deck
        3. Pick the waveform color for the state and redraw the waveform

        The result of this function are as follows:
        (none)
        """

        # 1. Status dot, word and progress bar
        self.status_section.set_state(name)

        # 2. Microphone circle
        self.deck.set_state(name)

        # 3. Waveform color
        self.wave_color = WAVE_COLORS.get(name, ui.BAR_IDLE)
        self._draw_waveform()

    def _px(self, pixels):
        """
        This function is about scaling a fixed pixel size to the screen's display scaling.
        The variable used in this code are:
        pixels: the size in pixels at 100% display scaling

        The flow process of this codes are as follows:
        1. Multiply by the scale factor and round to a whole pixel

        The result of this function are as follows:
        scaled: the size in pixels for this screen
        """

        # 1. Multiply by the scale factor and round
        return self.theme.px(pixels)

    def _draw_waveform(self):
        """
        This function is about drawing the waveform bars from the stored level history.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Clear the waveform canvas
        2. Draw one centred rounded bar per stored level in the current state's color; silence
           stays a dotted baseline

        The result of this function are as follows:
        (none)
        """

        # 1. Clear the canvas
        self.wave_canvas.delete("all")

        # 2. Draw one centred rounded bar per stored level
        pad = self._px(6)
        step = (self.wave_width - 2 * pad) / WAVE_BARS
        mid = self.wave_height / 2
        bar_width = max(2, self._px(4))
        room = mid - bar_width / 2 - self._px(1)
        for i, level in enumerate(self.wave_levels):
            half = max(0.5, min(1.0, level) * room)
            x = pad + i * step + step / 2
            self.wave_canvas.create_line(
                x, mid - half, x, mid + half, fill=self.wave_color, width=bar_width, capstyle="round"
            )

    def _reset_waveform(self):
        """
        This function is about clearing the waveform back to a flat line.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Fill the level history with silence
        2. Redraw the waveform

        The result of this function are as follows:
        (none)
        """

        # 1. Fill the level history with silence
        self.wave_levels.extend([0.0] * WAVE_BARS)

        # 2. Redraw the waveform
        self._draw_waveform()

    def push_level(self, level):
        """
        This function is about adding the newest audio level and redrawing the waveform.
        The variable used in this code are:
        level: audio loudness from 0.0 (silent) to 1.0 (loudest)

        The flow process of this codes are as follows:
        1. Add the level to the history (the oldest level drops off)
        2. Redraw the waveform

        The result of this function are as follows:
        (none)
        """

        # 1. Add the level to the history
        self.wave_levels.append(level)

        # 2. Redraw the waveform
        self._draw_waveform()

    def _short_path(self, path):
        """
        This function is about shortening a long folder path for the small path box.
        The variable used in this code are:
        path: the folder path to display

        The flow process of this codes are as follows:
        1. Make the path absolute
        2. If it is long, keep the drive and the last folder name, like C:\\...\\output

        The result of this function are as follows:
        short: the path text to show
        """

        # 1. Make the path absolute
        full = os.path.abspath(path)

        # 2. Shorten long paths
        if len(full) <= 32:
            return full
        return f"{os.path.splitdrive(full)[0]}\\...\\{os.path.basename(full)}"

    def _set_text(self, label, text):
        """
        This function is about setting a footer label's text and hiding it when empty.
        The variable used in this code are:
        label: the footer label to update
        text: the new text ("" hides the label)

        The flow process of this codes are as follows:
        1. Set the text
        2. Show the label if it has text, otherwise hide it so the window stays compact

        The result of this function are as follows:
        (none)
        """

        # 1. Set the text
        label.config(text=text)

        # 2. Show or hide the label
        if text:
            label.grid()
        else:
            label.grid_remove()

    def _set_setup_controls(self, state):
        """
        This function is about enabling or disabling the setup controls together.
        The variable used in this code are:
        state: "normal" or "disabled"

        The flow process of this codes are as follows:
        1. Apply the state to Browse, Check Model and the device radios

        The result of this function are as follows:
        (none)
        """

        # 1. Apply the state to the setup controls
        self.browse_button.config(state=state)
        self.check_button.config(state=state)
        if self.gpu_radio:
            self.gpu_radio.config(state=state)
        self.cpu_radio.config(state=state)

    def on_mic_toggle(self):
        """
        This function is about turning the microphone on or off, also while recording.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Read the switch and set or clear the shared event the recorder watches
        2. Show "My mic: ON" or "My mic: OFF" on the switch, with "(auto)" when Meet controls it

        The result of this function are as follows:
        (none)
        """

        # 1. Set or clear the shared event
        is_on = self.mic_var.get()
        if is_on:
            self.mic_event.set()
        else:
            self.mic_event.clear()

        # 2. Show the new state on the switch
        label = "My mic: ON" if is_on else "My mic: OFF"
        if self.auto_var.get():
            label += " (auto)"
        self.mic_check.config(text=label)

    def on_auto_toggle(self):
        """
        This function is about switching between automatic (follow Meet) and manual microphone control.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Refresh which controls are usable and the switch's label

        The result of this function are as follows:
        (none)
        """

        # 1. Refresh the controls and label
        self._refresh_mic_controls()
        self.on_mic_toggle()

    def _refresh_mic_controls(self):
        """
        This function is about enabling the right microphone controls for the current state.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. The Auto checkbox is locked while recording
        2. The manual "My mic" switch is locked while Auto is on (Meet controls it)

        The result of this function are as follows:
        (none)
        """

        # 1. Lock the Auto checkbox while recording
        recording = getattr(self, "state", "IDLE") == "RECORDING"
        self.auto_check.config(state="disabled" if recording else "normal")

        # 2. Lock the manual switch while Auto is on
        self.mic_check.config(state="disabled" if self.auto_var.get() else "normal")

    def _on_meet_mic(self, is_on):
        """
        This function is about passing a Meet mute change from the watcher thread to the window.
        The variable used in this code are:
        is_on: True if Meet says you are unmuted, False if muted or Meet is not visible

        The flow process of this codes are as follows:
        1. Put the change on the message queue (the window updates widgets only on the main thread)

        The result of this function are as follows:
        (none)
        """

        # 1. Put the change on the message queue
        self.msg_queue.put(("mic_auto", is_on))

    def on_browse(self):
        """
        This function is about letting the user pick the folder where sessions are saved.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Open the folder picker starting at the current output folder
        2. If a folder was chosen, store it and update the path box

        The result of this function are as follows:
        (none)
        """

        # 1. Open the folder picker
        chosen = filedialog.askdirectory(initialdir=self.output_dir, title="Choose output folder")

        # 2. Store the chosen folder
        if chosen:
            self.output_dir = os.path.normpath(chosen)
            self.folder_var.set(self._short_path(self.output_dir))

    def on_check_model(self):
        """
        This function is about showing whether the Whisper model is already downloaded.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Ask is_model_cached() (local files only, no download)
        2. Show a green dot and "Model found", or a red dot and "Model not found"

        The result of this function are as follows:
        (none)
        """

        # 1. Ask whether the model is cached
        found = is_model_cached()

        # 2. Show the result
        self.model_dot.itemconfig(self.model_dot_id, fill=ui.GREEN if found else ui.RED)
        self.model_label.config(
            text="Model found" if found else "Model not found", fg=ui.GREEN_TEXT if found else ui.RED_TEXT
        )

    def on_toggle(self):
        """
        This function is about handling the Start/Stop button click based on current state.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Ignore rapid repeat clicks (accidental double-click on the same button)
        2. If idle or done, start a new recording session
        3. If recording, stop it

        The result of this function are as follows:
        (none)
        """

        # 1. Ignore rapid repeat clicks
        now = time.time()
        if now - self.last_toggle_click < DEBOUNCE_SECONDS:
            return
        self.last_toggle_click = now

        # 2. If idle or done, start a new recording session
        if self.state in ("IDLE", "DONE"):
            self.start_recording()

        # 3. If recording, stop it
        elif self.state == "RECORDING":
            self.stop_recording()

    def _reenable_controls(self):
        """
        This function is about restoring the button and device controls after a session ends.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Re-enable the Start Recording button
        2. Re-enable Browse, Check Model and the device radiobuttons, and refresh the model indicator

        The result of this function are as follows:
        (none)
        """

        # 1. Re-enable the Start Recording button
        self.toggle_button.config(text="Start Recording", state="normal")

        # 2. Re-enable the setup controls and refresh the model indicator
        self._set_setup_controls("normal")
        self._refresh_mic_controls()
        self.on_check_model()

    def _short_recording_note(self):
        """
        This function is about building a warning prefix when the actual recording turned out
        unusually short, as a last-resort safety net beyond the stop-confirmation dialog (e.g. if
        the recording was cut short by something other than the user clicking Stop).
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. If the last recording's duration is unknown or not unusually short, return no note
        2. Otherwise build a short warning line to prefix onto the final status message

        The result of this function are as follows:
        note: a warning string ending in a space, or an empty string if nothing to flag
        """

        # 1. If duration is unknown or not unusually short, return no note
        if self.last_recording_seconds is None or self.last_recording_seconds >= SHORT_RECORDING_SECONDS:
            return ""

        # 2. Otherwise build a short warning line
        return f"Note: recording was only {self.last_recording_seconds:.0f}s long — was that intentional? "

    def start_recording(self):
        """
        This function is about beginning a new record-then-transcribe session.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Build the date folder and timestamped session folder and file paths
        2. Reset the UI (timer, waveform, status, progress, saved label)
        3. Start the recording worker thread and the live timer tick, and in auto mode start the
           watcher that follows Meet's mute button (the microphone starts OFF)

        The result of this function are as follows:
        (none)
        """

        # 1. Build the date folder and timestamped session folder and file paths
        date_str = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.output_dir, date_str, timestamp)
        os.makedirs(self.session_dir, exist_ok=True)
        self.wav_path = os.path.join(self.session_dir, f"{timestamp}_recording.wav")
        self.mp3_path = os.path.join(self.session_dir, f"{timestamp}_recording.mp3")
        self.txt_path = os.path.join(self.session_dir, f"{timestamp}_transcript.txt")

        # 2. Reset the UI
        self.stop_event = threading.Event()
        self.state = "RECORDING"
        self.last_recording_seconds = None
        self.toggle_button.config(text="Stop Recording")
        self.status_label.config(text="Recording...")
        self._set_text(self.saved_label, "")
        self.progress_bar["value"] = 0
        self._set_text(self.progress_label, "")
        self.start_time = time.time()
        self._reset_waveform()
        self._set_setup_controls("disabled")
        self._apply_visual_state("RECORDING")

        # 3. Start the recording worker thread, the live timer tick, and the Meet watcher (auto mode)
        self.tick_timer()
        threading.Thread(target=self._record_worker, daemon=True).start()
        self._refresh_mic_controls()
        if self.auto_var.get():
            self.mic_var.set(False)
            self.on_mic_toggle()
            threading.Thread(target=watch_meet_mic, args=(self.stop_event, self._on_meet_mic), daemon=True).start()

    def _record_worker(self):
        """
        This function is about running the blocking recording call off the main thread.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Call record_system_audio with the session's stop_event, the microphone switch (the
           shared event the "My mic" switch sets and clears), and a callback that sends each
           loudness value to the main thread for the waveform
        2. Notify the main thread that recording has finished (or that an error occurred)

        The result of this function are as follows:
        (none, communicates via self.msg_queue)
        """
        try:
            # 1. Call record_system_audio with the session's stop_event
            record_system_audio(
                self.wav_path,
                stop_event=self.stop_event,
                level_callback=lambda level: self.msg_queue.put(("level", level)),
                use_mic=True,
                mic_on_event=self.mic_event,
            )

            # 2. Notify the main thread that recording has finished
            self.msg_queue.put(("recording_done", None))
        except Exception as e:
            self.msg_queue.put(("error", f"Recording failed: {e}"))

    def stop_recording(self):
        """
        This function is about signaling the recording worker to stop.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. If recording only just started, confirm before stopping (guards against an
           accidental click stopping a session almost immediately)
        2. Set the stop_event so the recording loop exits
        3. Disable the button and show a transitional status until transcription begins

        The result of this function are as follows:
        (none)
        """

        # 1. If recording only just started, confirm before stopping
        elapsed = time.time() - self.start_time
        if elapsed < SHORT_RECORDING_SECONDS:
            if not messagebox.askyesno(
                "Stop recording?", f"Recording started only {elapsed:.0f}s ago. Stop anyway?"
            ):
                return

        # 2. Set the stop_event so the recording loop exits
        self.stop_event.set()

        # 3. Disable the button and show a transitional status
        self.toggle_button.config(state="disabled")
        self.status_label.config(text="Stopping...")

    def tick_timer(self):
        """
        This function is about updating the live elapsed-time label once per second while recording.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Stop ticking if no longer recording
        2. Compute elapsed seconds and format as mm:ss
        3. Reschedule itself after 1 second

        The result of this function are as follows:
        (none)
        """

        # 1. Stop ticking if no longer recording
        if self.state != "RECORDING":
            return

        # 2. Compute elapsed seconds and format as mm:ss
        elapsed = int(time.time() - self.start_time)
        minutes, seconds = divmod(elapsed, 60)
        self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")

        # 3. Reschedule itself after 1 second
        self.root.after(1000, self.tick_timer)

    def begin_transcription(self):
        """
        This function is about moving into the transcribing state and starting its worker thread.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Update state and status label
        2. Start the transcription worker thread

        The result of this function are as follows:
        (none)
        """

        # 1. Update state and status label
        self.state = "TRANSCRIBING"
        self.status_label.config(text="Transcribing...")
        self.toggle_button.config(text="Start Recording", state="disabled")
        self._apply_visual_state("TRANSCRIBING")

        # 2. Start the transcription worker thread with the device chosen on the main thread
        selected_device = self.device_var.get()
        threading.Thread(target=self._transcribe_worker, args=(selected_device,), daemon=True).start()

    def _transcribe_worker(self, device):
        """
        This function is about running transcription off the main thread and cleaning up the WAV file.
        The variable used in this code are:
        device: "cuda" or "cpu", chosen on the main thread before this worker started

        The flow process of this codes are as follows:
        1. Transcribe the WAV file, reporting progress through the message queue (transcribe_audio
           retries with VAD off internally if the first pass finds no speech, e.g. singing)
        2. If the transcript is still empty even after that retry (true silence), report that and
           stop here, keeping the WAV so it can be inspected instead of silently discarding it
        3. Convert the WAV to a smaller MP3 and delete the WAV
        4. Only now notify the main thread that the session is fully done (flagging if the VAD-off
           retry was used, since that can hallucinate text and is worth double-checking), or that
           any step above raised an error

        The result of this function are as follows:
        (none, communicates via self.msg_queue)
        """
        def on_progress(pct):
            self.msg_queue.put(("progress", pct))

        def on_status(message):
            self.msg_queue.put(("status", message))

        # 1. Transcribe the WAV file, reporting progress and phase through the message queue
        try:
            _, saved_txt_path, used_fallback = transcribe_audio(
                self.wav_path, self.txt_path, progress_callback=on_progress, device=device, status_callback=on_status
            )
        except ModelSetupError as e:
            self.msg_queue.put(("error", str(e)))
            return
        except Exception as e:
            self.msg_queue.put(("error", f"Transcription failed: {e}"))
            return

        try:
            with open(saved_txt_path, "r", encoding="utf-8") as f:
                transcript_content = f.read().strip()
        except Exception as e:
            self.msg_queue.put(("error", f"Reading transcript failed: {e}"))
            return

        # 2. If still empty even after the VAD-off retry, report that and stop here
        if not transcript_content:
            self.msg_queue.put(("empty", self.wav_path))
            return

        # 3. Convert the WAV to a smaller MP3 and delete the WAV
        try:
            convert_wav_to_mp3(self.wav_path, self.mp3_path)
        except Exception as e:
            self.msg_queue.put(("error", f"MP3 conversion failed: {e}"))
            return

        try:
            os.remove(self.wav_path)
        except Exception as e:
            self.msg_queue.put(("error", f"Deleting WAV failed: {e}"))
            return

        # 4. Only now notify the main thread that the session is fully done
        self.msg_queue.put(("done", (self.session_dir, used_fallback)))

    def poll_queue(self):
        """
        This function is about draining background-thread messages and applying them to the GUI.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Pull every pending message from the queue without blocking
        2. Apply the corresponding widget updates for each message type (loudness values are
           combined into one, the loudest, so the waveform adds one bar per poll)
        3. Draw the new waveform bar, then reschedule itself to run again shortly

        The result of this function are as follows:
        (none)
        """
        new_level = None
        try:
            # 1. Pull every pending message from the queue without blocking
            while True:
                event, payload = self.msg_queue.get_nowait()

                # 2. Apply the corresponding widget updates for each message type
                if event == "level":
                    new_level = max(new_level or 0.0, payload)
                elif event == "mic_auto":
                    if self.auto_var.get():
                        self.mic_var.set(payload)
                        self.on_mic_toggle()
                elif event == "recording_done":
                    new_level = None
                    self.last_recording_seconds = time.time() - self.start_time
                    self._reset_waveform()
                    self.begin_transcription()
                elif event == "status":
                    self.status_label.config(text=payload)
                elif event == "progress":
                    self.progress_bar["value"] = payload
                    self._set_text(self.progress_label, f"{round(payload)}%")
                elif event == "done":
                    session_dir, used_fallback = payload
                    self.state = "DONE"
                    short_note = self._short_recording_note()
                    if used_fallback:
                        self.status_label.config(text="Done (recovered without VAD)")
                        self._set_text(self.saved_label, f"{short_note}Please verify accuracy — silence can hallucinate. Last saved: {session_dir}")
                    else:
                        self.status_label.config(text="Done")
                        self._set_text(self.saved_label, f"{short_note}Last saved: {session_dir}")
                    self._reenable_controls()
                    self._apply_visual_state("DONE")
                elif event == "empty":
                    self.state = "IDLE"
                    self.status_label.config(text="No speech detected (even without VAD)")
                    self._set_text(self.saved_label, f"{self._short_recording_note()}Transcript was empty. WAV kept at: {payload}")
                    self._reenable_controls()
                    self._apply_visual_state("IDLE")
                elif event == "error":
                    self.state = "IDLE"
                    self.status_label.config(text=f"Error: {payload}")
                    self._reenable_controls()
                    self._apply_visual_state("ERROR")
        except queue.Empty:
            pass

        # 3. Draw the new waveform bar, then reschedule itself
        if new_level is not None:
            self.push_level(new_level)
        self.root.after(POLL_MS, self.poll_queue)


def enable_dpi_awareness():
    """
    This function is about telling Windows the app handles display scaling itself, so text is
    drawn sharp instead of being stretched like a picture.
    The variable used in this code are:
    (none)

    The flow process of this codes are as follows:
    1. Ask Windows for system DPI awareness; ignore the call if it is not supported

    The result of this function are as follows:
    (none)
    """

    # 1. Ask Windows for system DPI awareness
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


if __name__ == "__main__":
    enable_dpi_awareness()
    root = tk.Tk()
    app = App(root)
    root.mainloop()
