# import serial
import time
import collections
import json
import copy
import math


class ByteUtils:

    """ helper class to create byte arrays """
    @staticmethod
    def ba2hex(a):
        """ converts a byte array to hex """
        return ":".join("%0.2x" % x for x in a)

    @staticmethod
    def s2hex(s):
        """ converts a string to hex values """
        return ":".join(chr(x) for x in s)

    @staticmethod
    def diff(s1, s2, name1, name2):
        h1 = ByteUtils.s2hex(s1)
        h2 = ByteUtils.s2hex(s2)
        print("1 (" + name1 + ") ")
        print(h1)
        print("2 (" + name2 + ") ")
        print(h2)
        d = ""
        a1 = h1.split(":")
        a2 = h2.split(":")
        for i in range(0, len(a1)):
            if len(d) > 0:
                d += ":"
            if a1[i] != a2[i]:
                try:
                    # d += ByteUtils.b2h(ByteUtils.h2b(a1[i]) - ByteUtils.h2b(a2[i]))
                    d += a1[i]
                except IndexError:
                    print(a1, a2)
            else:
                d += "--"
        print("d ")
        print(d)

    @staticmethod
    def h2b(v):
        """ hex to byte """
        return int(v, 16)

    @staticmethod
    def b2h(v):
        """ byte to hex """
        return "%0.2x" % v

    @staticmethod
    def to_byte_array(hex_tuple):
        """ converts an array of hex string to a byte array """
        command = bytearray([0 for number in range(len(hex_tuple))])
        index = 0
        for h in hex_tuple:
            command[index] = ByteUtils.h2b(h)
            index += 1
        return ByteUtils._checksum(command)

    @staticmethod
    def _checksum(command):
        """ calculates the checksum """
        checksum = 0
        for char in command:
            checksum += char
        command[len(command)-1] = checksum % 256
        return command


class Lync12Lookup:

    @staticmethod
    def tone_adjustment(v):
        if v == 0x00:
            return 0
        if v < 0x0B:
            return int(v, 16)
        if v > 0x0B:
            return 0

    @staticmethod
    def balance_adjustment(v):
        if v == 0x00:
            return 0
        if v < 0x13:
            return int(v, 16)
        if v > 0x14:
            return 0

    @staticmethod
    def get_string_name(a):
        name = []
        i = 0
        # print("get name")
        # print(a)
        while i <= len(a) and a[i] != 0x00:
            name.append(int(a[i]))
            i += 1

        return ''.join(chr(c) for c in name)


