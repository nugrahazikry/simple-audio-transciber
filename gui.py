import os
import queue
import threading
import time
import tkinter as tk
import warnings
from datetime import datetime
from tkinter import ttk

warnings.filterwarnings("ignore")

from dotenv import load_dotenv

load_dotenv()

from record_audio import record_system_audio, convert_wav_to_mp3
from transcribe import transcribe_audio, is_gpu_available

OUTPUT_DIR = "output"


class App:
    def __init__(self, root):
        """
        This function is about setting up the GUI window, its widgets, and initial state.
        The variable used in this code are:
        root: the tkinter root window

        The flow process of this codes are as follows:
        1. Store the root window and initialize state (IDLE) and a thread-safe message queue
        2. Detect whether a usable GPU is available (only offer the GPU option if so)
        3. Build and lay out all widgets (button, device choice, timer, status, progress bar,
           saved-path label)
        4. Start polling the message queue for updates from background threads

        The result of this function are as follows:
        (none, builds the running GUI)
        """

        # 1. Store the root window and initialize state and a thread-safe message queue
        self.root = root
        self.root.title("Audio Transcriber")
        self.root.geometry("300x250")
        self.root.resizable(False, False)

        self.state = "IDLE"
        self.stop_event = None
        self.msg_queue = queue.Queue()
        self.start_time = None
        self.session_dir = None
        self.wav_path = None
        self.txt_path = None

        # 2. Detect whether a usable GPU is available
        self.gpu_available = is_gpu_available()
        self.device_var = tk.StringVar(value="cuda" if self.gpu_available else "cpu")

        # 3. Build and lay out all widgets
        self.toggle_button = ttk.Button(root, text="Start Recording", command=self.on_toggle)
        self.toggle_button.pack(pady=(15, 5))

        device_frame = ttk.Frame(root)
        device_frame.pack(pady=2)
        ttk.Label(device_frame, text="Device:").pack(side="left")
        if self.gpu_available:
            self.gpu_radio = ttk.Radiobutton(device_frame, text="GPU", variable=self.device_var, value="cuda")
            self.gpu_radio.pack(side="left")
        else:
            self.gpu_radio = None
        self.cpu_radio = ttk.Radiobutton(device_frame, text="CPU", variable=self.device_var, value="cpu")
        self.cpu_radio.pack(side="left")

        self.timer_label = ttk.Label(root, text="00:00", font=("Segoe UI", 20))
        self.timer_label.pack(pady=5)

        self.status_label = ttk.Label(root, text="Idle", wraplength=280, justify="center")
        self.status_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(root, mode="determinate", maximum=100, length=250)
        self.progress_bar.pack(pady=5)

        self.progress_label = ttk.Label(root, text="")
        self.progress_label.pack()

        self.saved_label = ttk.Label(root, text="", wraplength=280, justify="center")
        self.saved_label.pack(pady=5)

        # 4. Start polling the message queue for updates from background threads
        self.root.after(150, self.poll_queue)

    def on_toggle(self):
        """
        This function is about handling the Start/Stop button click based on current state.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. If idle or done, start a new recording session
        2. If recording, stop it

        The result of this function are as follows:
        (none)
        """

        # 1. If idle or done, start a new recording session
        if self.state in ("IDLE", "DONE"):
            self.start_recording()

        # 2. If recording, stop it
        elif self.state == "RECORDING":
            self.stop_recording()

    def _reenable_controls(self):
        """
        This function is about restoring the button and device controls after a session ends.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Re-enable the Start Recording button
        2. Re-enable the device radiobuttons so the device can be changed before the next session

        The result of this function are as follows:
        (none)
        """

        # 1. Re-enable the Start Recording button
        self.toggle_button.config(text="Start Recording", state="normal")

        # 2. Re-enable the device radiobuttons
        if self.gpu_radio:
            self.gpu_radio.config(state="normal")
        self.cpu_radio.config(state="normal")

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
        self.session_dir = os.path.join(OUTPUT_DIR, date_str, timestamp)
        os.makedirs(self.session_dir, exist_ok=True)
        self.wav_path = os.path.join(self.session_dir, f"{timestamp}_recording.wav")
        self.mp3_path = os.path.join(self.session_dir, f"{timestamp}_recording.mp3")
        self.txt_path = os.path.join(self.session_dir, f"{timestamp}_transcript.txt")

        # 2. Reset the UI
        self.stop_event = threading.Event()
        self.state = "RECORDING"
        self.toggle_button.config(text="Stop")
        self.status_label.config(text="Recording...")
        self.saved_label.config(text="")
        self.progress_bar["value"] = 0
        self.progress_label.config(text="")
        self.start_time = time.time()
        if self.gpu_radio:
            self.gpu_radio.config(state="disabled")
        self.cpu_radio.config(state="disabled")

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
        1. Set the stop_event so the recording loop exits
        2. Disable the button and show a transitional status until transcription begins

        The result of this function are as follows:
        (none)
        """

        # 1. Set the stop_event so the recording loop exits
        self.stop_event.set()

        # 2. Disable the button and show a transitional status
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
                    self.begin_transcription()
                elif event == "status":
                    self.status_label.config(text=payload)
                elif event == "progress":
                    self.progress_bar["value"] = payload
                    self.progress_label.config(text=f"{round(payload)}%")
                elif event == "done":
                    session_dir, used_fallback = payload
                    self.state = "DONE"
                    if used_fallback:
                        self.status_label.config(text="Done (recovered without VAD)")
                        self.saved_label.config(text=f"Please verify accuracy — silence can hallucinate. Last saved: {session_dir}")
                    else:
                        self.status_label.config(text="Done")
                        self.saved_label.config(text=f"Last saved: {session_dir}")
                    self._reenable_controls()
                elif event == "empty":
                    self.state = "IDLE"
                    self.status_label.config(text="No speech detected (even without VAD)")
                    self.saved_label.config(text=f"Transcript was empty. WAV kept at: {payload}")
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
