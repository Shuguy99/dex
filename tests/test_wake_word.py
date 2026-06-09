import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock pvporcupine before core.wake_word is imported
sys.modules["pvporcupine"] = MagicMock()
sys.modules["pvporcupine"].KEYWORDS = ["джарвис"]

from core.wake_word import WakeWordDetector


class TestWakeWordDetector(unittest.TestCase):
    def setUp(self):
        self.detector = WakeWordDetector(wake_word="джарвис")

    def test_init(self):
        self.assertEqual(self.detector._wake_word, "джарвис")
        self.assertIsNone(self.detector._on_wake)
        self.assertFalse(self.detector._active)
        self.assertIsNone(self.detector._porcupine)

    @patch("pvporcupine.KEYWORDS")
    def test_available_true(self, mock_kw):
        self.assertTrue(self.detector.available)

    def test_available_false(self):
        with patch.dict("sys.modules", {"pvporcupine": None}):
            d = WakeWordDetector()
            # reload to clear cached import
            self.assertFalse(d.available)

    @patch("pvporcupine.create")
    @patch.dict("os.environ", {"PICOVOICE_ACCESS_KEY": "test-key"})
    def test_init_porcupine_success(self, mock_create):
        mock_create.return_value = MagicMock()
        self.detector._init_porcupine()
        self.assertIsNotNone(self.detector._porcupine)
        mock_create.assert_called_once_with(access_key="test-key", keywords=["джарвис"])

    @patch("pvporcupine.create", side_effect=Exception("init fail"))
    @patch.dict("os.environ", {"PICOVOICE_ACCESS_KEY": "test-key"})
    def test_init_porcupine_failure(self, mock_create):
        self.detector._init_porcupine()
        self.assertIsNone(self.detector._porcupine)

    def test_text_contains_wake_true(self):
        self.assertTrue(self.detector.text_contains_wake("джарвис привет"))
        self.assertTrue(self.detector.text_contains_wake("ДЖАРВИС"))
        self.assertTrue(self.detector.text_contains_wake("  джарвис  "))

    def test_text_contains_wake_false(self):
        self.assertFalse(self.detector.text_contains_wake("привет"))
        self.assertFalse(self.detector.text_contains_wake(""))
        self.assertFalse(self.detector.text_contains_wake("джаз"))

    def test_extract_command(self):
        cmd = self.detector.extract_command("джарвис как дела")
        self.assertEqual(cmd, "как дела")
        cmd = self.detector.extract_command("джарвис, открой файл")
        self.assertEqual(cmd, "открой файл")
        cmd = self.detector.extract_command("ДЖАРВИС команда")
        self.assertEqual(cmd, "команда")

    def test_extract_command_no_wake(self):
        cmd = self.detector.extract_command("просто текст")
        self.assertEqual(cmd, "просто текст")

    def test_extract_command_empty(self):
        cmd = self.detector.extract_command("")
        self.assertEqual(cmd, "")

    @patch("core.wake_word.WakeWordDetector._text_fallback_loop")
    def test_start_fallback(self, mock_loop):
        callback = MagicMock()
        with patch.object(WakeWordDetector, "available", False):
            d = WakeWordDetector(wake_word="джарвис")
            d.start(callback)
            self.assertTrue(d._active)
            self.assertIs(d._on_wake, callback)
            mock_loop.assert_called_once()

    @patch("core.wake_word.WakeWordDetector._porcupine_loop")
    def test_start_porcupine(self, mock_loop):
        callback = MagicMock()
        with patch.object(WakeWordDetector, "available", True):
            d = WakeWordDetector(wake_word="джарвис")
            d.start(callback)
            self.assertTrue(d._active)
            mock_loop.assert_called_once()

    def test_stop(self):
        self.detector._active = True
        self.detector._porcupine = MagicMock()
        self.detector.stop()
        self.assertFalse(self.detector._active)
        self.detector._porcupine.delete.assert_called_once()

    @patch("pyaudio.PyAudio")
    def test_porcupine_loop_trigger(self, mock_pyaudio):
        mock_pa_instance = MagicMock()
        mock_pyaudio.return_value = mock_pa_instance
        mock_stream = MagicMock()
        mock_pa_instance.open.return_value = mock_stream
        mock_stream.read.return_value = b"\x00\x00" * 512
        self.detector._porcupine = MagicMock()
        self.detector._porcupine.frame_length = 512
        self.detector._porcupine.sample_rate = 16000
        self.detector._porcupine.process.return_value = 0

        callback = MagicMock()
        self.detector._on_wake = callback
        self.detector._active = True

        def stop_after(*args):
            self.detector._active = False
            return b"\x00\x00" * 512

        mock_stream.read.side_effect = stop_after
        self.detector._porcupine_loop()
        callback.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_pa_instance.terminate.assert_called_once()

    @patch("speech_recognition.Recognizer")
    @patch("speech_recognition.Microphone")
    def test_text_fallback_loop_trigger(self, mock_mic, mock_rec_cls):
        import speech_recognition as sr
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        mock_mic.return_value.__enter__.return_value = MagicMock()

        callback = MagicMock()
        self.detector._on_wake = callback
        self.detector._active = True

        def listen_side(*args, **kwargs):
            self.detector._active = False
            return MagicMock()

        mock_rec.listen.side_effect = listen_side
        mock_rec.recognize_google.return_value = "джарвис команда"
        self.detector._text_fallback_loop()
        callback.assert_called_once()

    @patch("speech_recognition.Recognizer")
    @patch("speech_recognition.Microphone")
    def test_text_fallback_loop_timeout(self, mock_mic, mock_rec_cls):
        import speech_recognition as sr
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        mock_mic.return_value.__enter__.return_value = MagicMock()

        callback = MagicMock()
        self.detector._on_wake = callback
        self.detector._active = True

        calls = [0]

        def listen_side(*a, **kw):
            calls[0] += 1
            if calls[0] >= 3:
                self.detector._active = False
            raise sr.WaitTimeoutError()

        mock_rec.listen.side_effect = listen_side
        self.detector._text_fallback_loop()
        callback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
