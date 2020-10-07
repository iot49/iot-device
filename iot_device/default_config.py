# default config for IoT49

import os

default_config = {}
default_docs   = {}

def __register(name, value, doc):
    default_config[name] = value
    default_docs  [name] = doc

__register('host_dir', 
    os.path.expanduser(os.path.join(os.getenv('IOT49', '~/'), 'mcu'),
    "Path to microcontroller configuration and libraries")

__register('device_server_port', 
    50001,
    "Port on which DeviceServer listens for connections")

__register('password', 
    "replace with a strong password",
    "Password protection for NetDevice & DeviceServer")
