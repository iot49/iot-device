from .eval import Eval, RemoteError
from .config_store import Config

from abc import ABC, abstractmethod
import os, threading, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class Device(ABC):

    def __init__(self, url:str):
        """Create device for given URL.
        Retrieves uid from device and raises error if device cannot be contacted.

        :param: url:str  e.g.
            serial:///dev/cu.usbmodem1413401
            net://mcu.com:1234
        """
        self._url = url
        # connect to device and retrieve it's uid
        # raise error if uid cannot be retrieved
        with self as repl:
            self._uid = repl.uid()

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
        return Config.get_device(self.uid, 'name', self.uid)

    @property
    def projects(self) -> list:
        """Projects folders of this device, convenience method"""
        return Config.get_device(self.uid, 'projects', ['base'])

    @property
    def root(self) -> str:
        """Root of file system on remote (e.g. /flash on pyboard)"""
        return Config.get_device(self.uid, 'root', '/')

    @abstractmethod
    def read(self, size=1) -> bytes:
        """Read size bytes"""

    @abstractmethod
    def read_all(self) -> bytes:
        """Read all available data"""

    @abstractmethod
    def write(self, data: bytes):
        """Writes data"""

    def read_until(self, pattern: bytes, timeout=3):
        """Read until pattern
        Raises RemoteError
        """
        result = bytearray()
        start = time.monotonic()
        while not result.endswith(pattern):
            if (time.monotonic() - start) > timeout:
                raise RemoteError(f"Timeout reading from MCU, got {result}, expect {pattern}")
            b = self.read(size=1)
            result.extend(b)
        return result

    def flush_input(self):
        """Flush input buffer - data from MCU
        Implement as needed, e.g. for SerialDevice."""
        pass

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
