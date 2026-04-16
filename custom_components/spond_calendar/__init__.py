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
    CONF_SPOND_EMAIL,
    CONF_SPOND_PASSWORD,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_DAYS_BACK,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR]

type SpondCalendarConfigEntry = ConfigEntry[SpondCoordinator]


class SpondCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator that polls Spond for events."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
        )
        self._email: str = entry.data[CONF_SPOND_EMAIL]
        self._password: str = entry.data[CONF_SPOND_PASSWORD]
        self._group_id: str = entry.data[CONF_GROUP_ID]
        self._client: Any | None = None

    async def _ensure_client(self) -> Any:
        """Lazily create (or re-create) the Spond client."""
        if self._client is None:
            from spond import spond as spond_module  # noqa: PLC0415

            self._client = spond_module.Spond(
                username=self._email, password=self._password
            )
        return self._client

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch upcoming events from Spond."""
        try:
            client = await self._ensure_client()

            now = datetime.now(tz=timezone.utc)
            min_date = now - timedelta(days=DEFAULT_DAYS_BACK)
            max_date = now + timedelta(days=DEFAULT_DAYS_AHEAD)

            events: list[dict[str, Any]] = await client.get_events(
                group_id=self._group_id,
                min_end=min_date,
                max_end=max_date,
                max_events=200,
            )
            return events

        except Exception as err:
            # Force a new client on next poll in case the session expired
            await self._close_client()
            raise UpdateFailed(f"Error fetching Spond events: {err}") from err

    async def _close_client(self) -> None:
        """Cleanly close the underlying HTTP session."""
        if self._client is not None:
            try:
                await self._client.clientsession.close()
            except Exception:  # noqa: BLE001
                pass
            self._client = None

    async def async_shutdown(self) -> None:
        """Shut down the coordinator and close the client."""
        await self._close_client()
        await super().async_shutdown()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Spond Calendar from a config entry."""
    coordinator = SpondCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: SpondCoordinator = entry.runtime_data
    await coordinator.async_shutdown()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
