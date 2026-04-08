"""Base class for all JARVIS integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Integration(ABC):
    """An integration bundles one or more Tool instances for a single platform."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable integration name, e.g. 'Gmail'."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when the integration has valid credentials."""
        ...

    @abstractmethod
    def get_tools(self) -> list:
        """Return the list of Tool objects this integration provides."""
        ...

    def status(self) -> dict:
        return {"name": self.name, "configured": self.is_configured()}
