# env.py

from .utilities import cd
import os

"""
Environment Variables

  Name          Default
* IOT           ~
* IOT49         $IOT/iot49
* IOT_DEVICES   $IOT49/devices
* IOT_LIBS      $IOT49/lib
* IOT_SECRETS   $IOT49/lib/secrets.py
"""

class Env:

    @staticmethod
    def abs_path(path):
        with cd(Env.iot_dir()):
            return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))

    @staticmethod
    def iot_dir():
        return os.getenv('IOT', '~')

    @staticmethod
    def iot49_dir():
        return os.getenv('IOT49', os.path.join(Env.iot_dir(), 'iot49'))

    @staticmethod
    def iot_secrets():
        return os.getenv('IOT_SECRETS', os.path.join(Env.iot49_dir(), 'libs/secrets.py'))
    
    @staticmethod
    def iot_device_dirs():
        return os.getenv('IOT_DEVICES', os.path.join(Env.iot49_dir(), 'devices')).split(':')

    @staticmethod
    def iot_lib_dirs():
        return os.getenv('IOT_LIBS', os.path.join(Env.iot49_dir(), 'libs')).split(':')
        
    @staticmethod
    def print_config():
        print("IOT:        ", Env.iot_dir())
        print("IOT49:      ", Env.iot49_dir())
        print("IOT_SECRETS:", Env.iot_secrets())
        print("IOT_DEVICES:", Env.iot_device_dirs())
        print("IOT_LIBS:   ", Env.iot_lib_dirs())
