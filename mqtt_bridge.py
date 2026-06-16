#!/usr/bin/env python3
"""
Optional MQTT bridge for Lync12.

When enabled, subscribes to command topics on an MQTT broker and publishes
zone state back, giving IoT devices bidirectional control alongside the web UI.

Environment variables:
  MQTT_ENABLED          Set to 'true' to enable (default: disabled).
  MQTT_BROKER           Broker hostname or IP (default: localhost).
  MQTT_PORT             Broker port (default: 1883).
  MQTT_USERNAME         Auth username (optional).
  MQTT_PASSWORD         Auth password (optional).
  MQTT_TOPIC_PREFIX     Base topic prefix (default: lync12).
  MQTT_CLIENT_ID        MQTT client identifier (default: lync12-bridge).
  MQTT_QOS              QoS level for subscribe/publish (default: 1).
  MQTT_STATE_INTERVAL   Seconds between periodic full state publishes (default: 60).
  MQTT_TLS              Set to 'true' to enable TLS (default: false).

Topic scheme (P = MQTT_TOPIC_PREFIX):
  Commands (subscribe):
    P/zone/<id>/power/set     payload: 0|1|on|off|true|false
    P/zone/<id>/mute/set      payload: 0|1|on|off
    P/zone/<id>/volume/set    payload: 0-100
    P/zone/<id>/input/set     payload: 1-18
    P/zone/<id>/balance/set   payload: -18 to 18
    P/zone/<id>/treble/set    payload: -10 to 10
    P/zone/<id>/bass/set      payload: -10 to 10
    P/zone/all/power/set      payload: 0|1  (broadcast to all zones)
    P/mp3/set                 payload: play|stop|repeaton|repeatoff|forward|back|reverse
    P/refresh                 payload: (any) — forces immediate full state publish

  State (publish, retained):
    P/zone/<id>/power/state
    P/zone/<id>/volume/state
    P/zone/<id>/mute/state
    P/zone/<id>/input/state
    P/zone/<id>/balance/state
    P/zone/<id>/treble/state
    P/zone/<id>/bass/state
    P/zone/<id>/state         (full zone JSON)
    P/availability            online | offline (LWT)
"""
import json
import logging
import os
import serial
import threading
import time

import app as _app
from lync12 import Lync12Command as Lync12
from paho.mqtt import client as mqtt_client
from paho.mqtt.enums import CallbackAPIVersion

logger = logging.getLogger(__name__)


def _parse_bool(value):
    return value.strip().lower() in ('1', 'on', 'true', 'yes')


