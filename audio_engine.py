import asyncio
import fractions
import math
import logging
import numpy as np
import audioop
import av
from aiortc.mediastreams import AudioStreamTrack

# Use PyAudioWPatch for native Windows WASAPI loopback if available
try:
    import pyaudiowpatch as pyaudio
    HAS_WASAPI_LOOPBACK = True
except ImportError:
    import pyaudio
    HAS_WASAPI_LOOPBACK = False

logger = logging.getLogger("audio_engine")
logging.basicConfig(level=logging.INFO)

class PCMAudioStreamTrack(AudioStreamTrack):
    """
    WebRTC Audio Track that streams captured PCM audio frames encoded to Opus.
    Uses a minimal queue (maxsize=2) to guarantee strictly zero latency accumulation.
    """
    kind = "audio"

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.queue = asyncio.Queue(maxsize=2)  # Max 20ms buffer (2 x 10ms)
        self._timestamp = 0
        self.sample_rate = engine.sample_rate
        self.channels = engine.channels
        self.chunk_size = engine.chunk_size
        self._silence_frame = b"\x00" * (self.chunk_size * self.channels * 2)

    async def recv(self):
        try:
            pcm_bytes = await asyncio.wait_for(self.queue.get(), timeout=0.05)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pcm_bytes = self._silence_frame

        samples = len(pcm_bytes) // (2 * self.channels)
        layout = "stereo" if self.channels == 2 else "mono"

        frame = av.AudioFrame(format="s16", layout=layout, samples=samples)
        frame.planes[0].update(pcm_bytes)
        frame.sample_rate = self.sample_rate
        frame.time_base = fractions.Fraction(1, self.sample_rate)
        frame.pts = self._timestamp
        self._timestamp += samples

        return frame


