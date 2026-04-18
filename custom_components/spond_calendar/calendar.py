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
    coordinator: SpondCoordinator = entry.runtime_data
    async_add_entities([SpondCalendarEntity(coordinator, entry)], update_before_add=False)


def _parse_event(raw: dict[str, Any]) -> CalendarEvent | None:
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

        return CalendarEvent(
            start=start,
            end=end,
            summary=summary,
            description="\n".join(description_parts) if description_parts else None,
            location=_extract_location(raw.get("location")),
            uid=raw.get("id"),
        )
    except Exception:
        _LOGGER.debug("Failed to parse Spond event: %s", raw, exc_info=True)
        return None


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _extract_location(loc: dict[str, Any] | None) -> str | None:
    if not loc:
        return None
    parts: list[str] = []
    if loc.get("feature"):
        parts.append(loc["feature"])
    if loc.get("address"):
        parts.append(loc["address"])
    return ", ".join(parts) if parts else None


def _get_rsvp_status(raw: dict[str, Any], person_id: str | None) -> str:
    if not person_id:
        return "unknown"
    responses = raw.get("responses", {})
    if person_id in responses.get("acceptedIds", []):
        return "accepted"
    if person_id in responses.get("declinedIds", []):
        return "declined"
    if person_id in responses.get("unansweredIds", []):
        return "unanswered"
    return "unknown"


class SpondCalendarEntity(CoordinatorEntity[SpondCoordinator], CalendarEntity):

    _attr_has_entity_name = True

    def __init__(self, coordinator: SpondCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        group_id: str = entry.data[CONF_GROUP_ID]
        group_name: str = entry.data.get(CONF_GROUP_NAME, group_id)
        self._attr_unique_id = f"{DOMAIN}_{group_id}"
        self._attr_name = group_name
        self._group_id = group_id

    def _should_hide(self, rsvp: str) -> bool:
        return self.coordinator.hide_declined and rsvp == "declined"

    def _apply_rsvp_indicator(self, ev: CalendarEvent, rsvp: str) -> CalendarEvent:
        if rsvp != "unanswered" or not self.coordinator.show_unanswered_indicator:
            return ev
        prefix = self.coordinator.unanswered_prefix
        return CalendarEvent(
            start=ev.start,
            end=ev.end,
            summary=f"{prefix} {ev.summary}",
            description=ev.description,
            location=ev.location,
            uid=ev.uid,
        )

    def _process_raw(self, raw: dict[str, Any]) -> CalendarEvent | None:
        rsvp = _get_rsvp_status(raw, self.coordinator.my_person_id)
        if self._should_hide(rsvp):
            return None
        ev = _parse_event(raw)
        if ev is None:
            return None
        return self._apply_rsvp_indicator(ev, rsvp)

    @property
    def event(self) -> CalendarEvent | None:
        if not self.coordinator.data:
            return None
        now = datetime.now(tz=timezone.utc)
        for raw in self.coordinator.data:
            ev = self._process_raw(raw)
            if ev and ev.start <= now <= ev.end:
                return ev
        upcoming: CalendarEvent | None = None
        for raw in self.coordinator.data:
            ev = self._process_raw(raw)
            if ev and ev.start > now:
                if upcoming is None or ev.start < upcoming.start:
                    upcoming = ev
        return upcoming

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        if not self.coordinator.data:
            return []
        results: list[CalendarEvent] = []
        for raw in self.coordinator.data:
            ev = self._process_raw(raw)
            if ev and ev.end >= start_date and ev.start <= end_date:
                results.append(ev)
        results.sort(key=lambda e: e.start)
        return results
