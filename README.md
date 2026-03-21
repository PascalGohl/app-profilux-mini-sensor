# ProfiLux Mini — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

A Home Assistant custom integration for the **GHL ProfiLux mini** aquarium controller. Reads temperature and pH sensor values from the controller over WebSocket and exposes them as native Home Assistant sensor entities.

## Features

- Automatic discovery of connected sensors (temperature and pH)
- Real-time polling every 60 seconds
- Full UI-based configuration via the Home Assistant integrations page
- Native sensor entities with proper device classes and units

## Entities

| Entity | Unit | Device Class |
|--------|------|--------------|
| `sensor.profilux_mini_temperature` | °C | `temperature` |
| `sensor.profilux_mini_ph` | pH | *(none)* |

## Requirements

- Home Assistant 2023.1 or newer
- GHL ProfiLux mini controller accessible on the local network
- Controller must have WebSocket interface enabled

## Installation

### Via HACS

1. Open HACS in Home Assistant.
2. Go to **Integrations → Custom repositories**.
3. Add `https://github.com/PascalGohl/app-profilux-mini-sensor` as an **Integration**.
4. Search for **ProfiLux Mini** and install it.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/profilux_mini/` directory into your Home Assistant `config/custom_components/` folder.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **ProfiLux Mini**.
3. Enter the following details:

| Field | Description |
|-------|-------------|
| **Host** | IP address of the ProfiLux mini (e.g. `192.168.1.100`) |
| **Username** | Controller username (default: `admin`) |
| **Password** | Controller password |

## Troubleshooting

- Ensure the ProfiLux mini is reachable on your network (try pinging its IP address).
- Verify the username and password match those configured on the controller.
- Check that no firewall is blocking WebSocket traffic (port 80) to the controller.

## License

MIT License — see [LICENSE](LICENSE) for details.
