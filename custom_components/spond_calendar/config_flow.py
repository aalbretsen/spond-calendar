"""Config flow for Spond Calendar integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_GROUP_ID,
    CONF_GROUP_NAME,
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
    DEFAULT_HIDE_DECLINED,
    DEFAULT_HIDE_DECLINED_REQUIRE_ALL,
    DEFAULT_INCLUDE_PLANNED,
    DEFAULT_SHOW_UNANSWERED_INDICATOR,
    DEFAULT_STRIP_DESCRIPTION_EMOJI,
    DEFAULT_STRIP_TITLE_EMOJI,
    DEFAULT_UNANSWERED_PREFIX,
    DEFAULT_UNANSWERED_REQUIRE_ALL,
    DEFAULT_USE_MEETUP_TIME_AS_DESCRIPTION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SPOND_EMAIL): str,
        vol.Required(CONF_SPOND_PASSWORD): str,
    }
)

_OPTION_DEFAULTS: dict[str, Any] = {
    CONF_INCLUDE_PLANNED: DEFAULT_INCLUDE_PLANNED,
    CONF_SHOW_UNANSWERED_INDICATOR: DEFAULT_SHOW_UNANSWERED_INDICATOR,
    CONF_UNANSWERED_PREFIX: DEFAULT_UNANSWERED_PREFIX,
    CONF_UNANSWERED_REQUIRE_ALL: DEFAULT_UNANSWERED_REQUIRE_ALL,
    CONF_HIDE_DECLINED: DEFAULT_HIDE_DECLINED,
    CONF_HIDE_DECLINED_REQUIRE_ALL: DEFAULT_HIDE_DECLINED_REQUIRE_ALL,
    CONF_STRIP_TITLE_EMOJI: DEFAULT_STRIP_TITLE_EMOJI,
    CONF_STRIP_DESCRIPTION_EMOJI: DEFAULT_STRIP_DESCRIPTION_EMOJI,
    CONF_USE_MEETUP_TIME_AS_DESCRIPTION: DEFAULT_USE_MEETUP_TIME_AS_DESCRIPTION,
}

_OPTION_TYPES: dict[str, type] = {
    CONF_INCLUDE_PLANNED: bool,
    CONF_SHOW_UNANSWERED_INDICATOR: bool,
    CONF_UNANSWERED_PREFIX: str,
    CONF_UNANSWERED_REQUIRE_ALL: bool,
    CONF_HIDE_DECLINED: bool,
    CONF_HIDE_DECLINED_REQUIRE_ALL: bool,
    CONF_STRIP_TITLE_EMOJI: bool,
    CONF_STRIP_DESCRIPTION_EMOJI: bool,
    CONF_USE_MEETUP_TIME_AS_DESCRIPTION: bool,
}


def _options_schema_fields(current: dict[str, Any] | None = None) -> dict[vol.Marker, type]:
    current = current or {}
    return {
        vol.Optional(key, default=current.get(key, default)): _OPTION_TYPES[key]
        for key, default in _OPTION_DEFAULTS.items()
    }


class SpondCalendarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._groups: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_SPOND_EMAIL]
            self._password = user_input[CONF_SPOND_PASSWORD]
            try:
                self._groups = await self._fetch_groups(self._email, self._password)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Failed to connect to Spond")
                errors["base"] = "cannot_connect"
            else:
                if not self._groups:
                    errors["base"] = "no_groups"
                else:
                    return await self.async_step_select_group()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_select_group(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            group_id = user_input[CONF_GROUP_ID]
            group_name = next(
                (g["name"] for g in self._groups if g["id"] == group_id),
                group_id,
            )
            await self.async_set_unique_id(group_id)
            self._abort_if_unique_id_configured()

            options = {k: v for k, v in user_input.items() if k != CONF_GROUP_ID}

            return self.async_create_entry(
                title=f"Spond – {group_name}",
                data={
                    CONF_SPOND_EMAIL: self._email,
                    CONF_SPOND_PASSWORD: self._password,
                    CONF_GROUP_ID: group_id,
                    CONF_GROUP_NAME: group_name,
                },
                options=options,
            )

        group_options = {g["id"]: g["name"] for g in self._groups}

        return self.async_show_form(
            step_id="select_group",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_GROUP_ID): vol.In(group_options),
                    **_options_schema_fields(),
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SpondCalendarOptionsFlow:
        return SpondCalendarOptionsFlow(config_entry)

    @staticmethod
    async def _fetch_groups(email: str, password: str) -> list[dict[str, Any]]:
        from spond import spond as spond_module  # noqa: PLC0415
        client = spond_module.Spond(username=email, password=password)
        try:
            groups = await client.get_groups()
            return [{"id": g["id"], "name": g["name"]} for g in groups]
        finally:
            await client.clientsession.close()


class SpondCalendarOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                _options_schema_fields(self._config_entry.options)
            ),
        )
