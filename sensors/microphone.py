import logging
import queue
import threading
from collections.abc import Callable

logger = logging.getLogger("dex.sensors.microphone")

INDICATOR_ON = "🔴"
INDICATOR_OFF = "⚫"


class Microphone:
    def __init__(self) -> None:
        self._stream = None
        self._audio_interface = None
        self._active = False
        self._privacy_mode = False
        self._recording = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._on_audio: Callable[[bytes], None] | None = None

    @property
    def available(self) -> bool:
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            count = p.get_device_count()
            p.terminate()
            return count > 0
        except Exception:
            return False

    def start(self, on_audio: Callable[[bytes], None] | None = None) -> bool:
        if self._privacy_mode:
            logger.warning("Microphone blocked by privacy mode")
            return False
        try:
            import pyaudio
            self._on_audio = on_audio
            self._audio_interface = pyaudio.PyAudio()
            self._stream = self._audio_interface.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024,
                stream_callback=self._audio_callback
            )
            self._active = True
            self._stream.start_stream()
            logger.info(f"Microphone started {INDICATOR_ON}")
            self._show_indicator(True)
            return True
        except Exception as e:
            logger.error(f"Microphone start failed: {e}")
            return False

    def stop(self) -> None:
        self._active = False
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._audio_interface:
            self._audio_interface.terminate()
        self._show_indicator(False)
        logger.info(f"Microphone stopped {INDICATOR_OFF}")

    def _audio_callback(self, in_data, frame_count, time_info, status) -> None:
        if self._on_audio:
            self._on_audio(in_data)
        return (None, 0)

    def _show_indicator(self, on: bool) -> None:
        try:
            char = INDICATOR_ON if on else INDICATOR_OFF
            print(f"\rMicrophone: {char}", end="", flush=True)
        except Exception:
            pass

    def enable_privacy_mode(self) -> None:
        self._privacy_mode = True
        self.stop()

    def disable_privacy_mode(self) -> None:
        self._privacy_mode = False

    def toggle_privacy_mode(self) -> None:
        if self._privacy_mode:
            self.disable_privacy_mode()
        else:
            self.enable_privacy_mode()
