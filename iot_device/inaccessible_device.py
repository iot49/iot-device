from .device import Device

import os, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class InaccessibleDevice(Device):

    def __init__(self, url, error_state):
        self._url = url
        self._uid = "00:00:00:00:00:00"
        self._error_state = error_state

    @property
    def name(self) -> str:
        """Device error state (DeviceRegistry.register)"""
        return self._error_state

    @property
    def error_state(self) -> str:
        """Device error state (DeviceRegistry.register)"""
        return self._error_state

    def read(self, size=None):
        raise RuntimeError("device is inaccessible")

    def write(self, data):
        raise RuntimeError("device is inaccessible")

    def __enter__(self):
        raise RuntimeError("device is inaccessible")

    def __exit__(self, type, value, traceback):
        pass
