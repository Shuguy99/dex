import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.memory.rag")


class RAGEngine:
    def __init__(self, vector_memory=None, llm_client=None,
                 docs_dir: str | None = None) -> None:
        self._vector_memory = vector_memory
        self._llm = llm_client
        self._docs_dir = Path(docs_dir) if docs_dir else Path("data/docs")
        self._docs_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._docs_dir / "index.json"
        self._index: dict[str, dict[str, Any]] = self._load_index()

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if self._index_path.exists():
            with open(self._index_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_index(self) -> None:
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    def _chunk_text(self, text: str, chunk_size: int = 512,
                    overlap: int = 64) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            if end < len(text):
                last_period = chunk.rfind(".")
                if last_period > chunk_size // 2:
                    end = start + last_period + 1
                    chunk = text[start:end]
            chunks.append(chunk.strip())
            start = end - overlap
        return [c for c in chunks if len(c) > 50]

    def index_document(self, path: str | Path, metadata: dict[str, Any] | None = None) -> int:
        path = Path(path)
        if not path.exists():
            logger.error(f"Document not found: {path}")
            return 0

        text = path.read_text(encoding="utf-8")
        doc_id = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
        chunks = self._chunk_text(text)

        self._index[doc_id] = {
            "path": str(path.resolve()),
            "name": path.name,
            "size": len(text),
            "chunks": len(chunks),
            "metadata": metadata or {}
        }

        if self._vector_memory and self._vector_memory.ready:
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk_meta = {
                    "source": str(path.name),
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "type": "document"
                }
                if metadata:
                    chunk_meta.update(metadata)
                self._vector_memory.add(chunk, chunk_meta, doc_id=chunk_id)

        self._save_index()
        logger.info(f"Indexed {path.name}: {len(chunks)} chunks")
        return len(chunks)

    def index_directory(self, dir_path: str | Path,
                        pattern: str = "*.{txt,md,py,json,yaml,yml,rst}") -> int:
        dir_path = Path(dir_path)
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return 0

        total = 0
        for f_path in dir_path.rglob(pattern) if "**" in pattern else dir_path.glob(pattern):
            if f_path.is_file() and str(f_path.resolve()) not in self._index:
                try:
                    total += self.index_document(f_path)
                except Exception as e:
                    logger.error(f"Failed to index {f_path}: {e}")
        return total

    def query(self, question: str, n_results: int = 5,
              use_llm: bool = True) -> str:
        if not self._vector_memory or not self._vector_memory.ready:
            return "RAG engine not initialized"

        results = self._vector_memory.search(question, n_results=n_results)
        if not results:
            return "Ничего не найдено в документации."

        if not use_llm or not self._llm or not self._llm.ready:
            return self._format_results(results)

        return self._answer_with_llm(question, results)

    def _format_results(self, results: list[dict]) -> str:
        lines = ["Найдено в документации:"]
        for r in results:
            source = r["metadata"].get("source", "unknown")
            text = r["text"][:200]
            lines.append(f"\n📄 {source}:\n  {text}")
        return "\n".join(lines)

    def _answer_with_llm(self, question: str, results: list[dict]) -> str:
        context = "\n\n".join([
            f"[{r['metadata'].get('source', 'doc')}]: {r['text'][:500]}"
            for r in results[:5]
        ])
        prompt = (
            f"Ответь на вопрос на русском языке, используя только информацию из контекста ниже. "
            f"Если в контексте нет ответа, скажи, что информации недостаточно.\n\n"
            f"Контекст:\n{context}\n\n"
            f"Вопрос: {question}\n\n"
            f"Ответ:"
        )
        return self._llm.generate(prompt, system="Ты — архивариус.")
