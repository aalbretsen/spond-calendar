
# Spond Calendar for Home Assistant
[![Spond Calendar Logo](https://github.com/aalbretsen/spond-calendar/blob/main/custom_components/spond_calendar/brand/logo.png)](https://github.com/aalbretsen/spond-calendar)

---

[![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz)
[![Release](https://img.shields.io/github/v/release/aalbretsen/spond-calendar)](https://github.com/aalbretsen/spond-calendar/releases)
[![License](https://img.shields.io/github/license/aalbretsen/spond-calendar)](https://github.com/aalbretsen/spond-calendar/blob/main/LICENSE)

A HACS-compatible custom integration that exposes your
[Spond](https://spond.com/) group events as a native calendar in Home Assistant.  
Built on top of the excellent [Olen/Spond](https://github.com/Olen/Spond) unofficial Python library.

## Features

* **UI-based setup** — enter your Spond credentials, pick a group from a dropdown, done.
* **Native calendar entity** — shows up in the Calendar dashboard, calendar cards, and works with calendar automations/triggers.
* **Polling** — refreshes events every 15 minutes.
* **Event window** — fetches 30 days of history and 90 days ahead.
* **Multiple groups** — add the integration once per group; each gets its own calendar entity.
* **Event details** — summary, start/end times, description, and location are all mapped.
* **Unanswered invite indicator** — open invites you haven't responded to are prefixed with a configurable marker (default: `❓ `) so they stand out in your calendar.
* **Hide declined events** — optionally suppress events you've already declined.
* **Strip emoji** — optionally remove emoji characters from event titles and/or event descriptions for cleaner calendar text.
* **Meet-up time as description** — for events with a meet-up time (e.g. matches), optionally replace the event description with a short note (localized to Norwegian or English based on your Home Assistant language) like `Oppmøte 30 minutter før, kl 16:30` / `Meet 30 minutes before, at 16:30`.

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** → three-dot menu → **Custom repositories**.
3. Add the repository URL and select category **Integration**.
4. Search for **Spond Calendar** and install.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/spond_calendar` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Spond Calendar**.
3. Enter your Spond email and password.
4. Select the group you want to expose as a calendar.
5. Configure options (unanswered indicator, hide declined events).
6. Done — the calendar entity appears as `calendar.spond_<group_name>`.

To add more groups, repeat the process.

## Configuration options

| Option | Description |
| --- | --- |
| Email | Your Spond login email |
| Password | Your Spond password |
| Group | The Spond group to expose |
| Include planned events | Show events not yet open for RSVP |
| Mark unanswered invites | Prefix unanswered event titles with an indicator |
| Prefix for unanswered events | Text prepended to event title when invite is open |
| Hide declined events | Suppress events you have declined |
| Only hide when all represented members declined | When you represent multiple members, require every one to have declined before hiding |
| Only mark unanswered when all represented members are unanswered | When you represent multiple members, require every one to be unanswered before marking |
| Remove emoji from event title | Strip emoji characters from the event title |
| Remove emoji from event description | Strip emoji characters from the event description |
| Replace description with meet-up time | When a meet-up time is set on the event, show a short note about when to meet instead of the Spond description (Norwegian or English, based on your Home Assistant language). Events without a valid meet-up time will get no description. |

## Architecture

```
Spond Cloud API
      │
      │  (HTTPS / JSON, polled every 15 min)
      ▼
┌─────────────────────┐
│   SpondCoordinator  │  DataUpdateCoordinator — manages session, fetches events
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────┐
│  SpondCalendarEntity    │  CalendarEntity — maps Spond events → CalendarEvent
└──────────┬──────────────┘
           │  • Checks RSVP status (accepted / declined / unanswered)
           │  • Applies unanswered-invite prefix to event title
           │  • Optionally hides declined events
           ▼
   HA Calendar dashboard, automations, triggers
```

## Dependencies

This integration depends on the [spond](https://pypi.org/project/spond/) library (≥ 1.2.0), which is installed automatically by Home Assistant.

## Home Assistant version requirement

This integration requires **Home Assistant 2026.3.0 or newer** in order to display the integration icon correctly in the Settings → Integrations UI. Older HA versions will still work, but will show a placeholder icon.

## Disclaimer

This integration uses **unofficial, reverse-engineered APIs**. Spond does not offer a public API. Use at your own risk — the API may change without notice.

## Credits

* **[Olen/Spond](https://github.com/Olen/Spond)** by [Olen](https://github.com/Olen) — the unofficial Python library for the Spond API that this integration depends on for all communication with Spond's servers. Without this library, this integration would not exist.
* **[Claude](https://claude.ai/) by [Anthropic](https://www.anthropic.com/)** — this integration was written with the assistance of Claude, Anthropic's AI assistant.

## License

MIT
