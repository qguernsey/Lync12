#!/usr/bin/env python
from flask import Flask, jsonify, abort
from lync12 import Lync12Command as Lync12
from flask_cors import CORS  # The typical way to import flask_cors
from flask import request
import serial

app = Flask(__name__)
cors = CORS(app)


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
    command = Lync12.get_zone_state()
    return jsonify(execute_command(command))


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


@app.route('/zone/<int:zone_id>/power', methods=['PUT'])
def zone_power(zone_id):
    if request.values['power'] == '1':
        power = True
    else:
        power = False
    print(str(zone_id) + " setting power to " + str(power))

    command = Lync12.set_power(zone_id, power)
    return jsonify(execute_command(command))


@app.route('/zone/<int:zone_id>/mute', methods=['PUT'])
def zone_mute(zone_id):
    if request.values['mute'] == '1':
        power = True
    else:
        power = False
    print(str(zone_id) + " setting mute to " + str(power))

    command = Lync12.set_mute(zone_id, power)
    return jsonify(execute_command(command))


@app.route('/zone/all/power', methods=['PUT', 'GET'])
def zone_power_all():
    if request.values['power'] == '1':
        power = True
    else:
        power = False
    print("setting power to of all zones to " + str(power))

    command = Lync12.set_power(0, power)
    return jsonify(execute_command(command))


@app.route('/zone/<int:zone_id>/volume', methods=['PUT'])
def zone_volume(zone_id):
    volume = int(request.values['volume'])
    print('volume from web: ')
    print(volume)

    command = Lync12.set_volume(zone_id, volume)
    return jsonify(execute_command(command))


@app.route('/zone/<int:zone_id>/input', methods=['PUT'])
def zone_input(zone_id):
    input_src = request.values['input']
    command = Lync12.set_input(zone_id, input_src)
    return jsonify(execute_command(command))


@app.route('/mp3/<string:action>', methods=['PUT', 'GET'])
def mp3_controls(action):
    action_id = Lync12.MP3_NULL
    if not action:
        abort(404)
    elif action == 'play':
        action_id = Lync12.MP3_PLAY
    elif action == 'stop':
        action_id = Lync12.MP3_STOP
    elif action == 'repeatoff':
        action_id = Lync12.MP3_REPEAT_OFF
    elif action == 'repeaton':
        action_id = Lync12.MP3_REPEAT_ON
    elif action == 'forward':
        action_id = Lync12.MP3_FF
    elif action == 'back' or action == 'reverse':
        action_id = Lync12.MP3_FB
    else:
        print('MP3 URL error: ' + action)

    command = Lync12.mp3_action(action_id)
    return jsonify(execute_command(command))


if __name__ == '__main__':
    app.run(port=8080, host='0.0.0.0')
