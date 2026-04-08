"""Home Assistant integration via REST API.

Required env vars:
  HA_BASE_URL    — e.g. http://homeassistant.local:8123
  HA_TOKEN       — Long-lived access token from HA profile
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['HA_TOKEN']}",
        "Content-Type": "application/json",
    }


def _base() -> str:
    return os.getenv("HA_BASE_URL", "http://homeassistant.local:8123").rstrip("/")


class HAListDevicesTool(Tool):
    name = "ha_list_devices"
    description = "List all devices and entities in Home Assistant."
    parameters = {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Filter by domain: light, switch, sensor, climate, etc.",
            },
        },
    }

    async def execute(self, domain: str = "") -> str:
        try:
            import httpx

            resp = httpx.get(
                f"{_base()}/api/states", headers=_headers(), timeout=10
            )
            resp.raise_for_status()
            states = resp.json()
            if domain:
                states = [s for s in states if s["entity_id"].startswith(f"{domain}.")]
            lines = [
                f"• {s['entity_id']}: {s['state']}"
                for s in states[:50]
            ]
            return "\n".join(lines) or f"No entities found for domain '{domain}'."
        except Exception as exc:
            logger.error("ha_list_devices failed: %s", exc)
            return f"Error listing HA devices: {exc}"


class HAControlDeviceTool(Tool):
    name = "ha_control_device"
    description = "Turn on/off or control a Home Assistant device."
    parameters = {
        "type": "object",
        "properties": {
            "entity_id": {"type": "string", "description": "Entity ID (e.g. light.living_room)"},
            "action": {
                "type": "string",
                "description": "Action: 'turn_on', 'turn_off', 'toggle'",
            },
            "brightness": {
                "type": "integer",
                "description": "Brightness 0-255 (for lights)",
            },
            "temperature": {
                "type": "number",
                "description": "Target temperature (for climate entities)",
            },
        },
        "required": ["entity_id", "action"],
    }

    async def execute(
        self,
        entity_id: str,
        action: str,
        brightness: int | None = None,
        temperature: float | None = None,
    ) -> str:
        try:
            import httpx

            domain = entity_id.split(".")[0]
            service_data: dict = {"entity_id": entity_id}
            if brightness is not None:
                service_data["brightness"] = brightness
            if temperature is not None:
                service_data["temperature"] = temperature

            resp = httpx.post(
                f"{_base()}/api/services/{domain}/{action}",
                headers=_headers(),
                json=service_data,
                timeout=10,
            )
            resp.raise_for_status()
            return f"HA: {action} applied to {entity_id}."
        except Exception as exc:
            logger.error("ha_control_device failed: %s", exc)
            return f"Error controlling device: {exc}"


class HAGetStateTool(Tool):
    name = "ha_get_state"
    description = "Get the current state of a Home Assistant entity."
    parameters = {
        "type": "object",
        "properties": {
            "entity_id": {"type": "string", "description": "Entity ID"},
        },
        "required": ["entity_id"],
    }

    async def execute(self, entity_id: str) -> str:
        try:
            import httpx

            resp = httpx.get(
                f"{_base()}/api/states/{entity_id}",
                headers=_headers(),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            state = data.get("state", "unknown")
            attrs = data.get("attributes", {})
            attr_str = ", ".join(f"{k}: {v}" for k, v in list(attrs.items())[:5])
            return f"{entity_id}: {state}" + (f" ({attr_str})" if attr_str else "")
        except Exception as exc:
            logger.error("ha_get_state failed: %s", exc)
            return f"Error getting state: {exc}"


class HomeAssistantIntegration(Integration):
    name = "home_assistant"

    def is_configured(self) -> bool:
        return bool(os.getenv("HA_BASE_URL") and os.getenv("HA_TOKEN"))

    def get_tools(self) -> list[Tool]:
        return [HAListDevicesTool(), HAControlDeviceTool(), HAGetStateTool()]
