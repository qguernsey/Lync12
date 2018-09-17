# import time
# import collections
# import json
import requests
import datetime
import json


class LyncConnector(object):
    def __init__(self, host, port):
        self.host = host
        self.port = str(port)
        self.secure = False
        self.username = ''
        self.password = ''
        self.__status_update_time = datetime.datetime(1970, 1, 1, 0, 0)
        self.__current_status = 'not init-ed'
        self.__cache_timeout = 15

    def setup(self, username, password):
        self.secure = True
        self.username = username
        self.password = password

    def __do_put(self, uri, data):
        url = 'http://' + self.host + ':' + self.port + uri
        # print(url)
        r = requests.put(url, data)
        return_code = r.status_code
        if return_code == 200:
            return True
        else:
            return False

    def __do_post(self, uri, data):
        url = 'http://' + self.host + ':' + self.port + uri
        # print(url)
        r = requests.post(url, data)
        return_code = r.status_code
        if return_code == 200:
            return True
        else:
            return False

    def __do_get(self, uri):
        url = 'http://' + self.host + ':' + self.port + uri
        # print(url)
        r = requests.get(url)
        return_code = r.status_code
        if return_code != 200:
            return 'Error'
        else:
            return r.text

    def get_status(self):
        """Get Controller Status.  Returns a JSON"""
        # print('Getting Status')
        current_time = datetime.datetime.now()
        run_time = self.__status_update_time + datetime.timedelta(seconds=self.__cache_timeout)
        if current_time > run_time:
            self.__current_status = self.__do_get('/status')
            self.__status_update_time = current_time
        return self.__current_status

    def get_zone_status(self, zone_id):
        zone_status = self.get_status()
        zone_json = json.loads(zone_status)
        for key, value in zone_json.items():
            if str(zone_id) == key:
                # print(key)
                # print(value)
                return value
        return '{}'

    def set_zone_power(self, zone_id, power_state):
        """Turn media zones on and off."""
        # _LOGGER.debug("Turning zone %d %b", zone_id, power_state)
        if power_state:
            data = {'power': '1'}
        else:
            data = {'power': '0'}
        return self.__do_put('/zone/' + str(zone_id) + '/power', data)

    def set_zone_mute(self, zone_id, mute_state):
        """Turn media zones on and off."""
        # _LOGGER.debug("Muting zone %d %b", zone_id, mute_state)
        if mute_state:
            data = {'mute': '1'}
        else:
            data = {'mute': '0'}
        return self.__do_put('/zone/' + str(zone_id) + '/mute', data)

    def set_zone_source(self, zone_id, source_id):
        """Set Zone input source"""
        # _LOGGER.debug("Setting Zone %s to source %s", zone_id, source_id)
        data = {'input': source_id}
        return self.__do_put('/zone/' + str(zone_id) + '/input', data)
