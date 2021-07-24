from abc import ABC, abstractmethod
import os, inspect, logging, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class RemoteError(Exception):
    pass


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
