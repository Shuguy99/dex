import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.dexos.search")


class LocalSearchEngine:
    def __init__(self, vector_memory=None, rag_engine=None) -> None:
        self._vector_memory = vector_memory
        self._rag = rag_engine
        self._data_dir = Path("data/dexos")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._data_dir / "search_index.json"
        self._index: dict[str, Any] = self._load_index()

    def _load_index(self) -> dict[str, Any]:
        if self._index_path.exists():
            try:
                with open(self._index_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"pdfs": [], "screenshots": [], "annotations": [],
                "documents": [], "last_index": None}

    def _save_index(self) -> None:
        with open(self._index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    def search(self, query: str, file_type: str | None = None,
               highlight_color: str | None = None,
               has_annotation: bool = False) -> list[dict[str, Any]]:
        results = []

        query_lower = query.lower()
        source_map = {
            "pdf": "pdfs", "pdfs": "pdfs",
            "doc": "documents", "documents": "documents",
            "screenshot": "screenshots", "img": "screenshots",
        }

        sources = []
        if file_type and file_type in source_map:
            sources = [source_map[file_type]]
        else:
            sources = ["pdfs", "documents", "screenshots", "annotations"]

        for src_key in sources:
            for item in self._index.get(src_key, []):
                text = item.get("text", "").lower()
                highlights = item.get("highlights", [])
                annotations = item.get("annotations", [])

                if query_lower in text:
                    score = 1.0
                    if query_lower in item.get("title", "").lower():
                        score += 0.5
                    if highlight_color and highlight_color in [
                        h.get("color", "") for h in highlights
                    ]:
                        score += 0.3
                    if has_annotation and annotations:
                        score += 0.2
                    results.append({
                        "source": src_key,
                        "title": item.get("title", ""),
                        "path": item.get("path", ""),
                        "snippet": text[:200],
                        "score": score,
                        "highlights": highlights[:3],
                        "annotations": annotations[:2]
                    })

        if self._vector_memory:
            mem_results = self._vector_memory.search(query, n_results=5)
            for r in mem_results:
                results.append({
                    "source": "memory",
                    "title": r.get("text", "")[:100],
                    "path": r.get("doc_id", ""),
                    "snippet": r.get("text", "")[:200],
                    "score": r.get("distance", 0.5),
                    "highlights": [],
                    "annotations": []
                })

        results.sort(key=lambda x: -x["score"])
        return results[:10]

    def index_pdf(self, path: str, highlights: list[dict] | None = None,
                  annotations: list[str] | None = None) -> str:
        entry = {
            "path": path,
            "title": Path(path).stem,
            "text": self._extract_pdf_text(path),
            "highlights": highlights or [],
            "annotations": annotations or [],
            "indexed": datetime.now().isoformat()
        }
        existing = [i for i in self._index["pdfs"] if i["path"] != path]
        existing.append(entry)
        self._index["pdfs"] = existing
        self._index["last_index"] = datetime.now().isoformat()
        self._save_index()

    def _extract_pdf_text(self, path: str) -> str:
        try:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() for page in reader.pages)
        except ImportError:
            pass
        try:
            import pdfminer
            from pdfminer.high_level import extract_text
            return extract_text(path)
        except ImportError:
            pass
        return f"(PDF content: {Path(path).name})"

    def index_screenshot(self, path: str, ocr_text: str = "") -> str:
        entry = {
            "path": path,
            "title": Path(path).stem,
            "text": ocr_text,
            "highlights": [],
            "annotations": [],
            "indexed": datetime.now().isoformat()
        }
        self._index["screenshots"].append(entry)
        self._save_index()

    def get_search_summary(self) -> str:
        counts = {k: len(v) for k, v in self._index.items() if isinstance(v, list)}
        lines = ["── Local Search Engine ──"]
        for src, cnt in counts.items():
            lines.append(f"  {src}: {cnt} entries")
        if self._index.get("last_index"):
            lines.append(f"  Last index: {self._index['last_index'][:19]}")
        return "\n".join(lines)
