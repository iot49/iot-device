# sample hosts.py
# copy to $IOT49/mcu/base

hosts = dict()

# one line for each microcontroller
# the hex numbers uniquely identify each microcontroller
# obtain from the uid() function below

# 'name' is a user-friendly name identifying the microcontroller
# 'projects' is the list of directories in Config.get('home_dir') synchronized by 'rsync'

# see example folder in https://github.com/iot49/iot-kernel for more information

hosts["30:ae:a4:12:34:28"] = { 'name': 'demo-wifi' }
hosts["3e:1c:dc:01:0a:fc"] = { 'name': 'demo', 'projects': ['base', 'stdlib', 'my_app'] }

def uid():
    try:
        import machine   # pylint: disable=import-error
        _id = machine.unique_id()
    except:
        try:
            import microcontroller   # pylint: disable=import-error
            _id = microcontroller.cpu.uid
        except:
            return None
    return ":".join("{:02x}".format(x) for x in _id)

