# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Build a Home Assistant custom integration for the GHL ProfiLux mini aquarium controller. The integration reads temperature and pH sensor values from the controller over WebSocket (SWMBus protocol) and exposes them as native Home Assistant sensor entities.

Config for the test device:
- address: `10.1.1.178`
- username: `admin`
- password: `Starfish`

## Repository layout

```
hacs.json         # HACS publishing metadata
README.md         # integration documentation (rendered by HACS)
LICENSE           # MIT license
custom_components/
  profilux_mini/
    manifest.json     # integration metadata, dependencies
    __init__.py       # HA entry point (setup/unload)
    config_flow.py    # UI config flow — calls fetch_readings() from sensor.py for validation
    sensor.py         # SWMBus protocol + fetch_readings() + TemperatureSensor/PhSensor entities
    const.py          # shared constants (DOMAIN, scan interval, …)
    strings.json      # UI strings
    translations/
      en.json
.github/
  workflows/
    validate.yaml     # HACS validation action
    hassfest.yaml     # Home Assistant hassfest validation action
scraper.py        # dev/debug CLI — imports sensor.py directly (not part of HA integration)
requirements.txt
```

Integration files live in `custom_components/profilux_mini/`. To deploy manually, copy that directory into `config/custom_components/` on the Home Assistant host.

## Installation

Copy `custom_components/profilux_mini/` into the Home Assistant `config/custom_components/` directory and restart HA. Then add the integration via **Settings → Devices & Services → Add Integration → ProfiLux Mini**.

## CI / GitHub Actions

Two validation workflows run on every push to `main`, on pull requests, on a daily schedule, and on manual dispatch.

| Workflow | File | What it checks |
|----------|------|----------------|
| **HACS Validation** | `.github/workflows/validate.yaml` | Integration structure meets [HACS](https://hacs.xyz/) requirements (`hacs/action@main`, category `integration`). Validates `hacs.json`, repo layout, and `manifest.json` fields. |
| **Hassfest** | `.github/workflows/hassfest.yaml` | Integration metadata is valid per Home Assistant standards (`home-assistant/actions/hassfest@master`). Checks `manifest.json`, `strings.json`, `translations/`, and required keys like `domain`, `version`, `config_flow`. |

### Common failure causes

- **manifest.json** — missing or invalid fields (`domain`, `version`, `requirements`, `codeowners`, `iot_class`). Both workflows validate this file.
- **hacs.json** — must exist at repo root with valid `name` and optional `render_readme`.
- **strings.json / translations/en.json** — must stay in sync; hassfest validates translation structure.
- **Repository structure** — integration files must live under `custom_components/<domain>/`.

### Testing edits

After any change to integration files, push the branch and verify that both GitHub Actions workflows pass. Use the GitHub CLI to check workflow status:

```bash
# Check status of the latest workflow runs on the current branch
gh run list --branch <branch-name> --limit 4
# View details of a specific run
gh run view <run-id>
```

If a workflow fails, inspect the logs with `gh run view <run-id> --log-failed` and fix the issue before proceeding.

### Notes

- There are **no unit tests or linting** configured. CI only performs structural/metadata validation.
- Both workflows require `GITHUB_TOKEN` (provided automatically by GitHub Actions).

## Entities

| Entity | Unit | Device class |
|--------|------|--------------|
| `sensor.profilux_mini_temperature` | °C | `temperature` |
| `sensor.profilux_mini_ph` | pH | *(none)* |

## Architecture

`sensor.py` contains both the SWMBus protocol / `fetch_readings()` function and the HA entity classes. A `DataUpdateCoordinator` (also in `sensor.py`) calls `fetch_readings()` every 60 seconds. Each sensor entity is a `CoordinatorEntity` subclass. `config_flow.py` validates credentials at setup by attempting one `fetch_readings()` call.

### SWMBus frame format

Enquiry (GET) frame for a single parameter code:
```
[SOH=0x01, slave_addr+80, master_addr, block_check, STX=0x02,
 ...code nibbles (nibble | 0x40)...,
 ENQ=0x05, ETX=0x03, block_check, EOT=0x04]
```

Response has the same structure, with data nibbles (nibble | 0x30) inserted between the code nibbles and ENQ.

`BlockCheck` = byte sum mod 256, minimum 32. Numbers are encoded little-endian as 4-bit nibbles OR'd with the section offset.

### Sensor parameter codes (ProfiLux mini)

| Code | Meaning |
|------|---------|
| 25 | Sensor 1 type (1=temp, 2=pH) |
| 49 | Sensor 2 type (= 25 + block size 24) |
| 10000 | Sensor 1 current value (raw) |
| 10008 | Sensor 2 current value (= 10000 + 8) |

### Scaling

- **Temperature** (`SENSORTYPE_TEMP=1`): raw ÷ 10 → °C (e.g. 246 → 24.6)
- **pH** (`SENSORTYPE_PH=2`): raw ÷ 100 → pH (e.g. 652 → 6.52)
