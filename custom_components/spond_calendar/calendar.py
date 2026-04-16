"""Calendar platform for Spond Calendar integration."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SpondCoordinator
from .const import CONF_GROUP_ID, CONF_GROUP_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Spond calendar entity from a config entry."""
    coordinator: SpondCoordinator = entry.runtime_data

    async_add_entities(
        [SpondCalendarEntity(coordinator, entry)],
        update_before_add=False,
    )


def _parse_event(raw: dict[str, Any]) -> CalendarEvent | None:
    """Convert a raw Spond event dict into a HA CalendarEvent."""
    try:
        start_str: str | None = raw.get("startTimestamp")
        end_str: str | None = raw.get("endTimestamp")

        if not start_str:
            return None

        start = _parse_dt(start_str)
        end = _parse_dt(end_str) if end_str else start

        summary = raw.get("heading", "Spond event")

        description_parts: list[str] = []
        if raw.get("description"):
            description_parts.append(raw["description"])
        if raw.get("type"):
            description_parts.append(f"Type: {raw['type']}")

        # Build location string from the nested location object
        location = _extract_location(raw.get("location"))

        return CalendarEvent(
            start=start,
            end=end,
            summary=summary,
            description="\n".join(description_parts) if description_parts else None,
            location=location,
            uid=raw.get("id"),
        )
    except Exception:
        _LOGGER.debug("Failed to parse Spond event: %s", raw, exc_info=True)
        return None


def _parse_dt(value: str) -> datetime:
    """Parse an ISO-8601 timestamp, ensuring it is timezone-aware."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extract_location(loc: dict[str, Any] | None) -> str | None:
    """Build a human-readable location string from Spond's location object."""
    if not loc:
        return None

    parts: list[str] = []

    # Spond uses "feature" for the venue name
    if loc.get("feature"):
        parts.append(loc["feature"])
    if loc.get("address"):
        parts.append(loc["address"])

    return ", ".join(parts) if parts else None


class SpondCalendarEntity(
    CoordinatorEntity[SpondCoordinator], CalendarEntity
):
    """A calendar entity exposing events from a single Spond group."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SpondCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)

        group_id: str = entry.data[CONF_GROUP_ID]
        group_name: str = entry.data.get(CONF_GROUP_NAME, group_id)

        self._attr_unique_id = f"{DOMAIN}_{group_id}"
        self._attr_name = group_name
        self._group_id = group_id

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event."""
        if not self.coordinator.data:
            return None

        now = datetime.now(tz=timezone.utc)

        # Find an active event (started, not yet ended)
        for raw in self.coordinator.data:
            ev = _parse_event(raw)
            if ev is None:
                continue
            if ev.start <= now <= ev.end:
                return ev

        # Otherwise return the next upcoming event
        upcoming: CalendarEvent | None = None
        for raw in self.coordinator.data:
            ev = _parse_event(raw)
            if ev is None:
                continue
            if ev.start > now:
                if upcoming is None or ev.start < upcoming.start:
                    upcoming = ev
        return upcoming

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return events within the requested window (used by the calendar card)."""
        if not self.coordinator.data:
            return []

        results: list[CalendarEvent] = []
        for raw in self.coordinator.data:
            ev = _parse_event(raw)
            if ev is None:
                continue
            # Include if the event overlaps with [start_date, end_date]
            if ev.end >= start_date and ev.start <= end_date:
                results.append(ev)

        results.sort(key=lambda e: e.start)
        return results
