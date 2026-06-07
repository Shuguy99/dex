import logging
import queue
import re
import threading
from collections.abc import Callable

logger = logging.getLogger("dex.voice")


class VoiceEngine:
    def __init__(self, lang: str = "ru-RU") -> None:
        self.lang = lang
        self._recorder = None
        self._synthesizer = None
        self._listening = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._listen_thread: threading.Thread | None = None
        self._wake_word = "джарвис"
        self._privacy_mode = False
        self._on_command: Callable[[str], None] | None = None

    @property
    def available(self) -> bool:
        try:
            import speech_recognition as sr
            return sr.Recognizer() is not None
        except Exception:
            return False

    def say(self, text: str):
        try:
            import pyttsx3
            if self._synthesizer is None:
                self._synthesizer = pyttsx3.init()
                self._synthesizer.setProperty("rate", 180)
                self._synthesizer.setProperty("voice", "russian")
            self._synthesizer.say(text)
            self._synthesizer.runAndWait()
        except Exception as e:
            logger.warning(f"TTS fallback needed: {e}")
            self._say_fallback(text)

    def _say_fallback(self, text: str):
        import subprocess
        try:
            subprocess.run(
                ["PowerShell", "-Command",
                 f"Add-Type -AssemblyName System.Speech; "
                 f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')"],
                capture_output=True, timeout=30
            )
        except Exception as e:
            logger.error(f"TTS fallback failed: {e}")

    def listen(self, timeout: float = 5.0, phrase_limit: float = 10.0) -> str | None:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except sr.WaitTimeoutError:
                return None
        try:
            text = r.recognize_google(audio, language=self.lang)
            return text.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            logger.error(f"Recognition error: {e}")
            return None

    def start_background_listening(self, on_command: Callable[[str], None]):
        self._on_command = on_command
        self._listening = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
        logger.info("Background listening started")

    def stop_listening(self):
        self._listening = False
        logger.info("Background listening stopped")

    def _listen_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            while self._listening:
                try:
                    audio = r.listen(source, timeout=1, phrase_time_limit=5)
                    text = r.recognize_google(audio, language=self.lang).lower()
                    logger.debug(f"Heard: {text}")

                    if self._privacy_mode:
                        if self._wake_word in text:
                            self.say("Приватный режим активен. Сенсоры отключены.")
                        continue

                    if self._wake_word in text:
                        re.sub(rf"^{re.escape(self._wake_word)}\s*,?\s*", "", text).strip()
                        self.say("Слушаю, сэр")
                        audio2 = r.listen(source, timeout=3, phrase_time_limit=10)
                        command_text = r.recognize_google(audio2, language=self.lang).lower()
                        logger.info(f"Command: {command_text}")
                        if self._on_command:
                            self._on_command(command_text)
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    logger.error(f"Listen loop error: {e}")

    def enable_privacy_mode(self):
        self._privacy_mode = True
        logger.info("Privacy mode enabled")

    def disable_privacy_mode(self):
        self._privacy_mode = False
        logger.info("Privacy mode disabled")

    @property
    def is_privacy_mode(self) -> bool:
        return self._privacy_mode
