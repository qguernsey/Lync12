#!/usr/bin/env python
from flask import Flask, jsonify, abort
from lync12 import Lync12Command as Lync12
from flask_cors import CORS  # The typical way to import flask_cors
from flask import request, send_from_directory
import serial
import datetime
import logging
import os
import threading

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


def execute_command(command):
    port = "/dev/ttyUSB0"
    # port = "/dev/tty.UC-232AC"
    ser = serial.Serial(port, 38400, timeout=4)
    result = command.execute(ser)
    ser.close()
    return result.json_data()


@app.route('/')
def index():
    return "Hello, World!"


@app.route('/status')
def status():
    global __dirty_bit
    global __json_cache
    global __status_update_time
    with _cache_lock:
        current_time = datetime.datetime.now()
        run_time = __status_update_time + datetime.timedelta(seconds=__cache_timeout)
        if __dirty_bit or run_time < current_time:
            logging.debug('refreshing status')
            command = Lync12.get_zone_state()
            __json_cache = execute_command(command)
            __status_update_time = datetime.datetime.now()
            __dirty_bit = False
    return jsonify(__json_cache)


# @app.route('/zone_names', methods=['GET'])
# def zone_names():
#    command = lync12.get_zone_names()
#    return jsonify(execute_command(command))


# @app.route('/source_names', methods=['GET'])
# def input_names():
#    command = lync12.get_source_names()
#    return jsonify(execute_command(command))


@app.route('/model', methods=['GET'])
def model():
    command = Lync12.get_model()
    return jsonify(execute_command(command))


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)


@app.route('/zone/<int:zone_id>/power', methods=['PUT'])
def zone_power(zone_id):
    if request.values['power'] == '1':
        power = True
    else:
        power = False
    logging.debug(str(zone_id) + " setting power to " + str(power))

    command = Lync12.set_power(zone_id, power)
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True
    return jsonify(execute_command(command))


@app.route('/zone/<int:zone_id>/mute', methods=['PUT'])
def zone_mute(zone_id):
    if request.values['mute'] == '1':
        power = True
    else:
        power = False
    logging.debug(str(zone_id) + " setting mute to " + str(power))

    command = Lync12.set_mute(zone_id, power)
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True
    return jsonify(execute_command(command))


@app.route('/zone/all/power', methods=['PUT', 'GET'])
def zone_power_all():
    if request.values['power'] == '1':
        power = True
    else:
        power = False
    logging.debug("setting power to of all zones to " + str(power))

    command = Lync12.set_power(0, power)
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True
    return jsonify(execute_command(command))


@app.route('/zone/<int:zone_id>/volume', methods=['PUT'])
def zone_volume(zone_id):
    try:
        volume = int(request.values['volume'])
    except (KeyError, ValueError):
        return jsonify({'error': 'volume must be an integer'}), 400
    if not 0 <= volume <= 100:
        return jsonify({'error': 'volume must be between 0 and 100'}), 400
    command = Lync12.set_volume(zone_id, volume)
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True
    return jsonify(execute_command(command))


@app.route('/zone/<int:zone_id>/input', methods=['PUT'])
def zone_input(zone_id):
    input_src = request.values['input']
    command = Lync12.set_input(zone_id, input_src)
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True
    return jsonify(execute_command(command))


@app.route('/zone/<int:zone_id>/balance', methods=['PUT', 'GET'])
def zone_balance(zone_id):
    try:
        balance_val = int(request.values['balance'])
    except (KeyError, ValueError):
        return jsonify({'error': 'balance must be an integer'}), 400
    if not -18 <= balance_val <= 18:
        return jsonify({'error': 'balance must be between -18 and 18'}), 400
    command = Lync12.set_balance(zone_id, balance_val)
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True
    return jsonify(execute_command(command))


@app.route('/zone/<int:zone_id>/treble', methods=['PUT', 'GET'])
def zone_treble(zone_id):
    try:
        treble_val = int(request.values['treble'])
    except (KeyError, ValueError):
        return jsonify({'error': 'treble must be an integer'}), 400
    if not -10 <= treble_val <= 10:
        return jsonify({'error': 'treble must be between -10 and 10'}), 400
    command = Lync12.set_treble(zone_id, treble_val)
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True
    return jsonify(execute_command(command))


@app.route('/zone/<int:zone_id>/bass', methods=['PUT', 'GET'])
def zone_base(zone_id):
    try:
        bass_val = int(request.values['bass'])
    except (KeyError, ValueError):
        return jsonify({'error': 'bass must be an integer'}), 400
    if not -10 <= bass_val <= 10:
        return jsonify({'error': 'bass must be between -10 and 10'}), 400
    command = Lync12.set_bass(zone_id, bass_val)
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True
    return jsonify(execute_command(command))


@app.route('/mp3/<string:action>', methods=['PUT', 'GET'])
def mp3_controls(action):
    action_id = _MP3_ACTIONS.get(action)
    if action_id is None:
        logging.error('MP3 URL error: ' + action)
        abort(404)

    command = Lync12.mp3_action(action_id)
    global __dirty_bit
    with _cache_lock:
        __dirty_bit = True
    return jsonify(execute_command(command))


if __name__ == '__main__':
    log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
    logging.basicConfig(level=log_level)
    app.run(port=8080, host='0.0.0.0')
