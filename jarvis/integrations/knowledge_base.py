"""Personal knowledge base — indexes documents into ChromaDB for semantic search.

Drop files into .jarvis/knowledge/ and JARVIS will index them automatically.
Supported formats: .txt, .md, .pdf, .docx, .html

Install extras: pip install pypdf python-docx beautifulsoup4
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from pathlib import Path

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

_KB_DIR = os.getenv("KB_DIR", ".jarvis/knowledge")
_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", ".jarvis/chroma")
_COLLECTION_NAME = "jarvis_knowledge"
_CHUNK_SIZE = 1000
_CHUNK_OVERLAP = 200


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def _extract_text(file_path: Path) -> str:
    """Extract plain text from a file based on its extension."""
    ext = file_path.suffix.lower()
    try:
        if ext in (".txt", ".md"):
            return file_path.read_text(encoding="utf-8", errors="replace")
        elif ext == ".pdf":
            import pypdf  # type: ignore[import]
            reader = pypdf.PdfReader(str(file_path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == ".docx":
            import docx  # type: ignore[import]
            doc = docx.Document(str(file_path))
            return "\n".join(p.text for p in doc.paragraphs)
        elif ext in (".html", ".htm"):
            from bs4 import BeautifulSoup  # type: ignore[import]
            soup = BeautifulSoup(file_path.read_text(encoding="utf-8"), "html.parser")
            return soup.get_text(separator="\n")
        else:
            return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Could not extract text from %s: %s", file_path, exc)
        return ""


def _get_collection():
    import chromadb

    os.makedirs(_CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=_CHROMA_DIR)
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


class KbIndexTool(Tool):
    name = "kb_index"
    description = "Index a file or directory into the personal knowledge base."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File or directory path to index (default: .jarvis/knowledge/)",
            },
        },
    }

    async def execute(self, path: str = "") -> str:
        try:
            collection = _get_collection()
            target = Path(path) if path else Path(_KB_DIR)
            target.mkdir(parents=True, exist_ok=True)

            files = list(target.rglob("*")) if target.is_dir() else [target]
            files = [f for f in files if f.is_file()]

            indexed = 0
            skipped = 0
            for file_path in files:
                text = _extract_text(file_path)
                if not text.strip():
                    skipped += 1
                    continue

                chunks = _chunk_text(text)
                for i, chunk in enumerate(chunks):
                    chunk_id = hashlib.sha256(
                        f"{file_path}:{i}:{chunk[:50]}".encode()
                    ).hexdigest()[:32]
                    try:
                        collection.upsert(
                            documents=[chunk],
                            ids=[chunk_id],
                            metadatas=[{
                                "source": str(file_path),
                                "chunk": i,
                                "filename": file_path.name,
                            }],
                        )
                    except Exception:
                        pass
                indexed += 1

            return f"Indexed {indexed} file(s) ({skipped} skipped) into knowledge base."
        except Exception as exc:
            logger.error("kb_index failed: %s", exc)
            return f"Error indexing: {exc}"


class KbSearchTool(Tool):
    name = "kb_search"
    description = "Search the personal knowledge base with a semantic query."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "max_results": {"type": "integer", "description": "Number of results (default 5)"},
            "source_filter": {
                "type": "string",
                "description": "Optional: filter by source filename",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self, query: str, max_results: int = 5, source_filter: str = ""
    ) -> str:
        try:
            collection = _get_collection()
            count = collection.count()
            if count == 0:
                return "Knowledge base is empty. Use kb_index to add documents."

            where = {"filename": {"$contains": source_filter}} if source_filter else None
            kwargs = {
                "query_texts": [query],
                "n_results": min(max_results, count),
            }
            if where:
                kwargs["where"] = where

            results = collection.query(**kwargs)
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]

            if not docs:
                return f"No knowledge base results for '{query}'."

            lines = []
            for doc, meta in zip(docs, metas):
                source = meta.get("filename", "unknown")
                lines.append(f"[{source}]\n{doc.strip()}")
            return "\n\n---\n\n".join(lines)
        except Exception as exc:
            logger.error("kb_search failed: %s", exc)
            return f"Error searching knowledge base: {exc}"


class KbListTool(Tool):
    name = "kb_list"
    description = "List all documents indexed in the knowledge base."
    parameters = {"type": "object", "properties": {}}

    async def execute(self) -> str:
        try:
            collection = _get_collection()
            count = collection.count()
            if count == 0:
                return "Knowledge base is empty."
            results = collection.get(limit=200)
            metas = results.get("metadatas", [])
            sources = sorted({m.get("filename", "unknown") for m in metas})
            return f"Knowledge base contains {count} chunks from {len(sources)} file(s):\n" + "\n".join(
                f"• {s}" for s in sources
            )
        except Exception as exc:
            logger.error("kb_list failed: %s", exc)
            return f"Error listing knowledge base: {exc}"


class KnowledgeBaseIntegration(Integration):
    name = "knowledge_base"

    def is_configured(self) -> bool:
        try:
            import chromadb  # noqa: F401
            return True
        except ImportError:
            return False

    def get_tools(self) -> list[Tool]:
        return [KbIndexTool(), KbSearchTool(), KbListTool()]
