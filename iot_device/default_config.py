# default config for IoT49

import os

default_config = {}
default_docs   = {}

def __register(name, value, doc):
    default_config[name] = value
    default_docs  [name] = doc

__register('host_dir', 
    os.path.expanduser(os.path.join(os.getenv('IOT49', '~/'), 'mcu')),
    "Configuration and libraries. Default: $IOT49/mcu")

__register('server_port', 
    50001,
    "Port on which DeviceServer listens for connections")

__register('password', 
    "replace with a strong password",
    "Password protection for NetDevice & DeviceServer")

__register('mpy-cross',
    os.path.join(os.getenv('IOT49', '~/'), 'bin'),
    "Base path to `mpy-cross`. The full path is `$compiler/%implementation/mpycross`")
