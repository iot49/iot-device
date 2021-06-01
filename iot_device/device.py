from .eval import Eval, RemoteError
from .device_config import DeviceConfig

from abc import ABC, abstractmethod
import os, threading, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class Device(ABC):

    def __init__(self, url:str):
        """Create device for given URL.
        Retrieves uid from device and raises error if device cannot be contacted.

        :param: url:str
        e.g.
            serial:///dev/cu.usbmodem1413401
            telnet://mcu.com:23
        """
        self._url = url
        # connect to device and retrieve its uid; raise RemoteError if unsuccessful
        self._uid = url
        with self as repl:
            self._uid = repl.exec(_uid).decode()

    @abstractmethod
    def read(self, size=1) -> bytes:
        """Read bytes. Can be aborted by KeyboardInterrupt."""

    @abstractmethod
    def write(self, data: bytes):
        """Writes data to device."""

    @abstractmethod
    def inWaiting(self):
        """Number of bytes available for reading without blocking."""

    @abstractmethod
    def __enter__(self) -> Eval:
        """Usage pattern:

        with device as repl:
            repl.exec(...)
            repl.rlist(...)
        """

    @abstractmethod
    def __exit__(self, type, value, traceback):
        pass

    def __repr__(self):
        return f"{self.name} @ {self.url} ({self.uid})"

    @property
    def uid(self) -> str:
        """Cache"""
        return self._uid

    @property
    def url(self) -> str:
        return self._url

    @property
    def scheme(self) -> str:
        return self.url.split('://')[0]

    @property
    def address(self) -> str:
        return self.url.split('://')[1]

    @property
    def name(self) -> str:
        """Device name"""
        try:
            return DeviceConfig.get_device_config(self.uid).name
        except ValueError:
            return self.uid

    @property
    def config(self) -> DeviceConfig:
        return DeviceConfig.get_device_config(self.uid)


###############################################################################
# code snippet (run on remote)

_uid = """
uid = bytes(6)
try:
    import machine
    uid = machine.unique_id()
except:
    import microcontroller
    uid = microcontroller.cpu.uid
print(":".join("{:02x}".format(x) for x in uid), end="")
"""
