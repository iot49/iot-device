# env.py

from .utilities import cd
import os

"""
Environment Variables

  Name          Default
* IOT_PROJECTS  ~/projects
* IOT_DEVICES   $IOT_PROJECTS/devices
* IOT_LIBS      $IOT_PROJECTS/libs
* IOT_SECRETS   $IOT_LIBS/secrets.py
"""

class Env:

    @staticmethod
    def expand_path(path):
        return os.path.expanduser(os.path.expandvars(path))

    @staticmethod
    def iot_projects():
        return os.getenv('IOT_PROJECTS', '~/projects')

    @staticmethod
    def iot_devices():
        return os.getenv('IOT_DEVICES', os.path.join(Env.iot_projects(), 'devices'))

    @staticmethod
    def iot_libs():
        return os.getenv('IOT_LIBS', os.path.join(Env.iot_projects(), 'libs'))
        
    @staticmethod
    def iot_secrets():
        return os.getenv('IOT_SECRETS', os.path.join(Env.iot_libs(), 'secrets.py'))
    
    @staticmethod
    def print_config():
        print("IOT_PROJECTS:", Env.iot_projects())
        print("IOT_DEVICES: ", Env.iot_devices())
        print("IOT_LIBS:    ", Env.iot_libs())
        print("IOT_SECRETS: ", Env.iot_secrets())

# ensure this is defined ...

if not os.getenv('IOT_PROJECTS'):
    os.environ['IOT_PROJECTS'] = '~/projects'
