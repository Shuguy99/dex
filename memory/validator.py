import logging
from typing import Any

logger = logging.getLogger("dex.memory.validator")


class MemoryValidator:
    def __init__(self, vector_memory=None) -> None:
        self._vector_memory = vector_memory

    def validate_new_fact(self, fact_text: str, metadata: dict[str, Any] | None = None) -> bool:
        if self._vector_memory is None or not self._vector_memory.ready:
            return True

        similar = self._vector_memory.search(fact_text, n_results=3)
        if not similar:
            return True

        for item in similar:
            if item["distance"] < 0.3:
                existing = item["text"]
                if self._is_contradictory(fact_text, existing):
                    logger.warning(
                        f"Memory conflict detected!\n"
                        f"  Existing: {existing[:100]}...\n"
                        f"  New:      {fact_text[:100]}..."
                    )
                    return False
        return True

    def _is_contradictory(self, fact_a: str, fact_b: str) -> bool:
        import re
        negation_patterns = [
            (r"не (\w+)", r"\1"),
            (r"никогда не (\w+)", r"\1"),
            (r"нет", r"да"),
            (r"нельзя", r"можно"),
            (r"отсутствует", r"присутствует"),
        ]
        for neg_pat, pos_pat in negation_patterns:
            neg_match = re.search(neg_pat, fact_a.lower())
            pos_match = re.search(pos_pat, fact_b.lower())
            if neg_match and pos_match and neg_match.group(1).lower() == pos_match.group(1).lower():
                return True

            neg_match = re.search(neg_pat, fact_b.lower())
            pos_match = re.search(pos_pat, fact_a.lower())
            if neg_match and pos_match and neg_match.group(1).lower() == pos_match.group(1).lower():
                return True

        return False

    def requires_confirmation(self, fact_text: str) -> bool:
        from .encryptor import SecureMemory
        return SecureMemory.is_sensitive(fact_text)
