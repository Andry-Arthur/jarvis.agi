"""ChromaDB-backed persistent vector memory for JARVIS."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class Memory:
    """Stores conversation exchanges and retrieves relevant context via semantic search."""

    def __init__(
        self,
        persist_directory: str = ".jarvis/chroma",
        collection_name: str = "jarvis_memory",
        max_results: int = 5,
    ) -> None:
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.max_results = max_results
        self._client = None
        self._collection = None

    def _ensure_init(self) -> None:
        if self._collection is not None:
            return
        try:
            import chromadb

            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Memory initialised at %s", self.persist_directory)
        except ImportError:
            logger.warning("chromadb not installed — memory disabled.")
        except Exception as exc:
            logger.warning("Memory init failed: %s — memory disabled.", exc)

    async def add_exchange(self, user_message: str, assistant_response: str) -> None:
        """Persist a user/assistant exchange."""
        self._ensure_init()
        if self._collection is None:
            return
        doc = f"User: {user_message}\nJARVIS: {assistant_response}"
        try:
            self._collection.add(
                documents=[doc],
                ids=[str(uuid.uuid4())],
                metadatas=[{"timestamp": datetime.utcnow().isoformat()}],
            )
        except Exception as exc:
            logger.warning("Failed to save to memory: %s", exc)

    async def get_relevant_context(self, query: str) -> str:
        """Return relevant past exchanges as a formatted string."""
        self._ensure_init()
        if self._collection is None:
            return ""
        try:
            _count = self._collection.count()
            if _count == 0:
                return ""
            results = self._collection.query(
                query_texts=[query],
                n_results=min(self.max_results, _count),
            )
            docs = results.get("documents", [[]])[0]
            if not docs:
                return ""
            return "\n---\n".join(docs)
        except Exception as exc:
            logger.warning("Memory query failed: %s", exc)
            return ""

    async def add_fact(self, fact: str) -> None:
        """Store a standalone fact (e.g. user preference)."""
        self._ensure_init()
        if self._collection is None:
            return
        try:
            self._collection.add(
                documents=[f"[FACT] {fact}"],
                ids=[str(uuid.uuid4())],
                metadatas=[{"timestamp": datetime.utcnow().isoformat(), "type": "fact"}],
            )
        except Exception as exc:
            logger.warning("Failed to save fact: %s", exc)

    async def clear(self) -> None:
        """Wipe all stored memory."""
        self._ensure_init()
        if self._client is None:
            return
        self._client.delete_collection(self.collection_name)
        self._collection = None
        logger.info("Memory cleared.")
