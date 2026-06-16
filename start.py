#!/usr/bin/env python3
"""
Docker / dev startup script.

Environment variables:
  EMULATE=true              Use the software emulator instead of real hardware.
  EMULATE_ZONES=12          Number of zones for the emulator (6 or 12).
  SERIAL_PORT=/dev/...      Serial device path (ignored when EMULATE=true).
  LOG_LEVEL=INFO            Logging level.
  PORT=8080                 HTTP port to listen on.

  MQTT_ENABLED=true         Enable the MQTT bridge (disabled by default).
  MQTT_BROKER=localhost     MQTT broker hostname or IP.
  MQTT_PORT=1883            MQTT broker port.
  MQTT_USERNAME=            Auth username (optional).
  MQTT_PASSWORD=            Auth password (optional).
  MQTT_TOPIC_PREFIX=lync12  Base topic prefix for all MQTT topics.
  MQTT_CLIENT_ID=lync12-bridge  MQTT client identifier.
  MQTT_QOS=1                QoS level for subscribe/publish.
  MQTT_STATE_INTERVAL=60    Seconds between periodic full state publishes.
  MQTT_TLS=false            Set to 'true' to enable TLS (use with port 8883).
"""
import logging
import os

log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)

if os.environ.get('EMULATE', '').lower() in ('1', 'true', 'yes'):
    from emulator.emulator import Lync12Emulator
    zones = int(os.environ.get('EMULATE_ZONES', '12'))
    emu = Lync12Emulator(num_zones=zones)
    slave = emu.start()
    os.environ['SERIAL_PORT'] = slave
    logging.info('Emulator started — %d zones, SERIAL_PORT=%s', zones, slave)

from app import app
from mqtt_bridge import start_mqtt_bridge
start_mqtt_bridge()

port = int(os.environ.get('PORT', 8080))
logging.info('Starting Lync12 web server on port %d', port)
app.run(host='0.0.0.0', port=port)
