from abc import ABC, abstractmethod
import os, inspect, logging, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class RemoteError(Exception):
    pass


class Eval(ABC):
    """Abstract class encapsulating code evaluation on microcontroller."""

    def __init__(self, device):
        self._device = device

    @property
    def device(self):
        return self._device

    @property
    def implemention(self):
        return self._device.implementation

    @abstractmethod
    def exec(self, code: str, data_consumer=None, timeout=None) -> bytes:
        """Exec code on remote (Micro)Python VM.
        @param data_consumer if not None, output (from print statements) is
        passed to it as it becomes available.
        Otherwise, output is collected and returned as as bytes.
        @param timeout in seconds. None for infinite.
        """

    @abstractmethod
    def abort(self) -> None:
        """Abort currently running program without resetting the MicroPython VM.
        Variables and device assignments retained. boot.py and main.py not run.
        """

    @abstractmethod
    def softreset(self) -> None:
        """Abort currently running program and reset the MicroPython VM.
        Release all variables and devices. boot.py and main.py not run.
        """
    @abstractmethod
    def hardreset(self, printer, timeout) -> None:
        """Reset MicroPython VM & run boot.py, main.py. Same as pressing reset button.
        Prints output from boot.py or main.py.
        Follow by abort to stop "any" running program. 
        """

