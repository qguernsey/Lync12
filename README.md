# Lync12

## A quick overview:
lync.py is the main library that knows how to talk to the Lync12 controller. It has a Lync12Command factory class. You basically ask it for a command and it will return a command that can be executed over a serial connection.  I have tested this on Lync12 Version 2 hardware.

Example:
```
zone_id = 1
power = True
command = Lync12Command.set_power(zone_id, power)
port = "/dev/ttyUSB0"
ser = serial.Serial(port, 38400, timeout=2)
result = command.execute(ser)
ser.close()
print result.json_data()
```

## Files
App.py is a simple Flask app that provides a REST API to control the different zones. I run this app on port 8080 using supervisord.
audio.html and audio.js Provide a web interface that will use the REST API to control the speakers. Input names are currently generic and hardcoded.  Zone Names are pulled dynamically from the controller.
