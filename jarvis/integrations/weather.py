"""Weather integration via open-meteo (free, no API key needed).

Uses geopy + OpenStreetMap for geocoding.
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Heavy thunderstorm with hail",
}


async def _geocode(location: str) -> tuple[float, float]:
    """Geocode a location string to (lat, lon)."""
    import httpx

    resp = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": location, "format": "json", "limit": 1},
        headers={"User-Agent": "JARVIS.AGI/1.0"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(f"Location '{location}' not found.")
    return float(data[0]["lat"]), float(data[0]["lon"])


class WeatherCurrentTool(Tool):
    name = "weather_current"
    description = "Get the current weather for a location."
    parameters = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name or address"},
        },
        "required": ["location"],
    }

    async def execute(self, location: str) -> str:
        try:
            import httpx

            lat, lon = await _geocode(location)
            resp = httpx.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": True,
                    "hourly": "relativehumidity_2m",
                    "temperature_unit": "celsius",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            w = data["current_weather"]
            temp = w["temperature"]
            wind = w["windspeed"]
            code = w["weathercode"]
            desc = _WMO_CODES.get(code, f"Code {code}")
            return f"Current weather in {location}: {desc}, {temp}°C, wind {wind} km/h"
        except Exception as exc:
            logger.error("weather_current failed: %s", exc)
            return f"Error getting weather: {exc}"


class WeatherForecastTool(Tool):
    name = "weather_forecast"
    description = "Get a multi-day weather forecast for a location."
    parameters = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name or address"},
            "days": {"type": "integer", "description": "Number of days ahead (1-7, default 3)"},
        },
        "required": ["location"],
    }

    async def execute(self, location: str, days: int = 3) -> str:
        try:
            import httpx

            days = max(1, min(days, 7))
            lat, lon = await _geocode(location)
            resp = httpx.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
                    "forecast_days": days,
                    "temperature_unit": "celsius",
                    "timezone": "auto",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            daily = data["daily"]
            lines = []
            for i in range(days):
                date = daily["time"][i]
                code = daily["weathercode"][i]
                desc = _WMO_CODES.get(code, f"Code {code}")
                tmax = daily["temperature_2m_max"][i]
                tmin = daily["temperature_2m_min"][i]
                precip = daily["precipitation_sum"][i]
                lines.append(
                    f"{date}: {desc}, {tmin}–{tmax}°C, precipitation {precip} mm"
                )
            return f"Forecast for {location}:\n" + "\n".join(lines)
        except Exception as exc:
            logger.error("weather_forecast failed: %s", exc)
            return f"Error getting forecast: {exc}"


class WeatherIntegration(Integration):
    name = "weather"

    def is_configured(self) -> bool:
        return True  # No API key needed

    def get_tools(self) -> list[Tool]:
        return [WeatherCurrentTool(), WeatherForecastTool()]
