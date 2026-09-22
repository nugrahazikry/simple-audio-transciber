import wave
import threading
import numpy as np
import pyaudiowpatch as pyaudio
import lameenc

CHUNK = 1024


def _keep_device_awake(audio, render_device, sample_format, stop_event):
    """
    This function is about writing silence to the real output device so Windows doesn't see it
    as idle and power it down mid-recording, which breaks WASAPI loopback capture on long sessions.
    The variable used in this code are:
    audio: the open PyAudio instance
    render_device: device info dict for the actual playback device (not the loopback pseudo-device)
    sample_format: PyAudio sample format to open the stream with
    stop_event: threading.Event that signals when to stop writing and exit

    The flow process of this codes are as follows:
    1. Open a real playback stream on the render device
    2. Continuously write silent (zero) audio to it until stop_event is set
    3. Close the stream on exit

    The result of this function are as follows:
    (none, runs until stop_event is set)
    """
    out_channels = render_device["maxOutputChannels"]
    out_rate = int(render_device["defaultSampleRate"])

    # 1. Open a real playback stream on the render device
    keepalive_stream = audio.open(
        format=sample_format,
        channels=out_channels,
        rate=out_rate,
        output=True,
        output_device_index=render_device["index"],
        frames_per_buffer=CHUNK,
    )
    silence = b"\x00" * (CHUNK * out_channels * audio.get_sample_size(sample_format))

    # 2. Continuously write silent audio until stop_event is set
    try:
        while not stop_event.is_set():
            keepalive_stream.write(silence)
    finally:
        # 3. Close the stream on exit
        keepalive_stream.stop_stream()
        keepalive_stream.close()


def record_system_audio(output_path, stop_event=None):
    """
    This function is about recording the laptop's system audio output (speaker/loopback) until stopped.
    The variable used in this code are:
    output_path: path where the recorded WAV file will be saved
    stop_event: threading.Event used to signal stop (e.g. from a GUI); if not given, a local one is
    used and recording continues until Ctrl+C (CLI use)

    The flow process of this codes are as follows:
    1. Open PyAudio and find the real render device plus its matching WASAPI loopback device
    2. Open an input stream on the loopback device, and start a background thread writing silence
       to the real render device so Windows doesn't power it down as "idle" during long recordings
    3. Read audio chunks in a loop until stop_event is set (or Ctrl+C in CLI use)
    4. Stop the keep-alive thread, then write all collected chunks to a WAV file at output_path

    The result of this function are as follows:
    output_path: the path of the saved WAV file, same as the input argument
    """
    if stop_event is None:
        stop_event = threading.Event()

    with pyaudio.PyAudio() as audio:

        # 1. Open PyAudio and find the real render device plus its matching loopback device
        wasapi_info = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
        render_device = audio.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        loopback_device = render_device
        if not loopback_device["isLoopbackDevice"]:
            for loopback in audio.get_loopback_device_info_generator():
                if render_device["name"] in loopback["name"]:
                    loopback_device = loopback
                    break
            else:
                raise RuntimeError("No loopback device found for default speakers")

        channels = loopback_device["maxInputChannels"]
        sample_rate = int(loopback_device["defaultSampleRate"])
        sample_format = pyaudio.paInt16

        # 2. Open the loopback input stream and start the keep-alive background thread
        stream = audio.open(
            format=sample_format,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=loopback_device["index"],
            frames_per_buffer=CHUNK,
        )
        keepalive_thread = threading.Thread(
            target=_keep_device_awake, args=(audio, render_device, sample_format, stop_event), daemon=True
        )
        keepalive_thread.start()

        print(f"Recording system audio from: {loopback_device['name']}")
        print("Press Ctrl+C to stop recording...")

        # 3. Read audio chunks in a loop until stop_event is set (or Ctrl+C in CLI use)
        frames = []
        try:
            while not stop_event.is_set():
                data = stream.read(CHUNK)
                frames.append(data)
        except KeyboardInterrupt:
            print("Recording stopped.")
        finally:
            stop_event.set()
            stream.stop_stream()
            stream.close()
            keepalive_thread.join(timeout=2)

        # 4. Write all collected chunks to a WAV file at output_path
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(audio.get_sample_size(sample_format))
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(frames))

    return output_path


def convert_wav_to_mp3(wav_path, mp3_path):
    """
    This function is about converting a WAV file to a smaller, mono, 64kbps MP3 file for storage.
    The variable used in this code are:
    wav_path: path to the source WAV file
    mp3_path: path where the encoded MP3 file will be saved

    The flow process of this codes are as follows:
    1. Read the WAV file's PCM audio data and its channel/sample rate info
    2. Downmix stereo to mono by averaging channels (loopback audio has little real stereo content)
    3. Encode the mono PCM data to MP3 at 64kbps using lameenc
    4. Write the encoded MP3 bytes to mp3_path

    The result of this function are as follows:
    mp3_path: the path of the saved MP3 file, same as the input argument
    """

    # 1. Read the WAV file's PCM audio data and its channel/sample rate info
    with wave.open(wav_path, "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        pcm_data = wf.readframes(wf.getnframes())

    # 2. Downmix stereo to mono by averaging channels
    if channels > 1:
        samples = np.frombuffer(pcm_data, dtype=np.int16).reshape(-1, channels)
        pcm_data = samples.mean(axis=1).astype(np.int16).tobytes()
        channels = 1

    # 3. Encode the mono PCM data to MP3 at 64kbps using lameenc
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(64)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(channels)
    encoder.set_quality(2)

    mp3_data = encoder.encode(pcm_data)
    mp3_data += encoder.flush()

    # 4. Write the encoded MP3 bytes to mp3_path
    with open(mp3_path, "wb") as f:
        f.write(mp3_data)

    return mp3_path
