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
    CONF_STRIP_EMOJI,
    CONF_UNANSWERED_PREFIX,
    CONF_UNANSWERED_REQUIRE_ALL,
    DEFAULT_HIDE_DECLINED_REQUIRE_ALL,
    DEFAULT_STRIP_EMOJI,
    DEFAULT_UNANSWERED_PREFIX,
    DEFAULT_UNANSWERED_REQUIRE_ALL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SPOND_EMAIL): str,
        vol.Required(CONF_SPOND_PASSWORD): str,
    }
)


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

            return self.async_create_entry(
                title=f"Spond – {group_name}",
                data={
                    CONF_SPOND_EMAIL: self._email,
                    CONF_SPOND_PASSWORD: self._password,
                    CONF_GROUP_ID: group_id,
                    CONF_GROUP_NAME: group_name,
                },
                options={
                    CONF_INCLUDE_PLANNED: user_input.get(CONF_INCLUDE_PLANNED, False),
                    CONF_SHOW_UNANSWERED_INDICATOR: user_input.get(CONF_SHOW_UNANSWERED_INDICATOR, True),
                    CONF_UNANSWERED_PREFIX: user_input.get(CONF_UNANSWERED_PREFIX, DEFAULT_UNANSWERED_PREFIX),
                    CONF_UNANSWERED_REQUIRE_ALL: user_input.get(
                        CONF_UNANSWERED_REQUIRE_ALL, DEFAULT_UNANSWERED_REQUIRE_ALL
                    ),
                    CONF_HIDE_DECLINED: user_input.get(CONF_HIDE_DECLINED, False),
                    CONF_HIDE_DECLINED_REQUIRE_ALL: user_input.get(
                        CONF_HIDE_DECLINED_REQUIRE_ALL, DEFAULT_HIDE_DECLINED_REQUIRE_ALL
                    ),
                    CONF_STRIP_EMOJI: user_input.get(CONF_STRIP_EMOJI, DEFAULT_STRIP_EMOJI),
                },
            )

        group_options = {g["id"]: g["name"] for g in self._groups}

        return self.async_show_form(
            step_id="select_group",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_GROUP_ID): vol.In(group_options),
                    vol.Optional(CONF_INCLUDE_PLANNED, default=False): bool,
                    vol.Optional(CONF_SHOW_UNANSWERED_INDICATOR, default=True): bool,
                    vol.Optional(CONF_UNANSWERED_PREFIX, default=DEFAULT_UNANSWERED_PREFIX): str,
                    vol.Optional(
                        CONF_UNANSWERED_REQUIRE_ALL,
                        default=DEFAULT_UNANSWERED_REQUIRE_ALL,
                    ): bool,
                    vol.Optional(CONF_HIDE_DECLINED, default=False): bool,
                    vol.Optional(
                        CONF_HIDE_DECLINED_REQUIRE_ALL,
                        default=DEFAULT_HIDE_DECLINED_REQUIRE_ALL,
                    ): bool,
                    vol.Optional(CONF_STRIP_EMOJI, default=DEFAULT_STRIP_EMOJI): bool,
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

        opts = self._config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_INCLUDE_PLANNED, default=opts.get(CONF_INCLUDE_PLANNED, False)): bool,
                    vol.Optional(CONF_SHOW_UNANSWERED_INDICATOR, default=opts.get(CONF_SHOW_UNANSWERED_INDICATOR, True)): bool,
                    vol.Optional(CONF_UNANSWERED_PREFIX, default=opts.get(CONF_UNANSWERED_PREFIX, DEFAULT_UNANSWERED_PREFIX)): str,
                    vol.Optional(
                        CONF_UNANSWERED_REQUIRE_ALL,
                        default=opts.get(
                            CONF_UNANSWERED_REQUIRE_ALL, DEFAULT_UNANSWERED_REQUIRE_ALL
                        ),
                    ): bool,
                    vol.Optional(CONF_HIDE_DECLINED, default=opts.get(CONF_HIDE_DECLINED, False)): bool,
                    vol.Optional(
                        CONF_HIDE_DECLINED_REQUIRE_ALL,
                        default=opts.get(
                            CONF_HIDE_DECLINED_REQUIRE_ALL,
                            DEFAULT_HIDE_DECLINED_REQUIRE_ALL,
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_STRIP_EMOJI,
                        default=opts.get(CONF_STRIP_EMOJI, DEFAULT_STRIP_EMOJI),
                    ): bool,
                }
            ),
        )
