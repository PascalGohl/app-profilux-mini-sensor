"""GHL ProfiLux Mini — Home Assistant sensor platform.

Contains the SWMBus protocol implementation, fetch_readings(), the
DataUpdateCoordinator, and the TemperatureSensor / PhSensor entities.
"""
from __future__ import annotations

import base64
import logging
from datetime import timedelta

import websocket

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL as _SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SWMBus protocol
# ---------------------------------------------------------------------------

SOH = 0x01
STX = 0x02
ENQ = 0x05
ETX = 0x03
EOT = 0x04
CODE_OFFSET_SAVE   = 0x40
CODE_OFFSET_NOSAVE = 0x60
DATA_OFFSET        = 0x30
SLAVE_ADDR  = 0 + 80
MASTER_ADDR = 145

SENSORTYPE_TEMP = 1
SENSORTYPE_PH   = 2

CODE_SENSOR1_TYPE     = 25
CODE_SENSOR2_TYPE     = 49
CODE_SENSOR1_ACTVALUE = 10000
CODE_SENSOR2_ACTVALUE = 10008

SCALE = {
    SENSORTYPE_TEMP: 10,
    SENSORTYPE_PH:   100,
}


def _block_check(data: list, length: int) -> int:
    s = sum(data[:length]) & 0xFF
    return s if s >= 32 else s + 32


def _encode_code(code: int) -> list:
    nibbles = []
    while True:
        nibbles.append((code & 0xF) | CODE_OFFSET_SAVE)
        code >>= 4
        if code == 0:
            break
    return nibbles


def _make_enquiry(code: int) -> bytes:
    header = [SOH, SLAVE_ADDR, MASTER_ADDR]
    bca = _block_check(header, 3)
    code_nibbles = _encode_code(code)
    frame = header + [bca, STX] + code_nibbles + [ENQ, ETX]
    bcc = _block_check(frame, len(frame))
    frame += [bcc, EOT]
    return bytes(frame)


def _parse_response(data: bytes):
    b = list(data)
    if len(b) < 6 or b[0] != SOH or b[4] != STX:
        return None
    if b[1] < 80 or b[2] < 80:
        return None

    d = 5
    code_offset = b[d] & 0xF0
    if code_offset not in (CODE_OFFSET_SAVE, CODE_OFFSET_NOSAVE):
        return None

    code_nibbles = []
    while d < len(b) and (b[d] & 0xF0) == code_offset:
        code_nibbles.append(b[d] & 0x0F)
        d += 1

    data_nibbles = []
    while d < len(b) and (b[d] & 0xF0) == DATA_OFFSET:
        data_nibbles.append(b[d] & 0x0F)
        d += 1

    code = sum(n << (4 * i) for i, n in enumerate(code_nibbles))
    raw  = sum(n << (4 * i) for i, n in enumerate(data_nibbles))
    if raw >= 0x8000:
        raw -= 0x10000

    return code, raw


def _query(ws, codes: list) -> dict:
    for code in codes:
        ws.send_binary(_make_enquiry(code))
    results = {}
    for _ in codes:
        resp = ws.recv()
        parsed = _parse_response(resp)
        if parsed:
            results[parsed[0]] = parsed[1]
    return results


def fetch_readings(host: str, user: str, password: str) -> dict:
    """Connect to ProfiLux and return {'temperature': float|None, 'ph': float|None}."""
    url = f"ws://{host}/ws"
    auth_header = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
    ws = websocket.create_connection(url, header={"Authorization": auth_header}, timeout=10)

    try:
        type_results  = _query(ws, [CODE_SENSOR1_TYPE, CODE_SENSOR2_TYPE])
        value_results = _query(ws, [CODE_SENSOR1_ACTVALUE, CODE_SENSOR2_ACTVALUE])
    finally:
        ws.close()

    sensors = [
        (type_results.get(CODE_SENSOR1_TYPE), value_results.get(CODE_SENSOR1_ACTVALUE)),
        (type_results.get(CODE_SENSOR2_TYPE), value_results.get(CODE_SENSOR2_ACTVALUE)),
    ]

    temperature = ph = None
    for stype, raw in sensors:
        if raw is None or stype not in SCALE:
            continue
        value = round(raw / SCALE[stype], 1 if stype == SENSORTYPE_TEMP else 2)
        if stype == SENSORTYPE_TEMP:
            temperature = value
        elif stype == SENSORTYPE_PH:
            ph = value

    return {"temperature": temperature, "ph": ph}


# ---------------------------------------------------------------------------
# Home Assistant integration
# ---------------------------------------------------------------------------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    host     = entry.data[CONF_HOST]
    user     = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    coordinator = ProfiLuxCoordinator(hass, host, user, password)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([
        TemperatureSensor(coordinator, entry),
        PhSensor(coordinator, entry),
    ])


class ProfiLuxCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, host: str, user: str, password: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=_SCAN_INTERVAL_SECONDS),
        )
        self._host     = host
        self._user     = user
        self._password = password

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(
                fetch_readings, self._host, self._user, self._password
            )
        except Exception as exc:
            raise UpdateFailed(f"ProfiLux communication error: {exc}") from exc


class _ProfiLuxSensorBase(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ProfiLuxCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)


class TemperatureSensor(_ProfiLuxSensorBase):
    _attr_name = "ProfiLux Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "temperature")


class PhSensor(_ProfiLuxSensorBase):
    _attr_name = "ProfiLux pH"
    _attr_native_unit_of_measurement = "pH"
    _attr_icon = "mdi:ph"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "ph")
