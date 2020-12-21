from .device_registry import DeviceRegistry
from .remote_exec import RemoteError
from .remote_repl import RemoteRepl
from .remote_rsync import RemoteRsync
from .config_store import Config

from abc import abstractmethod
import os, threading, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class Device(DeviceRegistry):

    def __init__(self, id: str, desc: str, uid=None):
        self.__description = desc
        if uid:
            self.__uid = uid
        else:
            with self as repl:
                self.__uid = repl.uid()
        self.register(id, self)

    @property
    def uid(self) -> str:
        return self.__uid

    @property
    def description(self) -> str:
        return self.__description

    @property
    def protocol(self) -> str:
        return 'repl'

    @property
    @abstractmethod
    def address(self):
        pass

    @property
    @abstractmethod
    def connection(self) -> str:
        # serial, net, ...
        pass

    @property
    def name(self) -> str:
        """Device name, from projects/config/mcu.py"""
        return Config.get_device(self.uid, 'name', self.uid)

    @property
    def projects(self) -> list:
        """Projects folders of this device, from projects/config/mcu.py"""
        return Config.get_device(self.uid, 'projects', ['base'])

    @property
    def root(self) -> str:
        """"""
        return Config.get_device(self.uid, 'root', '/')

    @abstractmethod
    def read(self, size=1) -> bytes:
        """Read size bytes"""
        pass

    @abstractmethod
    def read_all(self) -> bytes:
        """Read all available data"""
        pass

    @abstractmethod
    def write(self, data: bytes):
        """Writes data"""
        pass

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

    def __enter__(self):
        if self.protocol == 'repl':
            return RemoteRsync(RemoteRepl(self))
        else:
            raise NotImplementedError(f"No evaluator for protocol {self.protocol}")

    @abstractmethod
    def __exit__(self, type, value, traceback):
        pass
