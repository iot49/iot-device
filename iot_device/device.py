from .device_registry import DeviceRegistry
from .eval import Eval, DeviceError
from .repl_eval import ReplEval
from .eval_fops import EvalFops
from .eval_rsync import EvalRsync
from .config_store import Config

from abc import abstractmethod
import os, threading, time, logging


logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


# Composed object:
#     ReplEval provides Eval for MicroPython raw repl
#     EvalFops adds file operations
#     EvalRsync adds rsync, rlist capability
class EvalFopsRsync(EvalFops, EvalRsync, ReplEval):
    def __init__(self, device, **kwargs):
        super(EvalFopsRsync, self).__init__(device, **kwargs)


class Device(DeviceRegistry):

    def __init__(self, id: str, desc: str, uid=None):
        self.__description = desc
        if uid:
            self.__uid = uid
        else:
            with self as repl:
                self.__uid = repl.uid
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
        """Device name, from mcu/base/hosts.py"""
        return Config.uid2hostname(self.uid)

    @property
    def projects(self) -> list:
        """Projects folders of this device, from mcu/base/hosts.py"""
        return Config.host_projects(self.uid)

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
        Raises DeviceError
        """
        result = bytearray()
        start = time.monotonic()
        while not result.endswith(pattern):
            if (time.monotonic() - start) > timeout:
                raise DeviceError(f"Timeout reading from MCU, got {result}, expect {pattern}")
            b = self.read(size=1)
            result.extend(b)
        return result

    def flush_input(self):
        """Flush input buffer - data from MCU
        Implement as needed, e.g. for SerialDevice."""
        pass

    def __enter__(self) -> Eval:
        if self.protocol == 'repl':
            return EvalFopsRsync(self)
        else:
            raise NotImplementedError(f"No evaluator for protocol {self.protocol}")

    @abstractmethod
    def __exit__(self, type, value, traceback):
        pass
