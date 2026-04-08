"""Plugin loader — discovers and loads JARVIS plugins from the plugins directory.

Plugin structure:
  .jarvis/plugins/my_plugin/
    plugin.json        — manifest (required)
    tools.py           — Tool subclasses (optional)
    __init__.py        — entry point (optional)

plugin.json format:
  {
    "name": "my_plugin",
    "version": "1.0.0",
    "description": "What this plugin does",
    "author": "Your Name",
    "tools_module": "tools",    // Python module file to import (default: tools)
    "tools_class": "MyTool",    // Optional: specific class name to load
    "requires": ["requests"]    // Optional: pip packages required
  }
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    name: str
    version: str = "0.0.1"
    description: str = ""
    author: str = ""
    tools_module: str = "tools"
    tools_class: str = ""
    requires: list[str] = field(default_factory=list)
    plugin_dir: Path = field(default_factory=Path)

    @classmethod
    def from_file(cls, path: Path) -> "PluginManifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            name=data.get("name", path.parent.name),
            version=data.get("version", "0.0.1"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            tools_module=data.get("tools_module", "tools"),
            tools_class=data.get("tools_class", ""),
            requires=data.get("requires", []),
            plugin_dir=path.parent,
        )


class PluginLoader:
    """Discovers, validates, and loads JARVIS plugins."""

    def __init__(self, plugins_dir: str = ".jarvis/plugins") -> None:
        self.plugins_dir = Path(plugins_dir)
        self._loaded: dict[str, PluginManifest] = {}

    def discover(self) -> list[PluginManifest]:
        """Scan plugins directory and return all valid plugin manifests."""
        if not self.plugins_dir.exists():
            return []
        manifests = []
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            manifest_file = plugin_dir / "plugin.json"
            if not manifest_file.exists():
                logger.warning("Plugin dir '%s' missing plugin.json — skipping", plugin_dir.name)
                continue
            try:
                manifest = PluginManifest.from_file(manifest_file)
                manifests.append(manifest)
            except Exception as exc:
                logger.warning("Failed to parse plugin '%s': %s", plugin_dir.name, exc)
        return manifests

    def load_tools(self, manifest: PluginManifest) -> list:
        """Import and return Tool instances from a plugin."""
        from jarvis.core.tools import Tool

        tools_file = manifest.plugin_dir / f"{manifest.tools_module}.py"
        if not tools_file.exists():
            logger.warning("Plugin '%s' tools file not found: %s", manifest.name, tools_file)
            return []

        spec = importlib.util.spec_from_file_location(
            f"jarvis_plugin_{manifest.name}", tools_file
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            logger.error("Failed to load plugin '%s': %s", manifest.name, exc)
            return []

        tools = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Tool)
                and attr is not Tool
            ):
                if not manifest.tools_class or attr_name == manifest.tools_class:
                    try:
                        tools.append(attr())
                    except Exception as exc:
                        logger.warning("Failed to instantiate %s: %s", attr_name, exc)

        self._loaded[manifest.name] = manifest
        logger.info("Plugin '%s' loaded with %d tool(s)", manifest.name, len(tools))
        return tools

    def load_all(self, registry) -> int:
        """Load all discovered plugins into a ToolRegistry. Returns number of tools loaded."""
        total = 0
        for manifest in self.discover():
            tools = self.load_tools(manifest)
            registry.register_many(tools)
            total += len(tools)
        return total

    def install(self, plugin_path_or_name: str) -> bool:
        """Install a plugin from a local directory path."""
        src = Path(plugin_path_or_name)
        if not src.exists():
            logger.error("Plugin path not found: %s", plugin_path_or_name)
            return False
        manifest_file = src / "plugin.json"
        if not manifest_file.exists():
            logger.error("No plugin.json in %s", src)
            return False

        manifest = PluginManifest.from_file(manifest_file)
        dest = self.plugins_dir / manifest.name
        dest.mkdir(parents=True, exist_ok=True)

        import shutil
        for item in src.iterdir():
            if item.name.startswith("."):
                continue
            target = dest / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

        # Install requirements
        if manifest.requires:
            import subprocess
            subprocess.run(
                ["pip", "install"] + manifest.requires,
                check=False,
                capture_output=True,
            )

        logger.info("Plugin '%s' installed to %s", manifest.name, dest)
        return True

    @property
    def loaded_plugins(self) -> list[str]:
        return list(self._loaded.keys())
