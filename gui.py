import os
import queue
import threading
import time
import tkinter as tk
import warnings
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

warnings.filterwarnings("ignore")

from dotenv import load_dotenv

load_dotenv()

from record_audio import record_system_audio, convert_wav_to_mp3
from transcribe import ModelSetupError, transcribe_audio, is_gpu_available, is_model_cached

VERSION = "1.0.1"
OUTPUT_DIR = "output"
DEBOUNCE_SECONDS = 0.5
SHORT_RECORDING_SECONDS = 5
BLUE = "#0A56D6"
BLUE_ACTIVE = "#0847B0"
BLUE_DISABLED = "#8DB0EC"
WINDOW_WIDTH = 450


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=150, height=46, radius=10):
        """
        This function is about building a blue button with rounded corners (tkinter has none built in).
        The variable used in this code are:
        parent: the widget that holds the button
        text: the text shown on the button
        command: the function called when the button is clicked
        width: button width in pixels
        height: button height in pixels
        radius: corner radius in pixels

        The flow process of this codes are as follows:
        1. Create the canvas with the parent's background and store the settings
        2. Draw the button and bind hover and click events

        The result of this function are as follows:
        (none, builds the button widget)
        """

        # 1. Create the canvas and store the settings
        super().__init__(parent, width=width, height=height, bg="white", highlightthickness=0, cursor="hand2")
        self.command = command
        self.text = text
        self.radius = radius
        self.enabled = True

        # 2. Draw the button and bind events
        self._draw(BLUE)
        self.bind("<Enter>", lambda e: self.enabled and self._draw(BLUE_ACTIVE))
        self.bind("<Leave>", lambda e: self._draw(BLUE if self.enabled else BLUE_DISABLED))
        self.bind("<ButtonRelease-1>", self._on_click)

    def _draw(self, color):
        """
        This function is about drawing the rounded rectangle and its text.
        The variable used in this code are:
        color: the fill colour of the button

        The flow process of this codes are as follows:
        1. Clear the canvas
        2. Draw four corner arcs and two rectangles that form the rounded rectangle
        3. Draw the white text in the centre

        The result of this function are as follows:
        (none)
        """
        w, h, r = int(self["width"]), int(self["height"]), self.radius

        # 1. Clear the canvas
        self.delete("all")

        # 2. Draw the rounded rectangle
        d = 2 * r
        self.create_arc(0, 0, d, d, start=90, extent=90, fill=color, outline=color)
        self.create_arc(w - d, 0, w, d, start=0, extent=90, fill=color, outline=color)
        self.create_arc(0, h - d, d, h, start=180, extent=90, fill=color, outline=color)
        self.create_arc(w - d, h - d, w, h, start=270, extent=90, fill=color, outline=color)
        self.create_rectangle(r, 0, w - r, h, fill=color, outline=color)
        self.create_rectangle(0, r, w, h - r, fill=color, outline=color)

        # 3. Draw the text
        self.create_text(w / 2, h / 2, text=self.text, fill="white", font=("Segoe UI", 11))

    def _on_click(self, event):
        """
        This function is about running the command when the button is clicked inside its area.
        The variable used in this code are:
        event: the mouse release event

        The flow process of this codes are as follows:
        1. Run the command only if the button is enabled and the release happened on the button

        The result of this function are as follows:
        (none)
        """

        # 1. Run the command if enabled and released inside the button
        if self.enabled and 0 <= event.x <= int(self["width"]) and 0 <= event.y <= int(self["height"]):
            self.command()

    def config(self, text=None, state=None):
        """
        This function is about changing the button text or enabled state like a normal button.
        The variable used in this code are:
        text: the new text, or None to keep it
        state: "normal" or "disabled", or None to keep it

        The flow process of this codes are as follows:
        1. Store the new text and state
        2. Redraw with the matching colour and cursor

        The result of this function are as follows:
        (none)
        """

        # 1. Store the new text and state
        if text is not None:
            self.text = text
        if state is not None:
            self.enabled = state == "normal"

        # 2. Redraw
        self._draw(BLUE if self.enabled else BLUE_DISABLED)
        super().config(cursor="hand2" if self.enabled else "arrow")


