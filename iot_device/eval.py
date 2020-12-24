from abc import ABC, abstractmethod
import os, inspect, logging, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class RemoteError(Exception):
    def __init__(self, msg):
        if isinstance(msg, bytes):
            try:
                msg = msg.decode()
            except UnicodeDecodeError:
                pass
        super().__init__(msg)


class Output(ABC):
    """Callbacks for remote code evaluation"""
    def ans(self, val:bytes):
        pass
    def err(self, val:bytes):
        pass


class OutputHelper(Output):
    def __init__(self):
        self.ans_ = bytearray()
        self.err_ = bytearray()
    def ans(self, val):
        self.ans_ += val
    def err(self, val):
        self.err_ += val


class Eval(ABC):
    """Abstract class encapsulating code evaluation on microcontroller."""

    def __init__(self, device):
        self._device = device

    @property
    def device(self):
        return self._device

    @abstractmethod
    def exec(self, code: str, output:Output=None, timeout=None) -> bytes:
        """Exec code on remote (Micro)Python VM.

        If output is None, evaluation results are returned from the function
        or a ReplExeption is raised in case of an error.

        Otherwise, output and errors are forwarded to the handler as they
        are received from the remote microcontroller.
        Used by interactive interfaces.
        """
        pass

    @abstractmethod
    def eval_exec(self, code: str, output:Output=None, timeout=None) -> None:
        """Try eval, then exec if the former fails"""

    @abstractmethod
    def softreset(self, output:Output=None, timeout=5) -> None:
        """Reset micropython VM"""
