<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://github.com/Donkie/Spoolman/assets/2332094/4e6e80ac-c7be-4ad2-9a33-dedc1b5ba30e">
  <source media="(prefers-color-scheme: light)" srcset="https://github.com/Donkie/Spoolman/assets/2332094/3c120b3a-1422-42f6-a16b-8d5a07c33000">
  <img alt="Icon of a filament spool" src="https://github.com/Donkie/Spoolman/assets/2332094/3c120b3a-1422-42f6-a16b-8d5a07c33000">
</picture>

<br/>

_Keep track of your inventory of 3D-printer filament spools._

Spoolman is a self-hosted web service designed to help you efficiently manage your 3D printer filament spools and monitor their usage. It acts as a centralized database that seamlessly integrates with popular 3D printing software like [OctoPrint](https://octoprint.org/) and [Klipper](https://www.klipper3d.org/)/[Moonraker](https://moonraker.readthedocs.io/en/latest/). When connected, it automatically updates spool weights as printing progresses, giving you real-time insights into filament usage.

[![Static Badge](https://img.shields.io/badge/Spoolman%20Wiki-blue?link=https%3A%2F%2Fgithub.com%2FDonkie%2FSpoolman%2Fwiki)](https://github.com/Donkie/Spoolman/wiki)
[![GitHub Release](https://img.shields.io/github/v/release/Donkie/Spoolman)](https://github.com/Donkie/Spoolman/releases)

### Features
* **Filament Management**: Keep comprehensive records of filament types, manufacturers, and individual spools.
* **API Integration**: The [REST API](https://donkie.github.io/Spoolman/) allows easy integration with other software, facilitating automated workflows and data exchange.
* **Real-Time Updates**: Stay informed with live spool updates through Websockets, providing immediate feedback during printing operations.
* **Central Filament Database**: A community-supported database of manufacturers and filaments simplify adding new spools to your inventory. Contribute by heading to [SpoolmanDB](https://github.com/Donkie/SpoolmanDB).
* **Web-Based Client**: Spoolman includes a built-in web client that lets you manage data effortlessly:
  * View, create, edit, and delete filament data.
  * Add custom fields to tailor information to your specific needs.
  * Print labels with QR codes for easy spool identification and tracking.
  * Contribute to its translation into 18 languages via [Weblate](https://hosted.weblate.org/projects/spoolman/).
* **Database Support**: SQLite, PostgreSQL, MySQL, and CockroachDB.
* **Multi-Printer Management**: Handles spool updates from several printers simultaneously.
* **Advanced Monitoring**: Integrate with [Prometheus](https://prometheus.io/) for detailed historical analysis of filament usage, helping you track and optimize your printing processes. See the [Wiki](https://github.com/Donkie/Spoolman/wiki/Filament-Usage-History) for instructions on how to set it up.

**Spoolman integrates with:**
  * [Moonraker](https://moonraker.readthedocs.io/en/latest/configuration/#spoolman) and most front-ends (Fluidd, KlipperScreen, Mainsail, ...)
  * [OctoPrint](https://github.com/mdziekon/octoprint-spoolman)
  * [OctoEverywhere](https://octoeverywhere.com/spoolman?source=github_spoolman)
  * [Home Assistant](https://github.com/Disane87/spoolman-homeassistant)

**Web client preview:**
![image](https://github.com/Donkie/Spoolman/assets/2332094/33928d5e-440f-4445-aca9-456c4370ad0d)

## Installation
Please see the [Installation page on the Wiki](https://github.com/Donkie/Spoolman/wiki/Installation) for details how to install Spoolman.

## Authentication

If you want to expose Spoolman through a reverse proxy such as nginx, you can enable the built-in authentication layer for browser sessions and API tokens.

Set these environment variables on the server:

```env
SPOOLMAN_AUTH_ENABLED=TRUE
SPOOLMAN_AUTH_ADMIN_USERNAME=admin
SPOOLMAN_AUTH_ADMIN_PASSWORD=change-me
SPOOLMAN_AUTH_SESSION_TTL_HOURS=168
SPOOLMAN_AUTH_COOKIE_SECURE=FALSE
```

Notes:

* `SPOOLMAN_AUTH_ADMIN_PASSWORD_FILE` can be used instead of `SPOOLMAN_AUTH_ADMIN_PASSWORD` if you prefer mounting a secret file.
* `SPOOLMAN_AUTH_COOKIE_SECURE` should be `FALSE` while testing over plain HTTP. Set it to `TRUE` when the browser reaches Spoolman over HTTPS through a reverse proxy.
* The bootstrap admin account is created automatically on first start if it does not already exist.
* After signing in, additional API tokens can be created in `Settings > Access` for scripts and integrations that should use `Authorization: Bearer ...`.

Browser access uses an HTTP-only session cookie. API clients can continue using the REST API, but should authenticate with a Bearer token once authentication is enabled.

### Hardware pairing

Hardware devices such as SpoolmanScale can be paired without typing a long API token manually:

1. Sign in to Spoolman and open `Settings > Access`.
2. Generate a hardware pairing code. The default device name is `SpoolmanScale` and the default expiry is 15 minutes.
3. On SpoolmanScale, open `Connection > Hardware Auth > Hardware Code` and enter the six-digit code.
4. Tap `Register + connect`. The device exchanges the code once, stores the returned Bearer token, and uses it for future Spoolman requests.