class ZoneState(object):
    def __init__(self, bindata):
        data = []
        for i in bindata:
            # print(i)
            data.append(i)
        if data[0] != 0x02:
            raise Exception("Zone- bad data input: header "+str(data[0])+" "+ByteUtils.s2hex(data))
        if data[1] != 0x00:
            raise Exception("Zone- bad data input: reserved")
        self.zone = data[2]
        self.command = data[3]
        self.state = collections.OrderedDict()
        if data[3] == 5:
            # Data1 - general state
            # print(type(data[4]))
            # print(bin(data[4]))
            self.state["power"] = True if data[4] & 0b00000001 else False
            self.state["mute"] = True if data[4] & 0b00000010 else False
            self.state["dnd"] = True if data[4] & 0b00000100 else False

            # Data2- Party Mode, all on/off
            self.state["party"] = True if data[5] & 0b00100000 else False
            self.state["allon"] = True if data[5] & 0b10000000 else False
            self.state["alloff"] = True if data[5] & 0b01000000 else False

            # MP3 repeat
            self.state["mp3repeat"] = True if data[6] & 0b00010000 else False

            # MP3 repeat party
            self.state["party repeat"] = True if data[7] & 0b00010000 else False

            # self.state["party_input"] = data[4] & 0b00000111

            # Data2 - keypad led indicator
            # self.state["mode_led"] = data[5] & 0b01111111

            # Data3 - inputs?
            # self.state["led_input"] = data[6] & 0b00111111
            # self.state["power3"] = True if data[6] & 0b10000000 else False
            # self.state["input1"] = True if data[6] & 0b00100000 else False
            # self.state["input2"] = True if data[6] & 0b00010000 else False
            # self.state["input3"] = True if data[6] & 0b00001000 else False
            # self.state["input4"] = True if data[6] & 0b00000100 else False
            # self.state["input5"] = True if data[6] & 0b00000010 else False
            # self.state["input6"] = True if data[6] & 0b00000001 else False

            # Data4 - reserved

            # Data5 - input port
            self.state["input"] = data[8] + 1

            # Data6 - volume (range 195-255; 0 == max)
            volume = data[9]
            if volume == 0:
                volume = 256
            self.state["volume-panel"] = volume - 196
            volume = int((volume - 195.0) / 61.0 * 100.0)
            self.state["volume"] = volume

            # Don't know what the codes are for these.  In the UI but not on the hex code sheet.
            # Data7 - treble
            self.state["treble"] = Lync12Lookup.tone_adjustment(data[10])

            # Data8 - bass
            self.state["bass"] = Lync12Lookup.tone_adjustment(data[11])

            # Data9 - balance
            self.state["balance"] = Lync12Lookup.balance_adjustment(data[12])

        # checksum
        self.state["checksum"] = data[13]
        self.state["inputs"] = []

    def clone_state(self):
        return copy.copy(self.state)

    def pretty(self):
        # return "zone: "+str(self.zone)+"\n"+json.dumps(self.state, indent=2, separators=(',', ': '))
        return "zone: "+str(self.zone)+" "+json.dumps(self.state)


class Lync12Result(object):
    def __init__(self, zone_states):
        self.data = {}
        for z in zone_states:
            if z.zone != 0:
                self.data[z.zone] = z.clone_state()
                self.data[z.zone]['zone'] = z.zone

    def json(self):
        return json.dumps(self.data)

    def json_data(self):
        return self.data


