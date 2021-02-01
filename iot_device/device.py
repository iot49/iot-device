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
            mp

            ://mcu.com:1234
        """
        self._url = url
        # connect to device and retrieve its uid; raise RemoteError if unsuccessful
        self._uid = url
        with self as repl:
            self._uid = repl.exec(_uid).decode()

    @abstractmethod
    def read(self, size=None) -> bytes:
        """Read all availble data or max size.
        Not blocking: short read (including b'') if no data availble.
        Important: May be aborted by KeyboardInterrupt."""

    @abstractmethod
    def write(self, data: bytes):
        """Writes data to device."""

    def read_until(self, pattern: bytes, timeout=1):
        """Read until pattern.
        Intended to be used to check for repl responses.
        Longer timeout may be required for reboot
        (if boot.py takes a long time without output).
        Raises RemoteError if the device is not responsive."""
        result = bytearray()
        start = time.monotonic()
        while not result.endswith(pattern):
            if (time.monotonic() - start) > timeout:
                if len(pattern) == 0:
                    raise TimeoutError(f"No response from {self.url}")
                raise RemoteError(
                    f"Unexpected response from {self.url}: got\n"
                    f"'{result.decode()}'\nexpect\n'{pattern.decode()}'")
            b = self.read(size=1)
            if len(b) > 0:
                # device is responsive, give it more time
                start = time.monotonic()
                result.extend(b)
        return result

    @property
    def in_waiting(self):
        # override in SerialDevice
        return 0

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
        return Config.get_device(self.uid, 'name', self.uid)

    @property
    def projects(self) -> list:
        """Projects folders of this device, convenience method"""
        return Config.get_device(self.uid, 'projects', ['base'])

    @property
    def root(self) -> str:
        """Root of file system on remote (e.g. /flash on pyboard)"""
        return Config.get_device(self.uid, 'root', '/')


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
