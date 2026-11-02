#!/usr/bin/env python
from flask import Flask, jsonify, abort
from lync12 import Lync12Command as Lync12
from flask_cors import CORS  # The typical way to import flask_cors
from flask import request, send_from_directory, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import disable_created_metrics
import serial
import datetime
import logging
import os
import re
import threading
import time

app = Flask(__name__)
cors = CORS(app)

_cache_lock = threading.Lock()
__json_cache = {}
__dirty_bit = False
__status_update_time = datetime.datetime(1970, 1, 1, 0, 0)
__cache_timeout = int(os.environ.get('CACHE_TIMEOUT', 300))

_MP3_ACTIONS = {
    'play': Lync12.MP3_PLAY,
    'stop': Lync12.MP3_STOP,
    'repeatoff': Lync12.MP3_REPEAT_OFF,
    'repeaton': Lync12.MP3_REPEAT_ON,
    'forward': Lync12.MP3_FF,
    'back': Lync12.MP3_FB,
    'reverse': Lync12.MP3_FB,
}

_serial_port = os.environ.get('SERIAL_PORT', '/dev/ttyUSB0')
_serial_lock = threading.Lock()
_ser = None
_poll_interval = int(os.environ.get('POLL_INTERVAL', 60))

# Prometheus metrics, served at /metrics. The command label is the command's
# kind, never its name: names carry the zone and value ("z3 set_volume 40").
# The *_created series would double the count and nothing reads them.
disable_created_metrics()
_commands = Counter('lync12_commands_total',
                    'Serial commands sent to the controller, by kind and outcome.',
                    ['command', 'outcome'])
_last_success = Gauge('lync12_last_success_timestamp_seconds',
                      'When the controller last answered a command with a reply that parsed.')
_zones_reported = Gauge('lync12_zones_reported',
                        'Zones in the last status reply (12 on a Lync12, 0 if it was empty).')
_duration = Histogram('lync12_command_duration_seconds',
                      'Time from writing a command to parsing its reply.',
                      buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8))
_serial_open = Gauge('lync12_serial_open', 'Whether the serial port is open (1) or not (0).')
_serial_open.set_function(lambda: 1 if _ser is not None and _ser.is_open else 0)
for _outcome in ('ok', 'empty_reply', 'parse_error', 'serial_error'):
    _commands.labels('state', _outcome)


def _command_kind(name):
    name = re.sub(r'^z\d+ ', '', name)
    if name.startswith('MP3'):
        return 'mp3'
    if name.startswith('input'):
        return 'input'
    return name.split()[0]


def _get_serial():
    global _ser
    if _ser is None or not _ser.is_open:
        _ser = serial.Serial(_serial_port, 38400, timeout=4, inter_byte_timeout=0.05)
    return _ser


def execute_command(command):
    global _ser
    kind = _command_kind(command.name)
    start = time.monotonic()
    try:
        with _serial_lock:
            result = command.execute(_get_serial())
    except serial.SerialException as e:
        _commands.labels(kind, 'serial_error').inc()
        logging.error('Serial error: ' + str(e))
        _ser = None
        raise
    except Exception:
        _commands.labels(kind, 'parse_error').inc()
        raise
    finally:
        _duration.observe(time.monotonic() - start)
    if command.result:
        _commands.labels(kind, 'ok').inc()
        _last_success.set_to_current_time()
    else:
        # The port is open but nothing came back within the read timeout:
        # the controller is off or the cable is out.
        _commands.labels(kind, 'empty_reply').inc()
    return result.json_data()


def mark_dirty():
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True


def _run(command, dirty=False):
    try:
        result = jsonify(execute_command(command))
        if dirty:
            mark_dirty()
        return result
    except serial.SerialException as e:
        return jsonify({'error': 'serial communication failure', 'detail': str(e)}), 503


@app.route('/')
def index():
    return send_from_directory('ui', 'index.html')


@app.route('/ui/<path:path>')
def ui_files(path):
    return send_from_directory('ui', path)


def _refresh_status():
    """Read every zone from the controller and replace the /status cache."""
    global __dirty_bit
    global __json_cache
    global __status_update_time
    new_cache = execute_command(Lync12.get_zone_state())
    with _cache_lock:
        __json_cache = new_cache
        __status_update_time = datetime.datetime.now()
        __dirty_bit = False
    _zones_reported.set(len(new_cache))


def _poll_loop():
    while True:
        time.sleep(_poll_interval)
        try:
            _refresh_status()
        except Exception as e:
            logging.warning('Status poll failed: %s', e)


def start_status_poller():
    """Read the controller every POLL_INTERVAL seconds (0 disables), so
    lync12_last_success_timestamp_seconds goes stale only when the controller
    stops answering, not when nobody is using the UI."""
    if _poll_interval <= 0:
        return
    threading.Thread(target=_poll_loop, name='status-poller', daemon=True).start()