class Lync12Command(object):
    def __init__(self, command_hex, rx_bytes, name, wait_time=0):
        self.command = ByteUtils.to_byte_array(command_hex)
        self.rx_bytes = rx_bytes
        self.result = None
        self.name = name
        self.zone_states = []
        self.wait_time = wait_time

    def execute(self, ser):
        """ execute the command and returns the result """
        ser.write(self.command)
        print(str(self.command))
        self.result = ser.read(self.rx_bytes)
        self._parse()
        if self.wait_time > 0:
            time.sleep(self.wait_time)
        return Lync12Result(self.zone_states)

    def _parse(self):
        # Need to dynamically breakup the bit stream based on the return command.
        i = 0

        # 6 is the shortest return command
        while i+6 <= len(self.result):
            # Packet peek
            # print( str(self.result[i:i+20]))
            # verify header and reserve bit
            # zone = 0
            # command = 0

            if not(self.result[i] == 0x02 or self.result[i] == 0x4c or self.result[i] == 0xFF):
                raise Exception("bad data input: header " + str(self.result[i:i+6]))
            elif self.result[i] == 0x4c:  # Check for raw Lync<num< return
                print(str(self.result[i:i + 6]))
                # TODO: return JSON with model
                i += 6
                continue
                # hard code for Lync12 only returned with model request, may break this out into separate method
            elif self.result[i] == 0xFF:  # trailing headers at the end of the all data
                print(str(self.result[i:i + 6]))
                # TODO: need to handle model number
                # TODO: need to handle Save locations
                # end of line.. break..
                break

            if self.result[i+1] != 0x00:
                raise Exception("bad data input: reserved")
            zone = self.result[i+2]
            command = self.result[i+3]

            # Zone state
            if command == 0x05:
                print("Zone State " + str(zone))
                # print(str(self.result[i:i + 14]))
                self.zone_states.append(ZoneState(self.result[i:i+14]))
                i += 14
                continue
            # Key Pad Exists
            elif command == 0x06:
                print("Key Pad Command")
                print(str(self.result[i:i + 14]))
                i += 14
                continue
            # MP3 Play End Stop
            elif command == 0x09:
                print("MP3 Stop")
                print(str(self.result[i:i + 6]))
                i += 6
                continue
            # Zone Source Name
            elif command == 0x0E:
                # print("Zone Source Name")
                # print(str(self.result[i+4:i + 15]))
                sname = Lync12Lookup.get_string_name(self.result[i + 4:i + 15])
                self.zone_states[zone - 1].state["inputs"].append(sname)
                print("Source " + str(zone) + " Name-" + sname)
                i += 18
                continue
            # Zone Name
            elif command == 0x0D:
                # print("Zone Name")
                # print(str(self.result[i+4:i + 15]))
                zname = Lync12Lookup.get_string_name(self.result[i+4:i + 15])
                self.zone_states[zone-1].state["name"] = zname
                print("Zone " + str(zone) + " Name-" + zname)
                i += 18
                continue
            # MP3 File Name
            elif command == 0x11:
                print("MP3 File Name")
                print(str(self.result[i:i + 69]))
                i += 69
                continue
            # MP3 Artist Name
            elif command == 0x12:
                print("MP3 Artist Name")
                print(str(self.result[i:i + 69]))
                i += 69
                continue
            # MP3 On
            elif command == 0x13:
                print("MP3 On")
                print(str(self.result[i:i + 6]))
                i += 6
                continue
            # MP3 Off
            elif command == 0x14:
                print("MP3 off")
                # print(str(self.result[i:i + 22]))
                print(str(self.result[i:i + 200]))
                i += 22
                continue
            elif command == 0x1b:
                print("Error Code?")
                print(str(self.result[i:i + 14]))
                i += 14
                continue
            else:
                print("hmmm.. shouldn't be here")
                print(str(self.result[i:i + 40]))
                i += 1

    def debug(self):
        print("Command: %s (tx_bytes %d)" % (self.name, self.rx_bytes))
        print(ByteUtils.ba2hex(self.command))
        if self.result:
            print("result: (len: " + str(len(self.result)) + ") " +
                  str(ByteUtils.s2hex(self.result)) + " " + str(self.result))
        for i in self.zone_states:
            print(i.pretty())
        print("\n")

    def diff(self, label, command):
        """ prints out the difference between the 2 command results """
        print("diff> " + label)
        ByteUtils.diff(self.result, command.result, self.name, command.name)
        print("\n")

    @staticmethod
    def get_model():
        command = (
            "02",  # head
            "00",  # reserved
            "00",  # zone
            "08",  # command
            "00",  # data
            "00",  # checksum
            )
        return Lync12Command(command, 6, "model")

    @staticmethod
    def get_zone_state():
        command = (
          "02",  # head
          "00",  # reserved
          "00",  # zone
          "0C",  # command
          "00",  # data
          "00",  # checksum
          )
        return Lync12Command(command, 8000, "state")

    @staticmethod
    def get_zone_names():
        command = (
          "02",  # head
          "00",  # reserved
          "01",  # zone
          "0D",  # command
          "00",  # data
          "00",  # checksum
          )
        return Lync12Command(command, 2000, "state")

    @staticmethod
    def get_source_names():
        command = (
          "02",  # head
          "00",  # reserved
          "01",  # zone
          "0E",  # command
          "00",  # data
          "00",  # checksum
          )
        return Lync12Command(command, 2000, "state")

    # Different power on/off codes when controlling all zones
    @staticmethod
    def set_power(zone, power):
        if zone == 0:
            if power:
                data = "55"
            else:
                data = "56"
        else:
            if power:
                data = "57"
            else:
                data = "58"
        command = (
          "02",  # head
          "00",  # reserved
          ByteUtils.b2h(zone),  # zone
          "04",  # command
          data,  # data
          "00",  # checksum
          )
        sleep_time = 0.25
        if power:
            sleep_time = 2

        return Lync12Command(command, 28, "z"+str(zone)+" power "+str(power), sleep_time)

    # Lync12 v2 Documentation is wrong for setting volume.  They have different bit codes for send and receive.
    # The controller uses the documented receive codes to set as well.. not the published ones.
    @staticmethod
    def set_volume(zone, vol):
        volume_int = vol * .6
        print("Volume panel: " + str(volume_int))
        # volume = 0
        if volume_int > 60:
            volume_int = 60
        elif volume_int < 0:
            volume_int = 0

        if volume_int == 60:
            volume = 0x00
        else:
            volume = 0xFF - (60 - int(math.floor(volume_int)))

        print("Volume controller: ")
        print(int(volume))

        # volume = 0x43 + int(math.floor(volume_int))
        # volume = int(math.floor(volume_int))
        # print(volume)
        # print(ByteUtils.b2h(volume))
        command = (
          "02",  # head
          "00",  # reserved
          ByteUtils.b2h(zone),  # zone
          "15",
          ByteUtils.b2h(int(volume)),  # volume
          "00",  # checksum
          )
        return Lync12Command(command, 28, "z"+str(zone)+" set_volume "+str(volume))

    @staticmethod
    def set_mute(zone, muted):
        if muted:
            mute = "1E"
        else:
            mute = "1F"
        command = (
          "02",  # head
          "00",  # reserved
          ByteUtils.b2h(zone),  # zone
          "04",  # command
          mute,  # data
          "00",  # checksum
          )
        return Lync12Command(command, 28, "z"+str(zone)+" mute")

    @staticmethod
    def lookup_input(input_num):
        input_array = ["10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
                       "1A", "1B", "63", "64", "65", "66", "67", "68"]
        if 1 <= input_num <= 18:
            return input_array[input_num - 1]
        else:
            return "00"

    @staticmethod
    def set_input(zone, input_num):
        """ sets the zone's input to to the input number.  input number is 1 based """
        input_num = int(input_num)
        command = (
          "02",  # head
          "00",  # reserved
          ByteUtils.b2h(zone),  # zone
          "04",  # command
          Lync12Command.lookup_input(input_num),  # data, input 1 is 0x03, 2 is 0x04
          "00",  # checksum
          )
        return Lync12Command(command, 28, "z"+str(zone)+" input"+str(input_num))

    @staticmethod
    def dnd(zone, dnded):
        if dnded:
            b_data = "59"
        else:
            b_data = "5A"
        command = (
          "02",  # head
          "00",  # reserved
          ByteUtils.b2h(zone),  # zone
          "04",  # command
          b_data,  # data
          "00",  # checksum
        )
        return Lync12Command(command, 14, "z"+str(zone)+" mute")

    """
if __name__ == '__main__':
    # this was run as a main script

    state = []

    def track_state(ser, label):
        s1 = command = Lync12Command.get_zone_state(5)
        data = command.execute(ser)
        state.append(s1)
        s1.name += " "+label
        s1.debug()


    port = "/dev/ttyUSB0"
    ser = serial.Serial(port, 38400, timeout=2)

    track_state(ser, "init")

    c1 = command = Lync12Command.set_power(3, True)
    data = command.execute(ser)
    # command.debug()

    time.sleep(3)
    # ===============================================

    track_state(ser, "after on")

    c2 = command = Lync12Command.set_input(3, 2)
    data = command.execute(ser)
    command.debug()

    time.sleep(2)
    # ===============================================

    track_state(ser, "after input 2")

    c2 = command = Lync12Command.set_input(3, 3)
    data = command.execute(ser)
    command.debug()

    time.sleep(2)
    # ===============================================

    track_state(ser, "after input 3")

    c2 = command = Lync12Command.set_input(3, 4)
    data = command.execute(ser)
    # command.debug()

    time.sleep(2)
    # ===============================================

    track_state(ser, "after input 4")

    c2 = command = Lync12Command.set_input(3, 1)
    data = command.execute(ser)
    command.debug()

    time.sleep(2)
    # ===============================================

    track_state(ser, "after input 1")

    c2 = command = Lync12Command.vol_up(3)
    data = command.execute(ser)
    c2.debug()
    c2 = command = Lync12Command.vol_up(3)
    data = command.execute(ser)
    c2.debug()
    c2 = command = Lync12Command.vol_up(3)
    data = command.execute(ser)
    c2.debug()

    track_state(ser, "after volup 1")

    c2 = command = Lync12Command.vol_down(3)
    data = command.execute(ser)
    c2.debug()
    c2 = command = Lync12Command.vol_down(3)
    data = command.execute(ser)
    c2.debug()
    c2 = command = Lync12Command.vol_down(3)
    data = command.execute(ser)
    c2.debug()

    # command.debug()

    time.sleep(2)
    # ===============================================

    track_state(ser, "after input vol")

    c4 = command = Lync12Command.mute(3)
    data = command.execute(ser)
    # command.debug()

    time.sleep(1)
    # ===============================================

    track_state(ser, "after mute1")

    c4 = command = Lync12Command.mute(3)
    data = command.execute(ser)
    # command.debug()

    time.sleep(1)
    # ===============================================

    track_state(ser, "after mute2")

    c4 = command = Lync12Command.set_power(3, False)
    data = command.execute(ser)
    # command.debug()

    time.sleep(1)
    # ===============================================

    track_state(ser, "end")

    # for i in range(0, len(state) - 1):
    #  state[i].diff("s%d, s%d" % (i, i+1), state[i + 1])
    # state[0].diff("s%d, s%d" % (0, len(state) - 1), state[len(state) - 1])


    s1 = command = MCA66Command.get_zone_state(3);
    data = command.execute(ser)
  
    c1 = command = MCA66Command.set_power(3, True);
    data = command.execute(ser)
    command.debug()
  
    time.sleep(3)
  
    s2 = command = MCA66Command.get_zone_state(3);
    data = command.execute(ser)
  
    c2 = command = MCA66Command.vol_up(3);
    data = command.execute(ser)
    command.debug()
  
    time.sleep(2)
  
    s3 = command = MCA66Command.get_zone_state(3);
    data = command.execute(ser)
  
    c3 = command = MCA66Command.vol_down(3);
    data = command.execute(ser)
    command.debug()
  
    time.sleep(2)
  
    s4 = command = MCA66Command.get_zone_state(3);
    data = command.execute(ser)
  
    c4 = command = MCA66Command.set_power(3, False);
    data = command.execute(ser)
    command.debug()
  
    time.sleep(1)
  
    s5 = command = MCA66Command.get_zone_state(3);
    data = command.execute(ser)
  
    s1.diff("s1, s2", s2)
    s2.diff("s2, s3", s3)
    s3.diff("s3, s4", s3)
    s4.diff("s4, s5", s5)
    s1.diff("s1, s5", s5)
    """

    """
    c2 = command = MCA66Command.get_zone_state(5);
    data = command.execute(ser)
    command.debug()
  
    c3 = command = MCA66Command.set_power(5, True);
    data = command.execute(ser)
    command.debug()
  
    c4 = command = MCA66Command.set_power(6, True);
    data = command.execute(ser)
    command.debug()
  
    time.sleep(2)
  
    c4_1 = command = MCA66Command.get_zone_state(5);
    data = command.execute(ser)
    command.debug()
  
    c5 = command = MCA66Command.set_power(5, False);
    data = command.execute(ser)
    command.debug()
  
    c6 = command = MCA66Command.set_power(6, False);
    data = command.execute(ser)
    command.debug()
  
    c7 = command = MCA66Command.get_zone_state(5);
    data = command.execute(ser)
    command.debug()
  
  
    c2.diff("turned on state", c4_1)
    c3.diff("zone 5", c5)
    c4.diff("zone 6", c6)
    c2.diff("final state", c7)
  

    ser.close()
      """
