# Lync12

A Flask REST API and mobile web UI for controlling a Lync12 whole-home audio system over a serial connection. Tested on Lync12 Version 2 hardware.

## Features

- REST API for full zone control — power, volume, input, mute, balance, treble, bass
- Dark-themed mobile web UI with responsive layouts for phone, tablet, and desktop
- PWA support — installable to home screen on iOS and Android
- MP3 player controls
- MQTT bridge for IoT and home-automation integration (optional, see below)
- Software emulator for development without hardware

## Quick Start

**Emulator mode (no hardware required):**
```bash
EMULATE=true python3 start.py
```

**Real hardware:**
```bash
SERIAL_PORT=/dev/ttyUSB0 python3 start.py
```

Then open `http://localhost:8080` in a browser.

## Docker

```bash
# Emulator
docker compose --profile emulator up

# Real hardware (edit device path in docker-compose.yml if needed)
docker compose --profile hardware up
```

## Environment Variables

| Variable               | Default        | Description                                  |
|------------------------|----------------|----------------------------------------------|
| `SERIAL_PORT`          | `/dev/ttyUSB0` | Serial device path                           |
| `EMULATE`              | —              | Set to `true` to use the emulator            |
| `EMULATE_ZONES`        | `12`           | Number of zones for emulator (6 or 12)       |
| `PORT`                 | `8080`         | HTTP port                                    |
| `CACHE_TIMEOUT`        | `300`          | Zone status cache TTL in seconds             |
| `LOG_LEVEL`            | `INFO`         | Logging level                                |
| `MQTT_ENABLED`         | —              | Set to `true` to enable the MQTT bridge      |
| `MQTT_BROKER`          | `localhost`    | MQTT broker hostname or IP                   |
| `MQTT_PORT`            | `1883`         | MQTT broker port                             |
| `MQTT_USERNAME`        | —              | Auth username (optional)                     |
| `MQTT_PASSWORD`        | —              | Auth password (optional)                     |
| `MQTT_TOPIC_PREFIX`    | `lync12`       | Base topic prefix for all MQTT topics        |
| `MQTT_CLIENT_ID`       | `lync12-bridge`| MQTT client identifier                       |
| `MQTT_QOS`             | `1`            | QoS level for subscribe/publish              |
| `MQTT_STATE_INTERVAL`  | `60`           | Seconds between periodic full state publishes|
| `MQTT_TLS`             | —              | Set to `true` to enable TLS (port 8883)      |

## REST API

| Method | Endpoint                  | Body / Params             | Description              |
|--------|---------------------------|---------------------------|--------------------------|
| GET    | `/status`                 | —                         | All zone states          |
| PUT    | `/zone/<id>/power`        | `power=1\|0`              | Set zone power           |
| GET    | `/zone/<id>/power`        | `?power=1\|0` (optional)  | Get or set zone power    |
| PUT    | `/zone/all/power`         | `power=1\|0`              | Set all zones power      |
| PUT    | `/zone/<id>/volume`       | `volume=0–100`            | Set volume               |
| PUT    | `/zone/<id>/input`        | `input=1–18`              | Set input source         |
| PUT    | `/zone/<id>/mute`         | `mute=1\|0`               | Set mute                 |
| PUT    | `/zone/<id>/balance`      | `balance=-18–18`          | Set balance              |
| PUT    | `/zone/<id>/treble`       | `treble=-10–10`           | Set treble               |
| PUT    | `/zone/<id>/bass`         | `bass=-10–10`             | Set bass                 |
| PUT    | `/mp3/<action>`           | —                         | MP3 control (see below)  |

MP3 actions: `play`, `stop`, `back`, `forward`, `repeaton`, `repeatoff`

## MQTT Control

The MQTT bridge lets any MQTT-capable IoT device or automation platform control Lync12 zones. It is **disabled by default** — the web interface is unchanged when `MQTT_ENABLED` is not set.

### Enable

```bash
# Local dev with emulator
EMULATE=true MQTT_ENABLED=true MQTT_BROKER=192.168.1.10 python3 start.py

# Hardware via Docker
MQTT_ENABLED=true MQTT_BROKER=192.168.1.10 ./start-hardware.sh
```

### Topic scheme

Replace `lync12` with your `MQTT_TOPIC_PREFIX`.

**Command topics (publish to these to control):**

| Topic | Payload | Description |
|-------|---------|-------------|
| `lync12/zone/<id>/power/set` | `on\|off\|1\|0` | Zone power |
| `lync12/zone/<id>/mute/set` | `on\|off\|1\|0` | Zone mute |
| `lync12/zone/<id>/volume/set` | `0–100` | Zone volume |
| `lync12/zone/<id>/input/set` | `1–18` | Input source |
| `lync12/zone/<id>/balance/set` | `-18–18` | Balance |
| `lync12/zone/<id>/treble/set` | `-10–10` | Treble EQ |
| `lync12/zone/<id>/bass/set` | `-10–10` | Bass EQ |
| `lync12/zone/all/power/set` | `on\|off\|1\|0` | All zones power |
| `lync12/mp3/set` | `play\|stop\|repeaton\|repeatoff\|forward\|back` | MP3 player |
| `lync12/refresh` | (any) | Force immediate state publish |

**State topics (subscribe to these to read state, all retained):**

| Topic | Example payload |
|-------|-----------------|
| `lync12/zone/<id>/power/state` | `on` |
| `lync12/zone/<id>/volume/state` | `45` |
| `lync12/zone/<id>/mute/state` | `off` |
| `lync12/zone/<id>/input/state` | `3` |
| `lync12/zone/<id>/balance/state` | `0` |
| `lync12/zone/<id>/treble/state` | `2` |
| `lync12/zone/<id>/bass/state` | `-1` |
| `lync12/zone/<id>/state` | `{"zone":1,"power":true,...}` (full JSON) |
| `lync12/availability` | `online` \| `offline` (LWT) |

### Example (mosquitto CLI)

```bash
# Watch all Lync12 topics
mosquitto_sub -h 192.168.1.10 -t 'lync12/#' -v

# Turn on zone 1
mosquitto_pub -h 192.168.1.10 -t lync12/zone/1/power/set -m on

# Set zone 2 volume to 40
mosquitto_pub -h 192.168.1.10 -t lync12/zone/2/volume/set -m 40

# Turn off all zones
mosquitto_pub -h 192.168.1.10 -t lync12/zone/all/power/set -m off
```

### Authentication / TLS

```bash
MQTT_ENABLED=true MQTT_BROKER=broker.example.com \
  MQTT_USERNAME=myuser MQTT_PASSWORD=mypass \
  MQTT_TLS=true MQTT_PORT=8883 python3 start.py
```

## Project Structure

```
Lync12/
├── app.py              # Flask REST API
├── lync12.py           # Serial protocol driver
├── start.py            # Startup script (handles emulator + Flask)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── emulator/
│   └── emulator.py     # PTY-based hardware emulator
├── ui/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── manifest.json   # PWA manifest
│   ├── sw.js           # Service worker
│   └── icon*.png/svg   # App icons
└── docs/
    ├── PROTOCOL_SPEC.md
    └── Lync_V2_Serial_Protocol.pdf
```
