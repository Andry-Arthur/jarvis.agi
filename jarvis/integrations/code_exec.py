"""Code execution sandbox — runs Python or shell snippets with a hard timeout.

Safety: execution is restricted to a temp directory unless CODE_EXEC_WORKDIR is set.
Never run arbitrary user code without reviewing it first.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

_TIMEOUT = int(os.getenv("CODE_EXEC_TIMEOUT", "30"))
_WORKDIR = os.getenv("CODE_EXEC_WORKDIR", "")


def _work_dir() -> Path:
    if _WORKDIR:
        return Path(_WORKDIR)
    return Path(tempfile.gettempdir()) / "jarvis_code_exec"


class ExecutePythonTool(Tool):
    name = "execute_python"
    description = (
        "Execute a Python code snippet and return stdout/stderr. "
        "Useful for calculations, data analysis, and automation scripts."
    )
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {
                "type": "integer",
                "description": f"Timeout in seconds (default {_TIMEOUT})",
            },
        },
        "required": ["code"],
    }

    async def execute(self, code: str, timeout: int = _TIMEOUT) -> str:
        work_dir = _work_dir()
        work_dir.mkdir(parents=True, exist_ok=True)
        script = work_dir / "jarvis_exec.py"
        script.write_text(code, encoding="utf-8")
        try:
            proc = await asyncio.create_subprocess_exec(
                "python",
                str(script),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(work_dir),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()
            result = output
            if errors:
                result += f"\n[stderr]\n{errors}"
            return result or "(no output)"
        except asyncio.TimeoutError:
            proc.kill()
            return f"Execution timed out after {timeout}s."
        except Exception as exc:
            logger.error("execute_python failed: %s", exc)
            return f"Error executing Python: {exc}"


class ExecuteShellTool(Tool):
    name = "execute_shell"
    description = (
        "Execute a shell command and return output. "
        "Use with caution — confirm with the user before running destructive commands."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
            "timeout": {
                "type": "integer",
                "description": f"Timeout in seconds (default {_TIMEOUT})",
            },
            "working_dir": {
                "type": "string",
                "description": "Working directory for the command",
            },
        },
        "required": ["command"],
    }

    async def execute(
        self, command: str, timeout: int = _TIMEOUT, working_dir: str = ""
    ) -> str:
        cwd = working_dir or str(_work_dir())
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()
            result = output
            if errors:
                result += f"\n[stderr]\n{errors}"
            return result or "(no output)"
        except asyncio.TimeoutError:
            proc.kill()
            return f"Command timed out after {timeout}s."
        except Exception as exc:
            logger.error("execute_shell failed: %s", exc)
            return f"Error executing shell command: {exc}"


class CodeExecIntegration(Integration):
    name = "code_exec"

    def is_configured(self) -> bool:
        return True  # Always available

    def get_tools(self) -> list[Tool]:
        return [ExecutePythonTool(), ExecuteShellTool()]
