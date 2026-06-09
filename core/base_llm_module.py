import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.base_llm_module")


class BaseLLMModule(ABC):
    def __init__(self, llm_client=None, data_dir: str | None = None) -> None:
        self._llm = llm_client
        self._data_dir = Path(data_dir) if data_dir else Path("data/base_llm_module")
        self._data_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def _data_path(self) -> Path:
        ...

    def _save(self, data: Any) -> None:
        with open(self._data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self) -> dict[str, Any]:
        if self._data_path.exists():
            try:
                with open(self._data_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.exception(f"Failed to load data from {self._data_path}")
        return {}

    @abstractmethod
    def get_summary(self) -> str:
        ...

    def generate_llm(self, prompt: str, schema: dict[str, Any] | None = None) -> Any:
        if not self._llm:
            logger.warning("No LLM client available")
            return None
        if schema:
            return self._llm.generate_structured(prompt, schema)
        return self._llm.generate(prompt)
