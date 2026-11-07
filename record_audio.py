import wave
import threading
import numpy as np
import pyaudiowpatch as pyaudio
import lameenc

CHUNK = 1024
LEVEL_FULL_SCALE = 8000
MIX_BLOCK = 480000


def _chunk_level(data):
    """
    This function is about turning one chunk of recorded audio into a loudness value for the waveform.
    The variable used in this code are:
    data: raw 16-bit audio bytes read from the stream

    The flow process of this codes are as follows:
    1. Convert the bytes to samples
    2. Compute the average loudness (RMS) and scale it to 0.0-1.0

    The result of this function are as follows:
    level: loudness from 0.0 (silent) to 1.0 (loud)
    """

    # 1. Convert the bytes to samples
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)

    # 2. Compute the RMS loudness and scale it to 0.0-1.0
    rms = float(np.sqrt(np.mean(samples**2))) if samples.size else 0.0
    return min(1.0, rms / LEVEL_FULL_SCALE)


def _mix_microphone(loopback_data, loopback_channels, mic_data, mic_channels):
    """
    This function is about mixing the recorded microphone audio into the recorded system audio.
    The variable used in this code are:
    loopback_data: raw 16-bit system audio bytes (interleaved channels)
    loopback_channels: number of channels in loopback_data
    mic_data: raw 16-bit microphone audio bytes (interleaved channels, may use another sample rate)
    mic_channels: number of channels in mic_data

    The flow process of this codes are as follows:
    1. Convert both recordings to samples and downmix the microphone to mono
    2. Stretch the microphone to the system audio length (this fixes the different sample rates and
       any clock drift), working in blocks to keep memory low
    3. Add the microphone to every system channel and clip to the 16-bit range

    The result of this function are as follows:
    mixed: the mixed 16-bit audio bytes, same length and format as loopback_data
    """

    # 1. Convert both recordings to samples and downmix the microphone to mono
    mixed = bytearray(loopback_data)
    loop = np.frombuffer(mixed, dtype=np.int16).reshape(-1, loopback_channels)
    mic_usable = len(mic_data) - len(mic_data) % (2 * mic_channels)
    mic = np.frombuffer(mic_data[:mic_usable], dtype=np.int16).reshape(-1, mic_channels)
    mic = mic.astype(np.float32).mean(axis=1)
    loop_len, mic_len = len(loop), len(mic)
    if loop_len < 2 or mic_len < 2:
        return mixed

    # 2. Stretch the microphone to the system audio length, block by block
    ratio = (mic_len - 1) / (loop_len - 1)
    for start in range(0, loop_len, MIX_BLOCK):
        end = min(start + MIX_BLOCK, loop_len)
        position = np.arange(start, end) * ratio
        first = position.astype(np.int64)
        second = np.minimum(first + 1, mic_len - 1)
        fraction = (position - first).astype(np.float32)
        mic_block = mic[first] * (1 - fraction) + mic[second] * fraction

        # 3. Add the microphone to every system channel and clip to the 16-bit range
        total = loop[start:end].astype(np.int32) + mic_block[:, None].astype(np.int32)
        loop[start:end] = np.clip(total, -32768, 32767).astype(np.int16)

    return mixed


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