@app.route('/metrics')
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@app.route('/status')
def status():
    with _cache_lock:
        current_time = datetime.datetime.now()
        run_time = __status_update_time + datetime.timedelta(seconds=__cache_timeout)
        needs_refresh = __dirty_bit or run_time < current_time

    if needs_refresh:
        logging.debug('refreshing status')
        try:
            _refresh_status()
        except serial.SerialException as e:
            return jsonify({'error': 'serial communication failure', 'detail': str(e)}), 503

    return jsonify(__json_cache)


# @app.route('/zone_names', methods=['GET'])
# def zone_names():
#    command = lync12.get_zone_names()
#    return _run(command)


# @app.route('/source_names', methods=['GET'])
# def input_names():
#    command = lync12.get_source_names()
#    return _run(command)


@app.route('/model', methods=['GET'])
def model():
    command = Lync12.get_model()
    return _run(command)


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)


@app.route('/zone/<int:zone_id>/power', methods=['GET'])
def zone_power_get(zone_id):
    if 'power' in request.values:
        power = request.values['power'] == '1'
        logging.debug(str(zone_id) + " setting power to " + str(power))
        command = Lync12.set_power(zone_id, power)
        return _run(command, dirty=True)
    with _cache_lock:
        zone = __json_cache.get(zone_id)
    if zone is None:
        return jsonify({'error': 'zone not found'}), 404
    return jsonify({'zone': zone_id, 'power': zone.get('power')})


@app.route('/zone/<int:zone_id>/power', methods=['PUT'])
def zone_power(zone_id):
    if request.values['power'] == '1':
        power = True
    else:
        power = False
    logging.debug(str(zone_id) + " setting power to " + str(power))

    command = Lync12.set_power(zone_id, power)
    return _run(command, dirty=True)


@app.route('/zone/<int:zone_id>/mute', methods=['PUT'])
def zone_mute(zone_id):
    if request.values['mute'] == '1':
        power = True
    else:
        power = False
    logging.debug(str(zone_id) + " setting mute to " + str(power))

    command = Lync12.set_mute(zone_id, power)
    return _run(command, dirty=True)


@app.route('/zone/all/power', methods=['PUT', 'GET'])
def zone_power_all():
    if 'power' not in request.values:
        return jsonify({'error': 'power parameter required'}), 400
    if request.values['power'] == '1':
        power = True
    else:
        power = False
    logging.debug("setting power to of all zones to " + str(power))

    command = Lync12.set_power(0, power)
    return _run(command, dirty=True)


@app.route('/zone/<int:zone_id>/volume', methods=['PUT'])
def zone_volume(zone_id):
    try:
        volume = int(request.values['volume'])
    except (KeyError, ValueError):
        return jsonify({'error': 'volume must be an integer'}), 400
    if not 0 <= volume <= 100:
        return jsonify({'error': 'volume must be between 0 and 100'}), 400
    command = Lync12.set_volume(zone_id, volume)
    return _run(command, dirty=True)


@app.route('/zone/<int:zone_id>/input', methods=['PUT'])
def zone_input(zone_id):
    try:
        input_src = int(request.values['input'])
    except (KeyError, ValueError):
        return jsonify({'error': 'input must be an integer'}), 400
    if not 1 <= input_src <= 18:
        return jsonify({'error': 'input must be between 1 and 18'}), 400
    command = Lync12.set_input(zone_id, input_src)
    return _run(command, dirty=True)


@app.route('/zone/<int:zone_id>/balance', methods=['PUT', 'GET'])
def zone_balance(zone_id):
    try:
        balance_val = int(request.values['balance'])
    except (KeyError, ValueError):
        return jsonify({'error': 'balance must be an integer'}), 400
    if not -18 <= balance_val <= 18:
        return jsonify({'error': 'balance must be between -18 and 18'}), 400
    command = Lync12.set_balance(zone_id, balance_val)
    return _run(command, dirty=True)


@app.route('/zone/<int:zone_id>/treble', methods=['PUT', 'GET'])
def zone_treble(zone_id):
    try:
        treble_val = int(request.values['treble'])
    except (KeyError, ValueError):
        return jsonify({'error': 'treble must be an integer'}), 400
    if not -10 <= treble_val <= 10:
        return jsonify({'error': 'treble must be between -10 and 10'}), 400
    command = Lync12.set_treble(zone_id, treble_val)
    return _run(command, dirty=True)


@app.route('/zone/<int:zone_id>/bass', methods=['PUT', 'GET'])
def zone_base(zone_id):
    try:
        bass_val = int(request.values['bass'])
    except (KeyError, ValueError):
        return jsonify({'error': 'bass must be an integer'}), 400
    if not -10 <= bass_val <= 10:
        return jsonify({'error': 'bass must be between -10 and 10'}), 400
    command = Lync12.set_bass(zone_id, bass_val)
    return _run(command, dirty=True)


@app.route('/mp3/<string:action>', methods=['PUT', 'GET'])
def mp3_controls(action):
    action_id = _MP3_ACTIONS.get(action)
    if action_id is None:
        logging.error('MP3 URL error: ' + action)
        abort(404)

    command = Lync12.mp3_action(action_id)
    return _run(command, dirty=True)


if __name__ == '__main__':
    log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    logging.basicConfig(level=log_level)
    app.run(port=8080, host='0.0.0.0')
