"""Calendar platform for Spond Calendar integration."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SpondCoordinator
from .const import CONF_GROUP_ID, CONF_GROUP_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


# Emoji ranges covering the common pictographic blocks, plus the glue
# codepoints (VS-16, ZWJ) used in composite emoji like 👨‍👩‍👧.
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FFFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    if not text:
        return text
    return " ".join(_EMOJI_RE.sub("", text).split()).strip()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SpondCoordinator = entry.runtime_data
    async_add_entities([SpondCalendarEntity(coordinator, entry)], update_before_add=False)


def _parse_event(
    raw: dict[str, Any],
    *,
    strip_emoji: bool = False,
    strip_description_emoji: bool = False,
) -> CalendarEvent | None:
    try:
        start_str: str | None = raw.get("startTimestamp")
        end_str: str | None = raw.get("endTimestamp")

        if not start_str:
            return None

        start = _parse_dt(start_str)
        end = _parse_dt(end_str) if end_str else start

        summary = raw.get("heading", "Spond event")
        if strip_emoji:
            summary = _strip_emoji(summary) or "Spond event"

        description = raw.get("description") or None
        if description and strip_description_emoji:
            description = _strip_emoji(description) or None

        return CalendarEvent(
            start=start,
            end=end,
            summary=summary,
            description=description,
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


def _invites_sent(raw: dict[str, Any]) -> bool:
    invite_time = raw.get("inviteTime")
    if not invite_time:
        return True
    try:
        return _parse_dt(invite_time) <= datetime.now(tz=timezone.utc)
    except (ValueError, TypeError):
        return True


def _get_rsvp_statuses(raw: dict[str, Any], person_ids: list[str]) -> list[str]:
    if not person_ids:
        return []
    responses = raw.get("responses") or {}
    accepted = set(responses.get("acceptedIds", []) or [])
    declined = set(responses.get("declinedIds", []) or [])
    unanswered = set(responses.get("unansweredIds", []) or [])

    statuses: list[str] = []
    for pid in person_ids:
        if pid in accepted:
            statuses.append("accepted")
        elif pid in declined:
            statuses.append("declined")
        elif pid in unanswered:
            statuses.append("unanswered")
    return statuses


class SpondCalendarEntity(CoordinatorEntity[SpondCoordinator], CalendarEntity):

    _attr_has_entity_name = True

    def __init__(self, coordinator: SpondCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        group_id: str = entry.data[CONF_GROUP_ID]
        group_name: str = entry.data.get(CONF_GROUP_NAME, group_id)
        self._attr_unique_id = f"{DOMAIN}_{group_id}"
        self._attr_name = group_name
        self._group_id = group_id

    def _should_hide(self, statuses: list[str]) -> bool:
        if not self.coordinator.hide_declined or not statuses:
            return False
        if self.coordinator.hide_declined_require_all:
            return all(s == "declined" for s in statuses)
        return any(s == "declined" for s in statuses)

    def _is_unanswered(self, statuses: list[str]) -> bool:
        if not statuses:
            return False
        if self.coordinator.unanswered_require_all:
            return all(s == "unanswered" for s in statuses)
        return any(s == "unanswered" for s in statuses)

    def _apply_rsvp_indicator(
        self, ev: CalendarEvent, statuses: list[str]
    ) -> CalendarEvent:
        if not self.coordinator.show_unanswered_indicator:
            return ev
        if not self._is_unanswered(statuses):
            return ev
        prefix = self.coordinator.unanswered_prefix
        summary = f"{prefix} {ev.summary}".strip() if prefix else ev.summary
        return CalendarEvent(
            start=ev.start,
            end=ev.end,
            summary=summary,
            description=ev.description,
            location=ev.location,
            uid=ev.uid,
        )

    def _process_raw(self, raw: dict[str, Any]) -> CalendarEvent | None:
        statuses = _get_rsvp_statuses(raw, self.coordinator.my_person_ids) if _invites_sent(raw) else []
        if self._should_hide(statuses):
            return None
        ev = _parse_event(
            raw,
            strip_emoji=self.coordinator.strip_emoji,
            strip_description_emoji=self.coordinator.strip_description_emoji,
        )
        if ev is None:
            return None
        return self._apply_rsvp_indicator(ev, statuses)

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