def record_system_audio(output_path, stop_event=None, level_callback=None, use_mic=False, mic_on_event=None):
    """
    This function is about recording the laptop's system audio output (speaker/loopback) until
    stopped, and optionally mixing in the default microphone.
    The variable used in this code are:
    output_path: path where the recorded WAV file will be saved
    stop_event: threading.Event used to signal stop (e.g. from a GUI); if not given, a local one is
    used and recording continues until Ctrl+C (CLI use)
    level_callback: optional function called with a 0.0-1.0 loudness value for every chunk read
    (used by the GUI waveform, the louder of system audio and microphone); if not given, nothing
    extra happens
    use_mic: True to also record the default microphone and mix it into the same WAV (if no
    microphone can be used, recording continues with system audio only); False (the default)
    records system audio only, as before
    mic_on_event: optional threading.Event used as a live on/off switch for the microphone: while
    it is set the microphone is recorded, while it is clear that moment is silence; if not given,
    the microphone is always on (only matters when use_mic is True)

    The flow process of this codes are as follows:
    1. Open PyAudio and find the real render device plus its matching WASAPI loopback device
    2. If use_mic, try to open the default microphone first (if that fails, carry on without it),
       then open an input stream on the loopback device, and start a background thread
       writing silence to the real render device so Windows doesn't power it down as "idle"
    3. Read audio chunks in a loop until stop_event is set (or Ctrl+C in CLI use), reporting each
       chunk's loudness to level_callback when one is given; the microphone is collected in the
       background by its own callback
    4. Stop the microphone and keep-alive thread, mix the microphone into the system audio when
       use_mic, then write the result to a WAV file at output_path

    The result of this function are as follows:
    output_path: the path of the saved WAV file, same as the input argument
    """
    if stop_event is None:
        stop_event = threading.Event()

    mic_frames = []
    mic_state = {"level": 0.0}

    def on_mic_audio(in_data, frame_count, time_info, status):
        """
        This function is about collecting one microphone chunk in the background.
        The variable used in this code are:
        in_data: raw 16-bit microphone audio bytes
        frame_count, time_info, status: values PyAudio passes to every callback (not used)

        The flow process of this codes are as follows:
        1. If the microphone switch is on, store the chunk and remember the loudest level since the
           last waveform update
        2. If the switch is off, store silence of the same length so the timeline stays correct

        The result of this function are as follows:
        (None, paContinue): tells PyAudio to keep the stream running
        """

        # 1. Switch on: store the chunk and remember the loudest level
        if mic_on_event is None or mic_on_event.is_set():
            mic_frames.append(in_data)
            mic_state["level"] = max(mic_state["level"], _chunk_level(in_data))

        # 2. Switch off: store silence of the same length
        else:
            mic_frames.append(bytes(len(in_data)))
        return (None, pyaudio.paContinue)

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

        # 2. Open the microphone (if wanted), the loopback input stream, and the keep-alive thread
        mic_stream = None
        if use_mic:
            try:
                mic_index = wasapi_info["defaultInputDevice"]
                if mic_index < 0:
                    raise RuntimeError("No microphone found")
                mic_device = audio.get_device_info_by_index(mic_index)
                mic_channels = min(2, mic_device["maxInputChannels"])
                if mic_channels < 1:
                    raise RuntimeError("No microphone found")
                mic_stream = audio.open(
                    format=sample_format,
                    channels=mic_channels,
                    rate=int(mic_device["defaultSampleRate"]),
                    input=True,
                    input_device_index=mic_device["index"],
                    frames_per_buffer=CHUNK,
                    stream_callback=on_mic_audio,
                    start=False,
                )
            except Exception as e:
                # keep recording system audio even if the microphone can't be used
                mic_stream = None
                print(f"Microphone not used: {e}")

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
        if mic_stream:
            try:
                mic_stream.start_stream()
            except Exception as e:
                mic_stream.close()
                mic_stream = None
                print(f"Microphone not used: {e}")

        print(f"Recording system audio from: {loopback_device['name']}")
        print("Press Ctrl+C to stop recording...")

        # 3. Read audio chunks in a loop until stop_event is set (or Ctrl+C in CLI use)
        frames = []
        try:
            while not stop_event.is_set():
                data = stream.read(CHUNK)
                frames.append(data)
                if level_callback:
                    level = _chunk_level(data)
                    if mic_stream:
                        level = max(level, mic_state["level"])
                        mic_state["level"] = 0.0
                    level_callback(level)
        except KeyboardInterrupt:
            print("Recording stopped.")
        finally:
            stop_event.set()
            stream.stop_stream()
            stream.close()
            if mic_stream:
                mic_stream.stop_stream()
                mic_stream.close()
            keepalive_thread.join(timeout=2)

        # 4. Mix the microphone into the system audio (if used), then write the WAV file
        audio_data = b"".join(frames)
        if mic_stream:
            audio_data = _mix_microphone(audio_data, channels, b"".join(mic_frames), mic_channels)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(audio.get_sample_size(sample_format))
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)

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
