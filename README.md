<p align="center">
  <img src="custom_components/spond_calendar/images/logo.png" alt="Spond Calendar" />
</p>

<h3 align="center">Spond Calendar for Home Assistant</h3>

<p align="center">
  A HACS-compatible custom integration that exposes your
  <a href="https://spond.com/">Spond</a> group events as a native calendar in Home Assistant.<br/>
  Built on top of the excellent <a href="https://github.com/Olen/Spond">Olen/Spond</a> unofficial Python library.
</p>

---

[![HACS][hacs-badge]][hacs-url]
[![Release][release-badge]][release-url]
[![License][license-badge]](LICENSE)

## Features

- **UI-based setup** — enter your Spond credentials, pick a group from a dropdown, done.
- **Native calendar entity** — shows up in the Calendar dashboard, calendar cards, and works with calendar automations/triggers.
- **Polling** — refreshes events every 15 minutes.
- **Event window** — fetches 30 days of history and 90 days ahead.
- **Multiple groups** — add the integration once per group; each gets its own calendar entity.
- **Event details** — summary, start/end times, description, and location are all mapped.

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
5. Done — the calendar entity appears as `calendar.spond_<group_name>`.

To add more groups, repeat the process.

## Using in automations

```yaml
automation:
  - alias: "Notify before Spond event"
    trigger:
      - platform: calendar
        event: start
        entity_id: calendar.my_spond_group
        offset: "-0:30:0"
    action:
      - service: notify.mobile_app_my_phone
        data:
          title: "Upcoming: {{ trigger.calendar_event.summary }}"
          message: "Starts at {{ trigger.calendar_event.start }} — {{ trigger.calendar_event.location }}"
```

## Configuration options

| Option | Description |
|--------|-------------|
| Email | Your Spond login email |
| Password | Your Spond password |
| Group | The Spond group to expose (selected from a dropdown) |

## Architecture

```
Spond Cloud API
      │
      │  (HTTPS / JSON, polled every 15 min)
      │  (30 days back ← today → 90 days ahead)
      ▼
┌─────────────────────┐
│   SpondCoordinator   │  DataUpdateCoordinator — manages session, fetches events
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────┐
│  SpondCalendarEntity     │  CalendarEntity — maps Spond events → CalendarEvent
└──────────┬──────────────┘
           │
           ▼
   HA Calendar dashboard, automations, triggers
```

## Dependencies

This integration depends on the [spond](https://pypi.org/project/spond/) library (≥ 1.2.0), which is installed automatically by Home Assistant.

## Disclaimer

This integration uses **unofficial, reverse-engineered APIs**. Spond does not offer a public API. Use at your own risk — the API may change without notice.

## Credits

- **[Olen/Spond](https://github.com/Olen/Spond)** by [Olen](https://github.com/Olen) — the unofficial Python library for the Spond API that this integration depends on for all communication with Spond's servers. Without this library, this integration would not exist.
- **[Claude](https://claude.ai/) by [Anthropic](https://www.anthropic.com/)** — this integration was written with the assistance of Claude (Opus), Anthropic's AI assistant, in an interactive session covering architecture research, API investigation, and code generation.

## License

MIT

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-blue.svg
[hacs-url]: https://hacs.xyz
[release-badge]: https://img.shields.io/github/v/release/aalbretsen/spond-calendar
[release-url]: https://github.com/aalbretsen/spond-calendar/releases
[license-badge]: https://img.shields.io/github/license/aalbretsen/spond-calendar
