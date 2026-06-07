import logging
from typing import Any

logger = logging.getLogger("dex.memory.vector_store")


class VectorMemory:
    def __init__(self, db_path: str, collection_name: str = "dex_memory") -> None:
        self._db_path = db_path
        self._collection_name = collection_name
        self._collection = None
        self._client = None
        self._embedder = None
        self._initialized = False

    def initialize(self):
        try:
            import chromadb
            from chromadb.config import Settings
            self._client = chromadb.PersistentClient(
                path=self._db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name
            )
            self._init_embedder()
            self._initialized = True
            logger.info(f"Vector store initialized at {self._db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._initialized = False

    def _init_embedder(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("cointegrated/rubert-tiny2")
        except Exception as e:
            logger.warning(f"Embedder not available, using fallback: {e}")
            self._embedder = None

    def _embed(self, text: str) -> list[float]:
        if self._embedder:
            return self._embedder.encode(text).tolist()
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in h[:384]]

    @property
    def ready(self) -> bool:
        return self._initialized and self._collection is not None

    def add(self, text: str, metadata: dict[str, Any] | None = None,
            doc_id: str | None = None):
        if not self.ready:
            logger.warning("Vector store not ready, cannot add")
            return
        doc_id = doc_id or str(hash(text))
        embedding = self._embed(text)
        self._collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id]
        )
        logger.debug(f"Added to vector store: {text[:50]}...")

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        if not self.ready:
            logger.warning("Vector store not ready, cannot search")
            return []
        embedding = self._embed(query)
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )
        items = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                items.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0
                })
        return items

    def get_all(self) -> list[dict[str, Any]]:
        if not self.ready:
            return []
        data = self._collection.get()
        items = []
        for i, doc in enumerate(data["documents"] or []):
            items.append({
                "id": data["ids"][i],
                "text": doc,
                "metadata": data["metadatas"][i] if data["metadatas"] else {}
            })
        return items

    def delete(self, doc_id: str):
        if self.ready:
            self._collection.delete(ids=[doc_id])

    def count(self) -> int:
        if self.ready:
            return self._collection.count()
        return 0
