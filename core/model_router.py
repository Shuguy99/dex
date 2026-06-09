import logging
from typing import Any

logger = logging.getLogger("dex.resource.model_router")

PURPOSES = [
    "chat",
    "rag",
    "planner",
    "tiered_small",
    "vision",
    "research",
    "debate",
    "code",
    "ethics",
    "personality",
    "retrospective",
    "meta_learning",
]


class ModelRouter:
    def __init__(self, llm_client: Any, purpose_map: dict[str, str] | None = None) -> None:
        self._llm = llm_client
        self._purpose_map = dict(purpose_map or {})

    def get_model(self, purpose: str) -> str | None:
        return self._purpose_map.get(purpose)

    def set_purpose_model(self, purpose: str, model: str) -> None:
        if purpose not in PURPOSES:
            logger.warning(f"Unknown purpose: {purpose}")
        self._purpose_map[purpose] = model
        logger.info(f"Model for '{purpose}': {model}")

    def generate(self, prompt: str, purpose: str | None = None, **kwargs: Any) -> str:
        model = self._purpose_map.get(purpose) if purpose else None
        if model:
            kwargs.setdefault("model", model)
        return self._llm.generate(prompt, **kwargs)

    def generate_structured(self, prompt: str, schema: dict[str, Any],
                            purpose: str | None = None, **kwargs: Any) -> Any:
        model = self._purpose_map.get(purpose) if purpose else None
        if model:
            kwargs.setdefault("model", model)
        return self._llm.generate_structured(prompt, schema, **kwargs)

    @property
    def purpose_map(self) -> dict[str, str]:
        return dict(self._purpose_map)

    @property
    def is_ready(self) -> bool:
        return bool(self._llm.ready)
