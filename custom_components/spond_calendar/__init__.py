"""The Spond Calendar integration."""
from __future__ import annotations

import contextlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_GROUP_ID,
    CONF_HIDE_DECLINED,
    CONF_HIDE_DECLINED_REQUIRE_ALL,
    CONF_INCLUDE_PLANNED,
    CONF_SHOW_UNANSWERED_INDICATOR,
    CONF_SPOND_EMAIL,
    CONF_SPOND_PASSWORD,
    CONF_STRIP_DESCRIPTION_EMOJI,
    CONF_STRIP_TITLE_EMOJI,
    CONF_UNANSWERED_PREFIX,
    CONF_UNANSWERED_REQUIRE_ALL,
    CONF_USE_MEETUP_TIME_AS_DESCRIPTION,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_DAYS_BACK,
    DEFAULT_HIDE_DECLINED,
    DEFAULT_HIDE_DECLINED_REQUIRE_ALL,
    DEFAULT_INCLUDE_PLANNED,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_SHOW_UNANSWERED_INDICATOR,
    DEFAULT_STRIP_DESCRIPTION_EMOJI,
    DEFAULT_STRIP_TITLE_EMOJI,
    DEFAULT_UNANSWERED_PREFIX,
    DEFAULT_UNANSWERED_REQUIRE_ALL,
    DEFAULT_USE_MEETUP_TIME_AS_DESCRIPTION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR]

type SpondCalendarConfigEntry = ConfigEntry[SpondCoordinator]


class SpondCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
        )
        self._entry = entry
        self._email: str = entry.data[CONF_SPOND_EMAIL]
        self._password: str = entry.data[CONF_SPOND_PASSWORD]
        self._group_id: str = entry.data[CONF_GROUP_ID]
        self._client: Any | None = None
        self._my_person_ids: list[str] = []

    @property
    def include_planned(self) -> bool:
        return self._entry.options.get(CONF_INCLUDE_PLANNED, DEFAULT_INCLUDE_PLANNED)

    @property
    def show_unanswered_indicator(self) -> bool:
        return self._entry.options.get(
            CONF_SHOW_UNANSWERED_INDICATOR, DEFAULT_SHOW_UNANSWERED_INDICATOR
        )

    @property
    def unanswered_prefix(self) -> str:
        return self._entry.options.get(CONF_UNANSWERED_PREFIX, DEFAULT_UNANSWERED_PREFIX)

    @property
    def hide_declined(self) -> bool:
        return self._entry.options.get(CONF_HIDE_DECLINED, DEFAULT_HIDE_DECLINED)

    @property
    def unanswered_require_all(self) -> bool:
        return self._entry.options.get(
            CONF_UNANSWERED_REQUIRE_ALL, DEFAULT_UNANSWERED_REQUIRE_ALL
        )

    @property
    def hide_declined_require_all(self) -> bool:
        return self._entry.options.get(
            CONF_HIDE_DECLINED_REQUIRE_ALL, DEFAULT_HIDE_DECLINED_REQUIRE_ALL
        )

    @property
    def strip_title_emoji(self) -> bool:
        return self._entry.options.get(
            CONF_STRIP_TITLE_EMOJI, DEFAULT_STRIP_TITLE_EMOJI
        )

    @property
    def strip_description_emoji(self) -> bool:
        return self._entry.options.get(
            CONF_STRIP_DESCRIPTION_EMOJI, DEFAULT_STRIP_DESCRIPTION_EMOJI
        )

    @property
    def use_meetup_time_as_description(self) -> bool:
        return self._entry.options.get(
            CONF_USE_MEETUP_TIME_AS_DESCRIPTION,
            DEFAULT_USE_MEETUP_TIME_AS_DESCRIPTION,
        )

    @property
    def language(self) -> str:
        return self.hass.config.language

    @property
    def my_person_ids(self) -> list[str]:
        return list(self._my_person_ids)

    async def _ensure_client(self) -> Any:
        if self._client is None:
            from spond import spond as spond_module  # noqa: PLC0415
            self._client = spond_module.Spond(
                username=self._email, password=self._password
            )
        return self._client

    async def _resolve_my_person_ids(self, client: Any) -> list[str]:
        """Return member IDs in the group for the user and any children they guard."""
        my_email = self._email.lower()
        person_ids: list[str] = []

        def _add(mid: str | None) -> None:
            if mid and mid not in person_ids:
                person_ids.append(mid)

        try:
            groups = await client.get_groups()
            for group in groups:
                if group.get("id") != self._group_id:
                    continue

                for member in group.get("members", []):
                    member_id = member.get("id")
                    member_profile = member.get("profile") or {}
                    if (member_profile.get("email") or "").lower() == my_email:
                        _add(member_id)
                        continue

                    for guardian in member.get("guardians", []) or []:
                        g_profile = guardian.get("profile") or {}
                        g_email = (
                            g_profile.get("email") or guardian.get("email") or ""
                        ).lower()
                        if g_email and g_email == my_email:
                            _add(member_id)
                            break

                break

            _LOGGER.debug(
                "Resolved %d Spond member ID(s) for %s in group %s: %s",
                len(person_ids),
                self._email,
                self._group_id,
                person_ids,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Failed to resolve person IDs", exc_info=True)
        return person_ids

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            client = await self._ensure_client()

            if not self._my_person_ids:
                self._my_person_ids = await self._resolve_my_person_ids(client)

            now = datetime.now(tz=timezone.utc)
            events: list[dict[str, Any]] = await client.get_events(
                group_id=self._group_id,
                include_scheduled=self.include_planned,
                min_end=now - timedelta(days=DEFAULT_DAYS_BACK),
                max_end=now + timedelta(days=DEFAULT_DAYS_AHEAD),
                max_events=200,
            )
        except Exception as err:
            await self._close_client()
            raise UpdateFailed(f"Error fetching Spond events: {err}") from err
        return events

    async def _close_client(self) -> None:
        if self._client is not None:
            with contextlib.suppress(Exception):
                await self._client.clientsession.close()
            self._client = None
        self._my_person_ids = []

    async def async_shutdown(self) -> None:
        await self._close_client()
        await super().async_shutdown()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SpondCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: SpondCoordinator = entry.runtime_data
    await coordinator.async_shutdown()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
