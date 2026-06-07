import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.sensors.vision")


class VisionEngine:
    def __init__(self, llm_client=None, ollama_model: str = "llava:13b") -> None:
        self._llm = llm_client
        self._model = ollama_model

    @property
    def available(self) -> bool:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            return self._model in result.stdout if result.returncode == 0 else False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def describe_image(self, image_path: str | Path,
                       prompt: str = "Опиши, что ты видишь на этом изображении") -> str:
        path = Path(image_path)
        if not path.exists():
            return "Файл изображения не найден."

        try:
            result = subprocess.run(
                ["ollama", "run", self._model, f"{prompt}\n\nImage: {path.resolve()}"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return f"Ошибка: {result.stderr}"
        except Exception as e:
            logger.error(f"Vision failed: {e}")
            return ""

    def analyze_screenshot(self, image_path: str | Path) -> dict[str, Any]:
        path = Path(image_path)
        if not path.exists():
            return {"error": "File not found"}

        prompt = (
            "Analyze this screenshot. Describe:\n"
            "1. What application or page is visible\n"
            "2. Key UI elements (buttons, text fields, menus)\n"
            "3. Any error messages or notifications\n"
            "4. The overall layout structure"
        )
        description = self.describe_image(path, prompt)
        return {"description": description, "source": str(path)}

    def read_text_from_image(self, image_path: str | Path) -> str:
        path = Path(image_path)
        if not path.exists():
            return ""

        try:
            import pytesseract
            from PIL import Image
            text = pytesseract.image_to_string(Image.open(path), lang="rus+eng")
            return text.strip()
        except ImportError:
            logger.warning("pytesseract not installed, using LLM vision")
            return self.describe_image(
                path, "Прочитай и распознай весь текст на этом изображении"
            )
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
