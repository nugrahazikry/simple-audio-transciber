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
from transcribe import transcribe_audio

OUTPUT_DIR = "output"


class App:
    def __init__(self, root):
        """
        This function is about setting up the GUI window, its widgets, and initial state.
        The variable used in this code are:
        root: the tkinter root window

        The flow process of this codes are as follows:
        1. Store the root window and initialize state (IDLE) and a thread-safe message queue
        2. Build and lay out all widgets (button, timer, status, progress bar, saved-path label)
        3. Start polling the message queue for updates from background threads

        The result of this function are as follows:
        (none, builds the running GUI)
        """
        self.root = root
        self.root.title("Audio Transcriber")
        self.root.geometry("300x220")
        self.root.resizable(False, False)

        self.state = "IDLE"
        self.stop_event = None
        self.msg_queue = queue.Queue()
        self.start_time = None
        self.session_dir = None
        self.wav_path = None
        self.txt_path = None

        self.toggle_button = ttk.Button(root, text="Start Recording", command=self.on_toggle)
        self.toggle_button.pack(pady=(15, 5))

        self.timer_label = ttk.Label(root, text="00:00", font=("Segoe UI", 20))
        self.timer_label.pack(pady=5)

        self.status_label = ttk.Label(root, text="Idle")
        self.status_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(root, mode="determinate", maximum=100, length=250)
        self.progress_bar.pack(pady=5)

        self.progress_label = ttk.Label(root, text="")
        self.progress_label.pack()

        self.saved_label = ttk.Label(root, text="", wraplength=280, justify="center")
        self.saved_label.pack(pady=5)

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
        if self.state in ("IDLE", "DONE"):
            self.start_recording()
        elif self.state == "RECORDING":
            self.stop_recording()

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
        date_str = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(OUTPUT_DIR, date_str, timestamp)
        os.makedirs(self.session_dir, exist_ok=True)
        self.wav_path = os.path.join(self.session_dir, f"{timestamp}_recording.wav")
        self.mp3_path = os.path.join(self.session_dir, f"{timestamp}_recording.mp3")
        self.txt_path = os.path.join(self.session_dir, f"{timestamp}_transcript.txt")

        self.stop_event = threading.Event()
        self.state = "RECORDING"
        self.toggle_button.config(text="Stop")
        self.status_label.config(text="Recording...")
        self.saved_label.config(text="")
        self.progress_bar["value"] = 0
        self.progress_label.config(text="")
        self.start_time = time.time()
        self.tick_timer()

        threading.Thread(target=self._record_worker, daemon=True).start()

    def _record_worker(self):
        """
        This function is about running the blocking recording call off the main thread.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Call record_system_audio with the session's stop_event
        2. Notify the main thread that recording has finished

        The result of this function are as follows:
        (none, communicates via self.msg_queue)
        """
        record_system_audio(self.wav_path, stop_event=self.stop_event)
        self.msg_queue.put(("recording_done", None))

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
        self.stop_event.set()
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
        if self.state != "RECORDING":
            return
        elapsed = int(time.time() - self.start_time)
        minutes, seconds = divmod(elapsed, 60)
        self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
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
        self.state = "TRANSCRIBING"
        self.status_label.config(text="Transcribing...")
        threading.Thread(target=self._transcribe_worker, daemon=True).start()

    def _transcribe_worker(self):
        """
        This function is about running transcription off the main thread and cleaning up the WAV file.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Transcribe the WAV file, reporting progress through the message queue
        2. If the transcript is non-empty, convert the WAV to a smaller MP3 and delete the WAV
        3. Notify the main thread that the session is done (or that an error occurred)

        The result of this function are as follows:
        (none, communicates via self.msg_queue)
        """
        try:
            def on_progress(pct):
                self.msg_queue.put(("progress", pct))

            _, saved_txt_path = transcribe_audio(self.wav_path, self.txt_path, progress_callback=on_progress)

            with open(saved_txt_path, "r", encoding="utf-8") as f:
                transcript_content = f.read().strip()

            if transcript_content:
                convert_wav_to_mp3(self.wav_path, self.mp3_path)
                os.remove(self.wav_path)

            self.msg_queue.put(("done", self.session_dir))
        except Exception as e:
            self.msg_queue.put(("error", str(e)))

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
            while True:
                event, payload = self.msg_queue.get_nowait()
                if event == "recording_done":
                    self.begin_transcription()
                elif event == "progress":
                    self.progress_bar["value"] = payload
                    self.progress_label.config(text=f"{round(payload)}%")
                elif event == "done":
                    self.state = "DONE"
                    self.status_label.config(text="Done")
                    self.saved_label.config(text=f"Last saved: {payload}")
                    self.toggle_button.config(text="Start Recording", state="normal")
                elif event == "error":
                    self.state = "IDLE"
                    self.status_label.config(text=f"Error: {payload}")
                    self.toggle_button.config(text="Start Recording", state="normal")
        except queue.Empty:
            pass
        self.root.after(150, self.poll_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
