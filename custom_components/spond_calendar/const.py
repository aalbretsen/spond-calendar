"""Constants for the Spond Calendar integration."""

DOMAIN = "spond_calendar"

CONF_SPOND_EMAIL = "email"
CONF_SPOND_PASSWORD = "password"
CONF_GROUP_ID = "group_id"
CONF_GROUP_NAME = "group_name"
CONF_INCLUDE_PLANNED = "include_planned"
CONF_SHOW_UNANSWERED_INDICATOR = "show_unanswered_indicator"
CONF_UNANSWERED_PREFIX = "unanswered_prefix"
CONF_HIDE_DECLINED = "hide_declined"
CONF_UNANSWERED_REQUIRE_ALL = "unanswered_require_all"
CONF_HIDE_DECLINED_REQUIRE_ALL = "hide_declined_require_all"
CONF_STRIP_EMOJI = "strip_emoji"

DEFAULT_SCAN_INTERVAL_MINUTES = 15
DEFAULT_DAYS_BACK = 30
DEFAULT_DAYS_AHEAD = 90
DEFAULT_UNANSWERED_PREFIX = "❓"
DEFAULT_UNANSWERED_REQUIRE_ALL = False
DEFAULT_HIDE_DECLINED_REQUIRE_ALL = True
DEFAULT_STRIP_EMOJI = False
