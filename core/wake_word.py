import logging
import os
import re
import threading
from collections.abc import Callable

logger = logging.getLogger("dex.wake_word")


class WakeWordDetector:
    def __init__(self, wake_word: str = "джарвис") -> None:
        self._wake_word = wake_word.lower()
        self._on_wake: Callable | None = None
        self._active = False
        self._thread: threading.Thread | None = None
        self._porcupine = None

    @property
    def available(self) -> bool:
        try:
            import pvporcupine
            pvporcupine.KEYWORDS
            return True
        except Exception:
            return False

    def _init_porcupine(self) -> None:
        try:
            import pvporcupine
            access_key = os.environ.get("PICOVOICE_ACCESS_KEY", "")
            if access_key:
                self._porcupine = pvporcupine.create(
                    access_key=access_key,
                    keywords=[self._wake_word]
                )
        except Exception as e:
            logger.debug(f"Porcupine not available: {e}")
            self._porcupine = None

    def text_contains_wake(self, text: str) -> bool:
        return self._wake_word in text.lower()

    def extract_command(self, text: str) -> str:
        return re.sub(rf"^{re.escape(self._wake_word)}\s*,?\s*", "", text.lower()).strip()

    def start(self, on_wake: Callable[[], None]) -> None:
        self._on_wake = on_wake
        self._active = True
        if self.available:
            self._thread = threading.Thread(target=self._porcupine_loop, daemon=True)
        else:
            self._thread = threading.Thread(target=self._text_fallback_loop, daemon=True)
        self._thread.start()
        logger.info("Wake word detector started")

    def stop(self) -> None:
        self._active = False
        if self._porcupine:
            self._porcupine.delete()
        logger.info("Wake word detector stopped")

    def _porcupine_loop(self):
        import struct

        import pyaudio
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length
        )
        while self._active:
            pcm = stream.read(self._porcupine.frame_length)
            pcm_unpacked = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
            keyword_index = self._porcupine.process(pcm_unpacked)
            if keyword_index >= 0 and self._on_wake:
                self._on_wake()
        stream.close()
        pa.terminate()

    def _text_fallback_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            while self._active:
                try:
                    audio = r.listen(source, timeout=1, phrase_time_limit=3)
                    text = r.recognize_google(audio, language="ru-RU").lower()
                    if self._wake_word in text and self._on_wake:
                        self._on_wake()
                except (sr.WaitTimeoutError, sr.UnknownValueError):
                    continue
                except Exception as e:
                    logger.error(f"Wake word loop error: {e}")
