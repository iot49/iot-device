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

"""
Environment Variables

  Name          Default
* IOT           ~
* IOT49         $IOT/iot49
* IOT_DEVICES   ./devices:.:$IOT49/devices
* IOT_LIBS      ./lib:.:$IOT49/lib
* IOT_SECRETS   ./lib/secrets.py:./secrets.py:$IOT49/lib/secrets.py
"""

class Env:

    @staticmethod
    def expand_path(path):
        # with cd(Env.iot_dir()):
        #    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))
        return os.path.expanduser(os.path.expandvars(path))

    @staticmethod
    def iot_dir():
        return os.getenv('IOT', '~')

    @staticmethod
    def iot49_dir():
        return os.getenv('IOT49', os.path.join(Env.iot_dir(), 'iot49'))

    @staticmethod
    def iot_device_dirs():
        return [ './devices', '.' ] + os.getenv('IOT_DEVICES', os.path.join(Env.iot49_dir(), 'devices')).split(':')

    @staticmethod
    def iot_lib_dirs():
        return [ './lib', '.' ] + os.getenv('IOT_LIBS', os.path.join(Env.iot49_dir(), 'lib')).split(':')
        
    @staticmethod
    def iot_secrets():
        if 'IOT_SECRETS' in os.environ: return os.getenv('IOT_SECRETS')
        for s in [ './lib/secrets', './secrets.py' ]:
            if os.path.isfile(s): return s
        return os.path.join(Env.iot49_dir(), 'lib/secrets.py')
    
    @staticmethod
    def print_config():
        print("IOT:        ", Env.iot_dir())
        print("IOT49:      ", Env.iot49_dir())
        print("IOT_SECRETS:", Env.iot_secrets())
        print("IOT_DEVICES:", Env.iot_device_dirs())
        print("IOT_LIBS:   ", Env.iot_lib_dirs())

# ensure these are defined ...

if not os.getenv('IOT'):
    os.environ['IOT'] = '~'

if not os.getenv('IOT49'):
    os.environ['IOT49'] = Env.expand_path('$IOT/iot49')
