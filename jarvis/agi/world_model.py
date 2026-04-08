"""World model — JARVIS maintains a structured representation of the user's world.

Tracks: people, projects, goals, recurring events, preferences, and relationships.
Stored in SQLite via aiosqlite. Updated from conversation context automatically.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_DB_PATH = os.getenv("WORLD_MODEL_DB", ".jarvis/world_model.db")

_EXTRACTION_SYSTEM = """You are JARVIS's world model updater. 
Given a conversation exchange, extract any new facts about the user's world.

Return a JSON object with these optional keys (omit keys where nothing new was learned):
{
  "people": [{"name": "...", "relationship": "...", "notes": "..."}],
  "projects": [{"name": "...", "status": "...", "description": "..."}],
  "goals": [{"goal": "...", "timeframe": "...", "priority": "high|medium|low"}],
  "preferences": [{"category": "...", "preference": "..."}],
  "events": [{"name": "...", "date": "...", "recurring": false}],
  "facts": ["any other important facts about the user's world"]
}

If nothing notable was learned, return: {}
Output ONLY the JSON object."""


class WorldModel:
    """Structured knowledge graph of the user's world."""

    def __init__(self, db_path: str = _DB_PATH) -> None:
        self.db_path = db_path
        self._ready = False

    async def _ensure(self) -> None:
        if self._ready:
            return
        try:
            import aiosqlite

            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
            async with aiosqlite.connect(self.db_path) as db:
                await db.executescript("""
                    CREATE TABLE IF NOT EXISTS people (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        relationship TEXT,
                        notes TEXT,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        status TEXT,
                        description TEXT,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS goals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        goal TEXT NOT NULL,
                        timeframe TEXT,
                        priority TEXT,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS preferences (
                        category TEXT NOT NULL,
                        preference TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (category, preference)
                    );
                    CREATE TABLE IF NOT EXISTS world_facts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fact TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                """)
                await db.commit()
            self._ready = True
        except ImportError:
            logger.warning("aiosqlite not installed — world model disabled.")
        except Exception as exc:
            logger.warning("WorldModel init failed: %s", exc)

    async def update_from_conversation(
        self, user_message: str, assistant_response: str, llm_router
    ) -> dict:
        """Extract and store world facts from a conversation exchange."""
        messages = [
            {
                "role": "user",
                "content": f"User: {user_message}\nJARVIS: {assistant_response}",
            }
        ]
        try:
            response = await llm_router.chat(messages, system=_EXTRACTION_SYSTEM)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            facts = json.loads(content)
            if facts:
                await self._store(facts)
            return facts
        except Exception as exc:
            logger.debug("World model extraction skipped: %s", exc)
            return {}

    async def _store(self, facts: dict) -> None:
        await self._ensure()
        if not self._ready:
            return
        import aiosqlite

        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            for person in facts.get("people", []):
                await db.execute(
                    "INSERT INTO people (name, relationship, notes, updated_at) VALUES (?, ?, ?, ?)",
                    (person.get("name"), person.get("relationship"), person.get("notes"), now),
                )
            for project in facts.get("projects", []):
                await db.execute(
                    "INSERT OR REPLACE INTO projects (name, status, description, updated_at) VALUES (?, ?, ?, ?)",
                    (project.get("name"), project.get("status"), project.get("description"), now),
                )
            for goal in facts.get("goals", []):
                await db.execute(
                    "INSERT INTO goals (goal, timeframe, priority, updated_at) VALUES (?, ?, ?, ?)",
                    (goal.get("goal"), goal.get("timeframe"), goal.get("priority"), now),
                )
            for pref in facts.get("preferences", []):
                await db.execute(
                    "INSERT OR REPLACE INTO preferences (category, preference, updated_at) VALUES (?, ?, ?)",
                    (pref.get("category"), pref.get("preference"), now),
                )
            for fact in facts.get("facts", []):
                await db.execute(
                    "INSERT INTO world_facts (fact, created_at) VALUES (?, ?)",
                    (fact, now),
                )
            await db.commit()

    async def get_context(self) -> str:
        """Return a summary of the world model for injection into the system prompt."""
        await self._ensure()
        if not self._ready:
            return ""
        import aiosqlite

        parts = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT name, relationship, notes FROM people ORDER BY updated_at DESC LIMIT 10") as cur:
                people = await cur.fetchall()
                if people:
                    parts.append("People: " + "; ".join(
                        f"{p[0]} ({p[1]})" + (f" — {p[2]}" if p[2] else "")
                        for p in people
                    ))

            async with db.execute("SELECT name, status FROM projects ORDER BY updated_at DESC LIMIT 5") as cur:
                projects = await cur.fetchall()
                if projects:
                    parts.append("Projects: " + "; ".join(
                        f"{p[0]} [{p[1]}]" for p in projects
                    ))

            async with db.execute("SELECT goal, priority FROM goals ORDER BY updated_at DESC LIMIT 5") as cur:
                goals = await cur.fetchall()
                if goals:
                    parts.append("Goals: " + "; ".join(
                        f"{g[0]} ({g[1]})" for g in goals
                    ))

            async with db.execute("SELECT preference FROM preferences ORDER BY updated_at DESC LIMIT 10") as cur:
                prefs = await cur.fetchall()
                if prefs:
                    parts.append("Preferences: " + "; ".join(p[0] for p in prefs))

        return "\n".join(parts)

    async def query(self, question: str) -> str:
        """Query the world model about the user."""
        context = await self.get_context()
        if not context:
            return "World model is empty — no facts stored yet."
        return context
