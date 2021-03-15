from abc import ABC, abstractmethod
import os, inspect, logging, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class RemoteError(Exception):
    def __init__(self, msg, output=None, error=None):
        # print(f"RemoteError:\n  msg = {msg}\n  out = {output}\n  err = {error}")
        super().__init__(msg, output, error)

    @property
    def exception(self):
        try:
            return self.args[2].strip().split('\n')[-1]
        except:
            return self.args[0]

    @property
    def msg(self):
        return self.args[0] or b''

    @property
    def output(self):
        return self.args[1] or b''

    @property
    def traceback(self):
        return self.args[2] or b''

    def __str__(self):
        if self.traceback:
            try:
                return self.traceback.decode()
            except UnicodeError:
                return self.traceback
        return self.msg


def default_data_consumer(data:bytes):
    print(data)


class Eval(ABC):
    """Abstract class encapsulating code evaluation on microcontroller."""

    def __init__(self, device):
        self._device = device

    @property
    def device(self):
        return self._device

    @abstractmethod
    def exec(self, code: str, data_consumer=None) -> bytes:
        """Exec code on remote (Micro)Python VM.
        If data_consumer is not None, output (from print statements) is
        passed to it as it becomes available.
        Otherwise, output is collected and returned as as bytes.
        """

    @abstractmethod
    def abort(self) -> None:
        """Abort currently running program without resetting the MicroPython VM"""

    @abstractmethod
    def softreset(self) -> None:
        """Reset MicroPython VM."""