class Lync12MqttBridge:
    def __init__(self, broker, port, prefix, client_id, qos, state_interval,
                 username=None, password=None, tls=False):
        self._broker = broker
        self._port = port
        self._prefix = prefix
        self._qos = qos
        self._state_interval = state_interval

        self._client = mqtt_client.Client(
            CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
        if username:
            self._client.username_pw_set(username, password)
        if tls:
            self._client.tls_set()

        self._client.will_set(
            f'{self._prefix}/availability', 'offline', qos=self._qos, retain=True
        )
        self._client.reconnect_delay_set(min_delay=1, max_delay=60)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def start(self):
        self._client.connect(self._broker, self._port)
        self._client.loop_start()
        t = threading.Thread(target=self._state_publisher, daemon=True)
        t.start()
        logger.info(
            'MQTT bridge started — broker=%s:%d prefix=%s',
            self._broker, self._port, self._prefix,
        )

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code != 0:
            logger.warning('MQTT connect failed: %s', reason_code)
            return
        logger.info('MQTT connected to %s:%d', self._broker, self._port)
        p = self._prefix
        client.publish(f'{p}/availability', 'online', qos=self._qos, retain=True)
        client.subscribe([(f'{p}/zone/+/+/set', self._qos),
                          (f'{p}/mp3/set', self._qos),
                          (f'{p}/refresh', self._qos)])
        self._publish_all_zones()

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        if reason_code != 0:
            logger.warning('MQTT disconnected unexpectedly (%s) — will reconnect', reason_code)

    def _on_message(self, client, userdata, message):
        topic = message.topic
        payload = message.payload.decode('utf-8', errors='replace').strip()
        p = self._prefix
        rel = topic[len(p):].lstrip('/')
        parts = rel.split('/')

        try:
            if parts == ['refresh']:
                self._publish_all_zones()
                return

            if parts == ['mp3', 'set']:
                action_id = _app._MP3_ACTIONS.get(payload.lower())
                if action_id is None:
                    logger.warning('MQTT invalid MP3 action: %r', payload)
                    return
                _app.execute_command(Lync12.mp3_action(action_id))
                _app.mark_dirty()
                return

            if len(parts) == 4 and parts[0] == 'zone' and parts[3] == 'set':
                zone_str, attr = parts[1], parts[2]
                if zone_str == 'all':
                    if attr != 'power':
                        logger.warning('MQTT zone/all only supports power, got: %s', attr)
                        return
                    zone_id = 0
                else:
                    try:
                        zone_id = int(zone_str)
                    except ValueError:
                        logger.warning('MQTT invalid zone id: %r', zone_str)
                        return
                self._handle_zone_command(zone_id, attr, payload)
                return

            logger.warning('MQTT unrecognised topic: %s', topic)
        except Exception:
            logger.exception('MQTT message handler error (topic=%s payload=%r)', topic, payload)

    def _handle_zone_command(self, zone_id, attr, payload):
        try:
            if attr == 'power':
                command = Lync12.set_power(zone_id, _parse_bool(payload))
            elif attr == 'mute':
                command = Lync12.set_mute(zone_id, _parse_bool(payload))
            elif attr == 'volume':
                val = int(payload)
                if not 0 <= val <= 100:
                    logger.warning('MQTT volume out of range: %s', payload)
                    return
                command = Lync12.set_volume(zone_id, val)
            elif attr == 'input':
                val = int(payload)
                if not 1 <= val <= 18:
                    logger.warning('MQTT input out of range: %s', payload)
                    return
                command = Lync12.set_input(zone_id, val)
            elif attr == 'balance':
                val = int(payload)
                if not -18 <= val <= 18:
                    logger.warning('MQTT balance out of range: %s', payload)
                    return
                command = Lync12.set_balance(zone_id, val)
            elif attr == 'treble':
                val = int(payload)
                if not -10 <= val <= 10:
                    logger.warning('MQTT treble out of range: %s', payload)
                    return
                command = Lync12.set_treble(zone_id, val)
            elif attr == 'bass':
                val = int(payload)
                if not -10 <= val <= 10:
                    logger.warning('MQTT bass out of range: %s', payload)
                    return
                command = Lync12.set_bass(zone_id, val)
            else:
                logger.warning('MQTT unknown attribute: %s', attr)
                return
        except ValueError:
            logger.warning('MQTT invalid payload for %s: %r', attr, payload)
            return

        result = _app.execute_command(command)
        _app.mark_dirty()

        if zone_id != 0:
            self._publish_zone(zone_id, result.get(zone_id, {}))
        else:
            # broadcast command — fetch fresh state since not all zones may be in result
            self._publish_all_zones()

    def _publish_zone(self, zone_id, zone_state):
        p = self._prefix
        q = self._qos
        base = f'{p}/zone/{zone_id}'
        for attr in ('power', 'volume', 'mute', 'input', 'balance', 'treble', 'bass'):
            if attr in zone_state:
                val = zone_state[attr]
                # publish booleans as on/off for readability
                if isinstance(val, bool):
                    val = 'on' if val else 'off'
                self._client.publish(f'{base}/{attr}/state', str(val), qos=q, retain=True)
        self._client.publish(f'{base}/state', json.dumps(zone_state), qos=q, retain=True)

    def _publish_all_zones(self):
        try:
            state = _app.execute_command(Lync12.get_zone_state())
            for zone_id, zone_state in state.items():
                self._publish_zone(zone_id, zone_state)
        except serial.SerialException:
            logger.warning('MQTT state publish failed — serial error')

    def _state_publisher(self):
        while True:
            time.sleep(self._state_interval)
            self._publish_all_zones()


def start_mqtt_bridge():
    """Start the MQTT bridge if MQTT_ENABLED is set. Otherwise a no-op."""
    if os.environ.get('MQTT_ENABLED', '').lower() not in ('1', 'true', 'yes'):
        return

    bridge = Lync12MqttBridge(
        broker=os.environ.get('MQTT_BROKER', 'localhost'),
        port=int(os.environ.get('MQTT_PORT', 1883)),
        prefix=os.environ.get('MQTT_TOPIC_PREFIX', 'lync12'),
        client_id=os.environ.get('MQTT_CLIENT_ID', 'lync12-bridge'),
        qos=int(os.environ.get('MQTT_QOS', 1)),
        state_interval=int(os.environ.get('MQTT_STATE_INTERVAL', 60)),
        username=os.environ.get('MQTT_USERNAME') or None,
        password=os.environ.get('MQTT_PASSWORD') or None,
        tls=os.environ.get('MQTT_TLS', '').lower() in ('1', 'true', 'yes'),
    )
    bridge.start()
