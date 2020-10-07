from .eval import Eval
from .repl_eval import ReplEval
from .eval_fops import EvalFops
from .eval_rsync import EvalRsync
from .config_store import Config

from abc import ABC, abstractmethod
import threading
import time
import logging

logger = logging.getLogger(__file__)


# Composed object:
#     ReplEval provides Eval for MicroPython raw repl
#     EvalFops adds file operations
#     EvalRsync adds rsync, rlist capability
class EvalFopsRsync(EvalFops, EvalRsync, ReplEval):
    def __init__(self, device, **kwargs):
        super(EvalFopsRsync, self).__init__(device, **kwargs)


class Device(ABC):

    def __init__(self, uid=None):
        self.__lock = threading.Lock()
        if uid:
            self.__uid = uid
        else:
            with self as repl:
                self.__uid = repl.uid

    @property
    def uid(self):
        return self.__uid

    @property
    def protocol(self) -> str:
        return 'repl'

    @property
    @abstractmethod
    def address(self):
        pass

    @property
    @abstractmethod
    def connection(self):
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

    def close(self):
        pass

    def read_until(self, pattern: bytes, timeout=5):
        """Read until pattern
        Raises TimeoutError
        """
        result = bytearray()
        start = time.monotonic()
        while not result.endswith(pattern):
            if (time.monotonic() - start) > timeout:
                raise TimeoutError(f"Timeout reading from IoT device, got '{result.decode()}', expect '{pattern.decode()}'")
            b = self.read(size=1)
            result.extend(b)
        return result

    def __eq__(self, other):
        return self == other

    @property
    def locked(self) -> bool:
        return self.__lock.locked()

    def __enter__(self) -> Eval:
        if not self.__lock.acquire(timeout=10):
            raise TimeoutError("lock acquisition timed out for {self.name} ({self.uid})")
        if self.protocol == 'repl':
            return EvalFopsRsync(self)
        else:
            raise NotImplementedError(f"No evaluator for protocol {self.protocol}")

    def __exit__(self, type, value, traceback):
        self.__lock.release()

    @abstractmethod
    def __hash__(self) -> int:
        pass
        