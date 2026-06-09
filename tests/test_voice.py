import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.voice import VoiceEngine


class TestVoiceEngine(unittest.TestCase):
    def setUp(self):
        self.engine = VoiceEngine(lang="ru-RU")

    def test_init(self):
        self.assertEqual(self.engine.lang, "ru-RU")
        self.assertFalse(self.engine._listening)
        self.assertEqual(self.engine._wake_word, "джарвис")
        self.assertFalse(self.engine._privacy_mode)

    @patch("speech_recognition.Recognizer")
    def test_available_true(self, mock_rec):
        mock_rec.return_value = MagicMock()
        self.assertTrue(self.engine.available)

    @patch("speech_recognition.Recognizer", side_effect=Exception("no sr"))
    def test_available_false(self, mock_rec):
        self.assertFalse(self.engine.available)

    @patch("pyttsx3.init")
    def test_say_success(self, mock_init):
        mock_engine = MagicMock()
        mock_init.return_value = mock_engine
        self.engine.say("hello")
        mock_engine.say.assert_called_once_with("hello")
        mock_engine.runAndWait.assert_called_once()

    @patch("pyttsx3.init")
    def test_say_reuses_synthesizer(self, mock_init):
        mock_engine = MagicMock()
        mock_init.return_value = mock_engine
        self.engine.say("first")
        self.engine.say("second")
        self.assertEqual(mock_engine.say.call_count, 2)

    @patch("pyttsx3.init", side_effect=Exception("no pyttsx3"))
    @patch("core.voice.VoiceEngine._say_fallback")
    def test_say_fallback_on_error(self, mock_fallback, mock_init):
        self.engine.say("hello")
        mock_fallback.assert_called_once_with("hello")

    @patch("subprocess.run")
    def test_say_fallback(self, mock_run):
        mock_run.return_value = MagicMock()
        self.engine._say_fallback("hello world")
        mock_run.assert_called_once()

    @patch("subprocess.run", side_effect=Exception("fail"))
    def test_say_fallback_error(self, mock_run):
        self.engine._say_fallback("hello")

    @patch("speech_recognition.Recognizer")
    @patch("speech_recognition.Microphone")
    def test_listen_timeout(self, mock_mic, mock_rec_cls):
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        from speech_recognition import WaitTimeoutError
        mock_rec.listen.side_effect = WaitTimeoutError()
        mock_mic.return_value.__enter__.return_value = MagicMock()
        result = self.engine.listen(timeout=1, phrase_limit=2)
        self.assertIsNone(result)

    @patch("speech_recognition.Recognizer")
    @patch("speech_recognition.Microphone")
    def test_listen_unknown_value(self, mock_mic, mock_rec_cls):
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        from speech_recognition import UnknownValueError
        mock_rec.listen.return_value = MagicMock()
        mock_rec.recognize_google.side_effect = UnknownValueError()
        mock_mic.return_value.__enter__.return_value = MagicMock()
        result = self.engine.listen(timeout=1, phrase_limit=2)
        self.assertIsNone(result)

    @patch("speech_recognition.Recognizer")
    @patch("speech_recognition.Microphone")
    def test_listen_request_error(self, mock_mic, mock_rec_cls):
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        from speech_recognition import RequestError
        mock_rec.listen.return_value = MagicMock()
        mock_rec.recognize_google.side_effect = RequestError("network error")
        mock_mic.return_value.__enter__.return_value = MagicMock()
        result = self.engine.listen(timeout=1, phrase_limit=2)
        self.assertIsNone(result)

    @patch("speech_recognition.Recognizer")
    @patch("speech_recognition.Microphone")
    def test_listen_success(self, mock_mic, mock_rec_cls):
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        mock_rec.listen.return_value = MagicMock()
        mock_rec.recognize_google.return_value = "Привет"
        mock_mic.return_value.__enter__.return_value = MagicMock()
        result = self.engine.listen(timeout=1, phrase_limit=2)
        self.assertEqual(result, "привет")

    def test_privacy_mode(self):
        self.assertFalse(self.engine.is_privacy_mode)
        self.engine.enable_privacy_mode()
        self.assertTrue(self.engine.is_privacy_mode)
        self.engine.disable_privacy_mode()
        self.assertFalse(self.engine.is_privacy_mode)

    def test_start_stop_listening(self):
        callback = MagicMock()
        self.engine.start_background_listening(callback)
        self.assertTrue(self.engine._listening)
        self.assertIsNotNone(self.engine._listen_thread)
        self.engine.stop_listening()
        self.assertFalse(self.engine._listening)

    @patch("speech_recognition.Recognizer")
    @patch("speech_recognition.Microphone")
    @patch("core.voice.VoiceEngine.say")
    def test_listen_loop_privacy_mode_wake(self, mock_say, mock_mic, mock_rec_cls):
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        mock_rec.listen.return_value = MagicMock()
        mock_rec.recognize_google.return_value = "джарвис привет"
        mock_mic.return_value.__enter__.return_value = MagicMock()

        self.engine._privacy_mode = True
        self.engine._on_command = MagicMock()
        self.engine._listening = True

        def stop_after(*args, **kwargs):
            self.engine._listening = False
            return MagicMock()

        mock_rec.listen.side_effect = stop_after
        self.engine._listen_loop()
        mock_say.assert_called_once_with("Приватный режим активен. Сенсоры отключены.")

    @patch("speech_recognition.Recognizer")
    @patch("speech_recognition.Microphone")
    @patch("core.voice.VoiceEngine.say")
    def test_listen_loop_wake_word(self, mock_say, mock_mic, mock_rec_cls):
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        mock_mic.return_value.__enter__.return_value = MagicMock()

        listen_results = iter([MagicMock(), MagicMock()])

        def listen_side(*args, **kwargs):
            try:
                return next(listen_results)
            except StopIteration:
                self.engine._listening = False
                from speech_recognition import WaitTimeoutError
                raise WaitTimeoutError() from None

        mock_rec.listen = MagicMock(side_effect=listen_side)
        mock_rec.recognize_google.return_value = "джарвис команда"

        self.engine._on_command = MagicMock()
        self.engine._listening = True
        self.engine._listen_loop()
        mock_say.assert_any_call("Слушаю, сэр")


if __name__ == "__main__":
    unittest.main()
