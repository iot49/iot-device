import pytest, time, os
from iot_device import DeviceRegistry

# use custom environment
projects_path = '~/iot-device/tests/projects'
os.environ['IOT_PROJECTS'] = projects_path

# find all connected devices
registry = DeviceRegistry()
registry.devices