class App:
    def __init__(self, root):
        """
        This function is about setting up the GUI window, its widgets, and initial state.
        The variable used in this code are:
        root: the tkinter root window

        The flow process of this codes are as follows:
        1. Store the root window and initialize state (IDLE) and a thread-safe message queue
        2. Detect whether a usable GPU is available (only offer the GPU option if so)
        3. Build and lay out all widgets (output folder, model check, device choice, timer,
           start button, status, progress bar, saved-path label)
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
        self.txt_path = None

        # 2. Detect whether a usable GPU is available
        self.gpu_available = is_gpu_available()
        self.device_var = tk.StringVar(value="cuda" if self.gpu_available else "cpu")

        # 3. Build and lay out all widgets
        self._apply_style()
        self.root.configure(bg="white")
        self.root.minsize(WINDOW_WIDTH, 1)
        body = ttk.Frame(root, padding=(16, 16, 14, 24))
        body.pack(fill="both", expand=True)

        folder_row = ttk.Frame(body)
        folder_row.pack(fill="x")
        ttk.Label(folder_row, text="Output Folder").pack(side="left")
        self.browse_button = ttk.Button(folder_row, text="Browse", width=8, command=self.on_browse)
        self.browse_button.pack(side="right")
        self.folder_var = tk.StringVar(value=self._short_path(self.output_dir))
        self.folder_entry = ttk.Entry(folder_row, textvariable=self.folder_var, validate="key", validatecommand=lambda: False)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(12, 10), ipady=3)

        model_row = ttk.Frame(body)
        model_row.pack(fill="x", pady=(12, 0))
        self.check_button = ttk.Button(model_row, text="Check Model", width=12, command=self.on_check_model)
        self.check_button.pack(side="left")
        self.model_dot = tk.Canvas(model_row, width=12, height=12, bg=self.root.cget("bg"), highlightthickness=0)
        self.model_dot.pack(side="left", padx=(16, 6))
        self.model_dot_id = self.model_dot.create_oval(1, 1, 11, 11, fill="#22A722", outline="")
        self.model_label = ttk.Label(model_row, text="")
        self.model_label.pack(side="left")

        self.device_frame = ttk.Frame(body)
        self.device_frame.pack(anchor="w", pady=(14, 0))
        ttk.Label(self.device_frame, text="Device:").pack(side="left")
        if self.gpu_available:
            self.gpu_radio = ttk.Radiobutton(self.device_frame, text="GPU", variable=self.device_var, value="cuda")
            self.gpu_radio.pack(side="left", padx=(6, 0))
        else:
            self.gpu_radio = None
        self.cpu_radio = ttk.Radiobutton(self.device_frame, text="CPU", variable=self.device_var, value="cpu")
        self.cpu_radio.pack(side="left", padx=(6, 0))

        self.timer_label = ttk.Label(body, text="00:00", font=("Segoe UI", 28))
        self.timer_label.pack(pady=(8, 2))

        self.toggle_button = RoundedButton(body, text="Start Recording", command=self.on_toggle)
        self.toggle_button.pack(pady=(4, 8))

        self.status_label = ttk.Label(body, text="Idle", wraplength=410, justify="center")
        self.status_label.pack()

        self.progress_bar = ttk.Progressbar(body, mode="determinate", maximum=100)
        self.progress_bar.pack(fill="x", pady=(8, 0))

        footer = ttk.Frame(body)
        footer.pack(fill="x")
        self.progress_label = ttk.Label(footer, text="")
        self.progress_label.grid(row=0, column=0)
        self.saved_label = ttk.Label(footer, text="", wraplength=410, justify="center")
        self.saved_label.grid(row=1, column=0)
        footer.columnconfigure(0, weight=1)
        self.progress_label.grid_remove()
        self.saved_label.grid_remove()
        self.on_check_model()

        # 4. Start polling the message queue for updates from background threads
        self.root.after(150, self.poll_queue)

    def _apply_style(self):
        """
        This function is about giving the ttk widgets the native Windows look.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Switch to the native Windows theme (grey background and native radio buttons like v1)
        2. Set white backgrounds and the same font on labels, radios and buttons

        The result of this function are as follows:
        (none)
        """
        style = ttk.Style()

        # 1. Switch to the native Windows theme
        style.theme_use("vista")

        # 2. White backgrounds and the same font on labels, radios and buttons
        for name in ("TFrame", "TLabel", "TRadiobutton"):
            style.configure(name, background="white")
            style.map(name, background=[("active", "white")])
        for name in ("TLabel", "TRadiobutton", "TButton"):
            style.configure(name, font=("Segoe UI", 9))

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
        self.model_dot.itemconfig(self.model_dot_id, fill="#22A722" if found else "#D93025")
        self.model_label.config(text="Model found" if found else "Model not found")

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
        2. Reset the UI (timer, status, progress, saved label)
        3. Start the recording worker thread and the live timer tick

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
        self._set_setup_controls("disabled")

        # 3. Start the recording worker thread and the live timer tick
        self.tick_timer()
        threading.Thread(target=self._record_worker, daemon=True).start()

    def _record_worker(self):
        """
        This function is about running the blocking recording call off the main thread.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Call record_system_audio with the session's stop_event
        2. Notify the main thread that recording has finished (or that an error occurred)

        The result of this function are as follows:
        (none, communicates via self.msg_queue)
        """
        try:
            # 1. Call record_system_audio with the session's stop_event
            record_system_audio(self.wav_path, stop_event=self.stop_event)

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
        2. Apply the corresponding widget updates for each message type
        3. Reschedule itself to run again shortly

        The result of this function are as follows:
        (none)
        """
        try:
            # 1. Pull every pending message from the queue without blocking
            while True:
                event, payload = self.msg_queue.get_nowait()

                # 2. Apply the corresponding widget updates for each message type
                if event == "recording_done":
                    self.last_recording_seconds = time.time() - self.start_time
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
                elif event == "empty":
                    self.state = "IDLE"
                    self.status_label.config(text="No speech detected (even without VAD)")
                    self._set_text(self.saved_label, f"{self._short_recording_note()}Transcript was empty. WAV kept at: {payload}")
                    self._reenable_controls()
                elif event == "error":
                    self.state = "IDLE"
                    self.status_label.config(text=f"Error: {payload}")
                    self._reenable_controls()
        except queue.Empty:
            pass

        # 3. Reschedule itself to run again shortly
        self.root.after(150, self.poll_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
