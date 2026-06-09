import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock TTS module before any imports from core.voice_clone
mock_TTS = MagicMock()
mock_TTS_api = MagicMock()
mock_TTS.api = mock_TTS_api
sys.modules["TTS"] = mock_TTS
sys.modules["TTS.api"] = mock_TTS_api

from core.voice_clone import VoiceCloner


class TestVoiceCloner(unittest.TestCase):
    def setUp(self):
        with patch("core.voice_clone.Path.mkdir"):
            self.cloner = VoiceCloner(model_dir="test_models")

    @patch("core.voice_clone.VoiceCloner.available", new_callable=lambda: False)
    def test_available_import_error(self, mock_available):
        cloner = VoiceCloner(model_dir="test_models")
        self.assertFalse(cloner.available)

    def test_available_true(self):
        with patch("core.voice_clone.VoiceCloner.available", new_callable=lambda: True):
            self.assertTrue(self.cloner.available)

    @patch("core.voice_clone.VoiceCloner.available", new_callable=lambda: False)
    def test_load_model_not_available(self, mock_available):
        cloner = VoiceCloner(model_dir="test_models")
        result = cloner.load_model()
        self.assertFalse(result)

    @patch("core.voice_clone.VoiceCloner.available", new_callable=lambda: True)
    @patch("TTS.api.TTS")
    def test_load_model_success(self, mock_tts, mock_available):
        cloner = VoiceCloner(model_dir="test_models")
        mock_tts.return_value = MagicMock()
        result = cloner.load_model("test_model")
        self.assertTrue(result)
        self.assertIsNotNone(cloner._model)

    @patch("core.voice_clone.VoiceCloner.available", new_callable=lambda: True)
    @patch("TTS.api.TTS", side_effect=Exception("load error"))
    def test_load_model_failure(self, mock_tts, mock_available):
        cloner = VoiceCloner(model_dir="test_models")
        result = cloner.load_model("test_model")
        self.assertFalse(result)

    @patch("core.voice_clone.VoiceCloner.load_model", return_value=False)
    def test_clone_no_model(self, mock_load):
        cloner = VoiceCloner(model_dir="test_models")
        cloner._model = None
        result = cloner.clone("hello", "speaker.wav")
        self.assertIsNone(result)

    @patch("core.voice_clone.VoiceCloner.load_model", return_value=True)
    def test_clone_speaker_not_found(self, mock_load):
        cloner = VoiceCloner(model_dir="test_models")
        cloner._model = MagicMock()
        result = cloner.clone("hello", "nonexistent.wav")
        self.assertIsNone(result)

    @patch("core.voice_clone.VoiceCloner.load_model", return_value=True)
    @patch("core.voice_clone.Path.exists")
    @patch("core.voice_clone.Path.mkdir")
    def test_clone_success(self, mock_mkdir, mock_exists, mock_load):
        mock_exists.return_value = True
        cloner = VoiceCloner(model_dir="test_models")
        cloner._model = MagicMock()
        result = cloner.clone("hello", "speaker.wav", output_path="out.wav")
        self.assertEqual(result, "out.wav")

    @patch("core.voice_clone.VoiceCloner.load_model", return_value=True)
    @patch("core.voice_clone.Path.exists")
    @patch("core.voice_clone.Path.mkdir")
    def test_clone_failure(self, mock_mkdir, mock_exists, mock_load):
        mock_exists.return_value = True
        cloner = VoiceCloner(model_dir="test_models")
        cloner._model = MagicMock()
        cloner._model.tts_to_file.side_effect = Exception("gen error")
        result = cloner.clone("hello", "speaker.wav", output_path="out.wav")
        self.assertIsNone(result)

    @patch("core.voice_clone.VoiceCloner.clone")
    def test_speak_clone_returns_none(self, mock_clone):
        mock_clone.return_value = None
        cloner = VoiceCloner(model_dir="test_models")
        result = cloner.speak("hello", "speaker.wav")
        self.assertFalse(result)

    @patch("core.voice_clone.VoiceCloner.clone")
    @patch("winsound.PlaySound")
    def test_speak_success(self, mock_play, mock_clone):
        mock_clone.return_value = "out.wav"
        cloner = VoiceCloner(model_dir="test_models")
        result = cloner.speak("hello", "speaker.wav")
        self.assertTrue(result)

    @patch("core.voice_clone.VoiceCloner.clone")
    @patch("winsound.PlaySound", side_effect=Exception("play fail"))
    def test_speak_playback_failure(self, mock_play, mock_clone):
        mock_clone.return_value = "out.wav"
        cloner = VoiceCloner(model_dir="test_models")
        result = cloner.speak("hello", "speaker.wav")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
