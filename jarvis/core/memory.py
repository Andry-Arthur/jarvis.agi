"""ChromaDB-backed persistent vector memory for JARVIS.

Architecture:
  - Episodic memory: conversation exchanges (semantic search)
  - User profile: structured permanent facts stored in SQLite via aiosqlite
  - Working memory: current active tasks (in-process dict)
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class UserProfile:
    """Structured profile stored in SQLite for permanent user facts."""

    def __init__(self, db_path: str = ".jarvis/profile.db") -> None:
        self.db_path = db_path
        self._ready = False

    async def _ensure(self) -> None:
        if self._ready:
            return
        try:
            import aiosqlite

            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """CREATE TABLE IF NOT EXISTS profile (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )"""
                )
                await db.commit()
            self._ready = True
        except ImportError:
            logger.warning("aiosqlite not installed — user profile disabled.")
        except Exception as exc:
            logger.warning("UserProfile init failed: %s", exc)

    async def set(self, key: str, value: Any) -> None:
        await self._ensure()
        if not self._ready:
            return
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO profile (key, value, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), datetime.now(timezone.utc).isoformat()),
            )
            await db.commit()

    async def get(self, key: str, default: Any = None) -> Any:
        await self._ensure()
        if not self._ready:
            return default
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM profile WHERE key = ?", (key,)) as cur:
                row = await cur.fetchone()
                if row:
                    return json.loads(row[0])
        return default

    async def get_all(self) -> dict:
        await self._ensure()
        if not self._ready:
            return {}
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT key, value FROM profile") as cur:
                rows = await cur.fetchall()
        return {row[0]: json.loads(row[1]) for row in rows}

    async def delete(self, key: str) -> None:
        await self._ensure()
        if not self._ready:
            return
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM profile WHERE key = ?", (key,))
            await db.commit()


class Memory:
    """
    Unified memory system:
      - Episodic: ChromaDB vector store for conversation history
      - Profile:  SQLite structured user data
      - Working:  In-process dict for current session tasks
    """

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

        db_path = os.path.join(os.path.dirname(persist_directory), "profile.db")
        self.profile = UserProfile(db_path=db_path)

        # Working memory: active tasks / short-term context
        self.working: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

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
            logger.warning("chromadb not installed — episodic memory disabled.")
        except Exception as exc:
            logger.warning("Memory init failed: %s — episodic memory disabled.", exc)

    # ------------------------------------------------------------------
    # Episodic memory
    # ------------------------------------------------------------------

    async def add_exchange(self, user_message: str, assistant_response: str) -> None:
        """Persist a user/assistant exchange to episodic memory."""
        self._ensure_init()
        if self._collection is None:
            return
        doc = f"User: {user_message}\nJARVIS: {assistant_response}"
        try:
            self._collection.add(
                documents=[doc],
                ids=[str(uuid.uuid4())],
                metadatas=[{
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "exchange",
                }],
            )
        except Exception as exc:
            logger.warning("Failed to save to episodic memory: %s", exc)

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

            # Prepend relevant profile facts
            profile_str = await self._profile_context()
            context = "\n---\n".join(docs)
            if profile_str:
                context = f"[User Profile]\n{profile_str}\n\n[Past Conversations]\n{context}"
            return context
        except Exception as exc:
            logger.warning("Memory query failed: %s", exc)
            return ""

    async def _profile_context(self) -> str:
        facts = await self.profile.get_all()
        if not facts:
            return ""
        return "\n".join(f"{k}: {v}" for k, v in facts.items())

    async def add_fact(self, fact: str, fact_type: str = "episodic") -> None:
        """Store a standalone fact in episodic memory."""
        self._ensure_init()
        if self._collection is None:
            return
        try:
            self._collection.add(
                documents=[f"[FACT] {fact}"],
                ids=[str(uuid.uuid4())],
                metadatas=[{
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": fact_type,
                }],
            )
        except Exception as exc:
            logger.warning("Failed to save fact: %s", exc)

    # ------------------------------------------------------------------
    # Working memory
    # ------------------------------------------------------------------

    def set_working(self, key: str, value: Any) -> None:
        """Set a working memory value for the current session."""
        self.working[key] = value

    def get_working(self, key: str, default: Any = None) -> Any:
        return self.working.get(key, default)

    def clear_working(self) -> None:
        self.working.clear()

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    async def clear(self) -> None:
        """Wipe all stored episodic memory."""
        self._ensure_init()
        if self._client is None:
            return
        self._client.delete_collection(self.collection_name)
        self._collection = None
        logger.info("Episodic memory cleared.")
