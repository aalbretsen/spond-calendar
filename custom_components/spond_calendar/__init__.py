"""The Spond Calendar integration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_GROUP_ID,
    CONF_HIDE_DECLINED,
    CONF_INCLUDE_PLANNED,
    CONF_SHOW_UNANSWERED_INDICATOR,
    CONF_SPOND_EMAIL,
    CONF_SPOND_PASSWORD,
    CONF_UNANSWERED_PREFIX,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_DAYS_BACK,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_UNANSWERED_PREFIX,
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
        self._my_person_id: str | None = None

    @property
    def include_planned(self) -> bool:
        return self._entry.options.get(CONF_INCLUDE_PLANNED, False)

    @property
    def show_unanswered_indicator(self) -> bool:
        return self._entry.options.get(CONF_SHOW_UNANSWERED_INDICATOR, True)

    @property
    def unanswered_prefix(self) -> str:
        return self._entry.options.get(CONF_UNANSWERED_PREFIX, DEFAULT_UNANSWERED_PREFIX)

    @property
    def hide_declined(self) -> bool:
        return self._entry.options.get(CONF_HIDE_DECLINED, False)

    @property
    def my_person_id(self) -> str | None:
        return self._my_person_id

    async def _ensure_client(self) -> Any:
        if self._client is None:
            from spond import spond as spond_module  # noqa: PLC0415
            self._client = spond_module.Spond(username=self._email, password=self._password)
        return self._client

    async def _resolve_my_person_id(self, client: Any) -> str | None:
        # Matches the logged-in user by email against group.members[].profile.email,
        # avoiding a separate /me API call that the library does not expose.
        try:
            groups = await client.get_groups()
            for group in groups:
                if group.get("id") != self._group_id:
                    continue
                for member in group.get("members", []):
                    profile = member.get("profile", {})
                    if profile.get("email", "").lower() == self._email.lower():
                        person_id = member.get("id")
                        _LOGGER.debug("Resolved Spond member ID: %s", person_id)
                        return person_id
            _LOGGER.debug("User %s not found in group %s members", self._email, self._group_id)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Failed to resolve person ID", exc_info=True)
        return None

    async def _async_update_data(self) -> list[dict[str, Any]]:
        try:
            client = await self._ensure_client()

            if self._my_person_id is None:
                self._my_person_id = await self._resolve_my_person_id(client)

            now = datetime.now(tz=timezone.utc)
            events: list[dict[str, Any]] = await client.get_events(
                group_id=self._group_id,
                include_scheduled=self.include_planned,
                min_end=now - timedelta(days=DEFAULT_DAYS_BACK),
                max_end=now + timedelta(days=DEFAULT_DAYS_AHEAD),
                max_events=200,
            )
            return events

        except Exception as err:
            # Close the client so a fresh session is created on the next poll.
            await self._close_client()
            raise UpdateFailed(f"Error fetching Spond events: {err}") from err

    async def _close_client(self) -> None:
        if self._client is not None:
            try:
                await self._client.clientsession.close()
            except Exception:  # noqa: BLE001
                pass
            self._client = None
        self._my_person_id = None

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
