# Lync12

A Flask REST API and mobile web UI for controlling a Lync12 whole-home audio system over a serial connection. Tested on Lync12 Version 2 hardware.

## Features

- REST API for full zone control — power, volume, input, mute, balance, treble, bass
- Dark-themed mobile web UI with responsive layouts for phone, tablet, and desktop
- PWA support — installable to home screen on iOS and Android
- MP3 player controls
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

| Variable        | Default        | Description                        |
|-----------------|----------------|------------------------------------|
| `SERIAL_PORT`   | `/dev/ttyUSB0` | Serial device path                 |
| `EMULATE`       | —              | Set to `true` to use the emulator  |
| `EMULATE_ZONES` | `12`           | Number of zones for emulator (6 or 12) |
| `PORT`          | `8080`         | HTTP port                          |
| `CACHE_TIMEOUT` | `4`            | Zone status cache TTL in seconds   |
| `LOG_LEVEL`     | `INFO`         | Logging level                      |

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
