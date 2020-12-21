# sample mcu.py
# copy to $IOT49/projects/config/mcu.py

# one line for each microcontroller
# the uids uniquely identify each microcontroller
# obtain from the uid() function below

# the key is a user-friendly name identifying the microcontroller
# 'projects' is the list of directories synchronized by 'rsync'

# see example folder in https://github.com/iot49/iot-kernel for more information

mcu1 = "30:ae:a4:12:34:28"
mcu2_name = { 'uid': "3e:1c:dc:01:0a:fc", 'projects': ['base', 'stdlib', 'my_app'], doc='wicked fast computer' }



# run the code below on an mcu to get it's uid:

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