class AudioEngine:
    def __init__(self, sample_rate: int = 48000, channels: int = 2, chunk_size: int = 480):
        self.sample_rate = sample_rate  # Target output rate (48 kHz)
        self.channels = channels        # Target channels (2 stereo)
        self.chunk_size = chunk_size    # 480 samples @ 48kHz = exactly 10.0 ms

        self.p = pyaudio.PyAudio()
        self.stream = None
        self.device_index = None
        self.device_name = "Unknown"
        self.device_sample_rate = sample_rate
        self.is_running = False
        self._ratecv_state = None

        self.webrtc_tracks = set()
        self.websocket_queues = set()
        self.http_queues = set()

        self.loop = None
        self.current_rms = 0.0
        self.current_peak = 0.0
        self.total_frames_captured = 0

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def get_default_loopback_device(self):
        """Find the native WASAPI Loopback device for the Windows default output speakers."""
        if not HAS_WASAPI_LOOPBACK:
            return None
        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = self.p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            for loopback in self.p.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    return loopback
            # Fallback to first available loopback device
            for loopback in self.p.get_loopback_device_info_generator():
                return loopback
        except Exception as e:
            logger.debug(f"WASAPI loopback query notice: {e}")
        return None

    def get_input_devices(self):
        """
        Returns a clean, simplified, and non-confusing list of audio sources.
        Puts [DEFAULT] PC Audio (What You Hear) at the top.
        """
        curated = []
        seen_names = set()

        # 1. Add Default PC Audio Loopback (Zero Cable Needed!)
        loopback = self.get_default_loopback_device()
        if loopback:
            curated.append({
                "index": loopback["index"],
                "name": "[Default] PC Audio (What You Hear - No Cable Needed)",
                "isDefault": True,
                "isLoopback": True,
                "channels": 2,
                "defaultSampleRate": int(loopback.get("defaultSampleRate", 48000))
            })
            seen_names.add("pc audio")

        # 2. Add Stereo Mix, VB-Cable, and Microphone cleanly without duplicates
        ignored_keywords = ["mapper", "primary", "wdm-ks", "input ()", "point", "line in"]
        device_count = self.p.get_device_count()

        for i in range(device_count):
            try:
                info = self.p.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0 and not info.get("isLoopbackDevice", False):
                    raw_name = info["name"].strip()
                    lower_name = raw_name.lower()

                    if any(k in lower_name for k in ignored_keywords):
                        continue

                    clean_name = raw_name
                    if "cable" in lower_name:
                        clean_name = "VB-Audio Virtual Cable"
                    elif "stereo mix" in lower_name:
                        clean_name = "Stereo Mix (Realtek)"
                    elif "microphone" in lower_name:
                        clean_name = "Microphone (PC Mic)"
                    elif "aux" in lower_name or "fxsound" in lower_name:
                        clean_name = "FxSound Audio"

                    if clean_name not in seen_names:
                        seen_names.add(clean_name)
                        curated.append({
                            "index": i,
                            "name": clean_name,
                            "isDefault": False,
                            "isLoopback": False,
                            "channels": min(2, info.get("maxInputChannels", 2)),
                            "defaultSampleRate": int(info.get("defaultSampleRate", 48000))
                        })
            except Exception:
                pass

        return curated

    def pick_best_device_index(self):
        # 1. Native WASAPI Loopback on Default Output (Best: No cable required!)
        loopback = self.get_default_loopback_device()
        if loopback:
            return loopback["index"]

        # 2. VB-Cable Output
        devices = self.get_input_devices()
        for d in devices:
            if "cable" in d["name"].lower():
                return d["index"]

        # 3. Stereo Mix
        for d in devices:
            if "stereo mix" in d["name"].lower():
                return d["index"]

        # 4. Default input
        try:
            return self.p.get_default_input_device_info()["index"]
        except Exception:
            return devices[0]["index"] if devices else 0

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        Hardware PortAudio thread callback.
        Handles real-time rate conversion if device uses 96kHz or 44.1kHz.
        """
        self.total_frames_captured += 1

        # Resample to 48000 Hz if hardware runs at a different native rate
        if self.device_sample_rate != self.sample_rate:
            try:
                in_data, self._ratecv_state = audioop.ratecv(
                    in_data, 2, self.channels, self.device_sample_rate, self.sample_rate, self._ratecv_state
                )
            except Exception:
                pass

        # Calculate peak and RMS level
        try:
            arr = np.frombuffer(in_data, dtype=np.int16)
            if len(arr) > 0:
                self.current_peak = float(np.max(np.abs(arr))) / 32768.0
                self.current_rms = float(np.sqrt(np.mean(arr.astype(np.float32) ** 2))) / 32768.0
        except Exception:
            pass

        # Dispatch to asyncio loop thread-safely
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._dispatch_to_subscribers, in_data)

        return (None, pyaudio.paContinue)

    def _dispatch_to_subscribers(self, pcm_bytes: bytes):
        """
        Distribute audio bytes to all active subscribers with strictly bounded queues.
        Old frames are discarded if the client is slow, eliminating latency buildup.
        """
        for track in list(self.webrtc_tracks):
            if track.queue.full():
                try:
                    track.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                track.queue.put_nowait(pcm_bytes)
            except asyncio.QueueFull:
                pass

        for q in list(self.websocket_queues):
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(pcm_bytes)
            except asyncio.QueueFull:
                pass

        for q in list(self.http_queues):
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(pcm_bytes)
            except asyncio.QueueFull:
                pass

    def start(self, device_index: int = None, sample_rate: int = 48000, channels: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = int(self.sample_rate * 0.010)  # 480 samples @ 48kHz = 10ms ultra-low latency
        self._ratecv_state = None

        if device_index is None:
            device_index = self.pick_best_device_index()

        self.device_index = device_index
        try:
            dev_info = self.p.get_device_info_by_index(self.device_index)
            raw_name = dev_info.get("name", f"Device {self.device_index}")
            self.device_sample_rate = int(dev_info.get("defaultSampleRate", self.sample_rate))
            is_loopback = dev_info.get("isLoopbackDevice", False)
            if is_loopback:
                self.device_name = "PC Audio (What You Hear)"
            elif "cable" in raw_name.lower():
                self.device_name = "VB-Audio Cable"
            elif "stereo mix" in raw_name.lower():
                self.device_name = "Stereo Mix"
            else:
                self.device_name = raw_name
        except Exception:
            self.device_name = f"Device {self.device_index}"
            self.device_sample_rate = self.sample_rate

        # Buffer frames according to hardware sample rate (10ms)
        hardware_chunk = int(self.device_sample_rate * 0.010)

        logger.info(f"Starting AudioEngine on device [{self.device_index}] '{self.device_name}' "
                    f"at hardware {self.device_sample_rate}Hz -> output {self.sample_rate}Hz {self.channels}ch")

        try:
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.device_sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=hardware_chunk,
                stream_callback=self._audio_callback
            )
            self.stream.start_stream()
            self.is_running = True
            logger.info("Audio capture stream started successfully.")
            return True, "Audio capture stream started successfully."
        except Exception as e:
            logger.warning(f"Failed to open stream on device {self.device_index}: {e}")
            # If the loopback device failed (e.g. no audio playing yet), auto-fallback to Stereo Mix or Cable
            if is_loopback:
                logger.info("WASAPI loopback unavailable, automatically falling back to Stereo Mix / VB-Cable...")
                devices = self.get_input_devices()
                for d in devices:
                    if not d.get("isLoopback", False):
                        logger.info(f"Retrying on fallback device: {d['name']}")
                        return self.start(device_index=d["index"], sample_rate=self.sample_rate, channels=self.channels)
            self.is_running = False
            return False, str(e)

    def stop(self):
        self.is_running = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
            self.stream = None
        logger.info("Audio capture stream stopped.")

    def change_device(self, device_index: int, channels: int = 2, sample_rate: int = 48000):
        self.stop()
        return self.start(device_index=device_index, sample_rate=sample_rate, channels=channels)

    def create_webrtc_track(self):
        track = PCMAudioStreamTrack(self)
        self.webrtc_tracks.add(track)
        return track

    def remove_webrtc_track(self, track):
        self.webrtc_tracks.discard(track)

    def register_websocket_queue(self):
        q = asyncio.Queue(maxsize=6)  # 60ms headroom to prevent server frame drops on minor network/eventloop jitter
        self.websocket_queues.add(q)
        return q

    def unregister_websocket_queue(self, q):
        self.websocket_queues.discard(q)

    def register_http_queue(self):
        q = asyncio.Queue(maxsize=10)
        self.http_queues.add(q)
        return q

    def unregister_http_queue(self, q):
        self.http_queues.discard(q)

    def get_status(self):
        return {
            "isRunning": self.is_running,
            "deviceIndex": self.device_index,
            "deviceName": self.device_name,
            "sampleRate": self.sample_rate,
            "channels": self.channels,
            "chunkSize": self.chunk_size,
            "latencyMs": (self.chunk_size / self.sample_rate) * 1000.0,
            "peakLevel": round(self.current_peak, 4),
            "rmsLevel": round(self.current_rms, 4),
            "webrtcClients": len(self.webrtc_tracks),
            "websocketClients": len(self.websocket_queues),
            "httpClients": len(self.http_queues),
            "totalClients": len(self.webrtc_tracks) + len(self.websocket_queues) + len(self.http_queues)
        }

    def shutdown(self):
        self.stop()
        try:
            self.p.terminate()
        except Exception:
            pass
