"""File system integration — sandboxed to user-configured directories.

Set FS_ALLOWED_DIRS in .env (comma-separated) to restrict access.
Default: user's home directory.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from pathlib import Path

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _allowed_dirs() -> list[Path]:
    raw = os.getenv("FS_ALLOWED_DIRS", str(Path.home()))
    return [Path(p.strip()).resolve() for p in raw.split(",") if p.strip()]


def _safe_path(path_str: str) -> Path:
    """Resolve a path and verify it's within allowed directories."""
    p = Path(path_str).resolve()
    for allowed in _allowed_dirs():
        try:
            p.relative_to(allowed)
            return p
        except ValueError:
            continue
    raise PermissionError(
        f"Path '{path_str}' is outside allowed directories: {_allowed_dirs()}"
    )


class FsReadFileTool(Tool):
    name = "fs_read_file"
    description = "Read the contents of a file."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path"},
            "max_chars": {"type": "integer", "description": "Max characters to return (default 10000)"},
        },
        "required": ["path"],
    }

    async def execute(self, path: str, max_chars: int = 10000) -> str:
        try:
            safe = _safe_path(path)
            text = safe.read_text(encoding="utf-8", errors="replace")
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n...[truncated — file has {len(text)} chars]"
            return text
        except PermissionError as exc:
            return str(exc)
        except Exception as exc:
            logger.error("fs_read_file failed: %s", exc)
            return f"Error reading file: {exc}"


class FsWriteFileTool(Tool):
    name = "fs_write_file"
    description = "Write or overwrite a file with the given content."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write"},
            "content": {"type": "string", "description": "Content to write"},
            "append": {
                "type": "boolean",
                "description": "If true, append instead of overwrite (default false)",
            },
        },
        "required": ["path", "content"],
    }

    async def execute(self, path: str, content: str, append: bool = False) -> str:
        try:
            safe = _safe_path(path)
            safe.parent.mkdir(parents=True, exist_ok=True)
            if append:
                with safe.open("a", encoding="utf-8") as f:
                    f.write(content)
            else:
                safe.write_text(content, encoding="utf-8")
            return f"{'Appended to' if append else 'Wrote'} {safe} ({len(content)} chars)"
        except PermissionError as exc:
            return str(exc)
        except Exception as exc:
            logger.error("fs_write_file failed: %s", exc)
            return f"Error writing file: {exc}"


class FsListDirectoryTool(Tool):
    name = "fs_list_directory"
    description = "List the contents of a directory."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: home dir)"},
            "pattern": {"type": "string", "description": "Glob pattern to filter (e.g. *.py)"},
        },
    }

    async def execute(self, path: str = "", pattern: str = "*") -> str:
        try:
            dir_path = _safe_path(path or str(Path.home()))
            if not dir_path.is_dir():
                return f"'{path}' is not a directory."
            entries = sorted(dir_path.glob(pattern))
            if not entries:
                return f"No files matching '{pattern}' in {dir_path}."
            lines = []
            for entry in entries[:100]:
                kind = "📁" if entry.is_dir() else "📄"
                lines.append(f"{kind} {entry.name}")
            suffix = f"\n... and {len(entries) - 100} more" if len(entries) > 100 else ""
            return "\n".join(lines) + suffix
        except PermissionError as exc:
            return str(exc)
        except Exception as exc:
            logger.error("fs_list_directory failed: %s", exc)
            return f"Error listing directory: {exc}"


class FsSearchFilesTool(Tool):
    name = "fs_search_files"
    description = "Search for files containing specific text."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text to search for"},
            "directory": {"type": "string", "description": "Directory to search in"},
            "file_pattern": {"type": "string", "description": "File glob pattern (e.g. *.txt)"},
            "max_results": {"type": "integer", "description": "Max results (default 20)"},
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        directory: str = "",
        file_pattern: str = "*",
        max_results: int = 20,
    ) -> str:
        try:
            search_dir = _safe_path(directory or str(Path.home()))
            results = []
            for file_path in search_dir.rglob(file_pattern):
                if not file_path.is_file():
                    continue
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    if query.lower() in text.lower():
                        results.append(str(file_path))
                        if len(results) >= max_results:
                            break
                except Exception:
                    continue
            if not results:
                return f"No files found containing '{query}'."
            return "\n".join(results)
        except PermissionError as exc:
            return str(exc)
        except Exception as exc:
            logger.error("fs_search_files failed: %s", exc)
            return f"Error searching files: {exc}"


class FsRunScriptTool(Tool):
    name = "fs_run_script"
    description = "Run a script file (Python or shell). Sandboxed to allowed directories."
    parameters = {
        "type": "object",
        "properties": {
            "script_path": {"type": "string", "description": "Path to the script"},
            "args": {"type": "string", "description": "Command-line arguments"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"},
        },
        "required": ["script_path"],
    }

    async def execute(self, script_path: str, args: str = "", timeout: int = 30) -> str:
        try:
            safe = _safe_path(script_path)
            ext = safe.suffix.lower()
            if ext == ".py":
                cmd = ["python", str(safe)] + (args.split() if args else [])
            else:
                cmd = [str(safe)] + (args.split() if args else [])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace")
            errors = stderr.decode("utf-8", errors="replace")
            if errors:
                output += f"\n[stderr]\n{errors}"
            return output or "(no output)"
        except PermissionError as exc:
            return str(exc)
        except asyncio.TimeoutError:
            return f"Script timed out after {timeout}s."
        except Exception as exc:
            logger.error("fs_run_script failed: %s", exc)
            return f"Error running script: {exc}"


class FilesystemIntegration(Integration):
    name = "filesystem"

    def is_configured(self) -> bool:
        return True  # Always available; sandboxed by FS_ALLOWED_DIRS

    def get_tools(self) -> list[Tool]:
        return [
            FsReadFileTool(),
            FsWriteFileTool(),
            FsListDirectoryTool(),
            FsSearchFilesTool(),
            FsRunScriptTool(),
        ]
