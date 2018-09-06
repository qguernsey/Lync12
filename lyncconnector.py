# import time
# import collections
# import json
import requests


class LyncConnector(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.secure = False
        self.username = ''
        self.password = ''

    def setup(self, username, password):
        self.secure = True
        self.username = username
        self.password = password

    def __do_put(self, uri, data):
        r = requests.put('http://'+self.host+':'+self.port+'/'+uri, data)
        return_code = r.status_code
        if return_code == 200:
            return True
        else:
            return False

    def __do_post(self, uri, data):
        r = requests.post('http://'+self.host+':'+self.port+'/'+uri, data)
        return_code = r.status_code
        if return_code == 200:
            return True
        else:
            return False

    def __do_get(self, uri):
        r = requests.get('http://'+self.host+':'+self.port+'/'+uri)
        return_code = r.status_code
        if return_code != 200:
            return 'Error'

    def set_zone_power(self, zone_id, power_state):
        """Turn media zones on and off."""
        # _LOGGER.debug("Turning zone %d %b", zone_id, power_state)
        if power_state:
            data = {'power': '1'}
        else:
            data = {'power': '0'}
        return self.__do_put('/zone/'+zone_id+'/power', data)

    def set_zone_source(self, zone_id, source_id):
        """Set Zone input source"""
        # _LOGGER.debug("Setting Zone %s to source %s", zone_id, source_id)
        data = {'input': source_id}
        return self.__do_put('/zone/' + zone_id + '/input', data)







