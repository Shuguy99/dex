import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.voice_clone")


class VoiceCloner:
    def __init__(self, model_dir: str | None = None) -> None:
        self._model_dir = Path(model_dir) if model_dir else Path("data/xtts")
        self._model_dir.mkdir(parents=True, exist_ok=True)
        self._model: Any = None

    @property
    def available(self) -> bool:
        try:
            import TTS  # type: ignore[import-not-found]
            return True
        except ImportError:
            return False

    def load_model(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2") -> Any:
        if not self.available:
            logger.warning("XTTS not installed")
            return False
        try:
            from TTS.api import TTS  # type: ignore[import-not-found]
            self._model = TTS(model_name, gpu=False)
            logger.info(f"Voice model loaded: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load XTTS: {e}")
            return False

    def clone(self, text: str, speaker_wav: str | Path,
              output_path: str | Path | None = None,
              language: str = "ru") -> str | None:
        if not self._model and not self.load_model():
            return None

        speaker = Path(speaker_wav)
        if not speaker.exists():
            logger.error(f"Speaker sample not found: {speaker}")
            return None

        output = Path(output_path) if output_path else \
            Path(tempfile.mktemp(suffix=".wav"))

        try:
            self._model.tts_to_file(
                text=text,
                speaker_wav=str(speaker),
                language=language,
                file_path=str(output)
            )
            logger.info(f"Voice cloned to: {output}")
            return str(output)
        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            return None

    def speak(self, text: str, speaker_wav: str | Path) -> bool:
        path = self.clone(text, speaker_wav)
        if not path:
            return False
        try:
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
            return True
        except Exception as e:
            logger.error(f"Playback failed: {e}")
            return False
