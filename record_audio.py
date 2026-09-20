import wave
import threading
import numpy as np
import pyaudiowpatch as pyaudio
import lameenc

CHUNK = 1024


def record_system_audio(output_path, stop_event=None):
    """
    This function is about recording the laptop's system audio output (speaker/loopback) until stopped.
    The variable used in this code are:
    output_path: path where the recorded WAV file will be saved
    stop_event: threading.Event used to signal stop (e.g. from a GUI); if not given, a local one is
    used and recording continues until Ctrl+C (CLI use)

    The flow process of this codes are as follows:
    1. Open PyAudio and find the default WASAPI loopback device
    2. Open an input stream on that loopback device
    3. Read audio chunks in a loop until stop_event is set (or Ctrl+C in CLI use)
    4. Write all collected chunks to a WAV file at output_path

    The result of this function are as follows:
    output_path: the path of the saved WAV file, same as the input argument
    """
    if stop_event is None:
        stop_event = threading.Event()

    with pyaudio.PyAudio() as audio:
        wasapi_info = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = audio.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        if not default_speakers["isLoopbackDevice"]:
            for loopback in audio.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    default_speakers = loopback
                    break
            else:
                raise RuntimeError("No loopback device found for default speakers")

        channels = default_speakers["maxInputChannels"]
        sample_rate = int(default_speakers["defaultSampleRate"])
        sample_format = pyaudio.paInt16

        stream = audio.open(
            format=sample_format,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=default_speakers["index"],
            frames_per_buffer=CHUNK,
        )

        print(f"Recording system audio from: {default_speakers['name']}")
        print("Press Ctrl+C to stop recording...")

        frames = []
        try:
            while not stop_event.is_set():
                data = stream.read(CHUNK)
                frames.append(data)
        except KeyboardInterrupt:
            print("Recording stopped.")
        finally:
            stream.stop_stream()
            stream.close()

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
    with wave.open(wav_path, "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        pcm_data = wf.readframes(wf.getnframes())

    if channels > 1:
        samples = np.frombuffer(pcm_data, dtype=np.int16).reshape(-1, channels)
        pcm_data = samples.mean(axis=1).astype(np.int16).tobytes()
        channels = 1

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(64)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(channels)
    encoder.set_quality(2)

    mp3_data = encoder.encode(pcm_data)
    mp3_data += encoder.flush()

    with open(mp3_path, "wb") as f:
        f.write(mp3_data)

    return mp3_path
