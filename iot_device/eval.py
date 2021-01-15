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

    @property
    def traceback(self):
        return self.args[0]

    @property
    def msg(self):
        try:
            return self.args[0].strip().split('\n')[-1]
        except:
            return self.args[0]



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
    def exec(self, code: str, output:Output=None) -> bytes:
        """Exec code on remote (Micro)Python VM.

        If output is None, evaluation results are returned from the function
        or a ReplExeption is raised in case of an error.

        Otherwise, output and errors are forwarded to the handler as they
        are received from the remote microcontroller.
        Used by interactive interfaces.

        Runs until code execution terminates or a KeyboardInterrupt is received.
        In the latter case, call abort to also terminate the program on the microcontroller.
        """
        pass

    @abstractmethod
    def eval_exec(self, code: str, output:Output=None) -> None:
        """Try eval, then exec if the former fails"""

    @abstractmethod
    def softreset(self) -> None:
        """Reset MicroPython VM"""

    @abstractmethod
    def abort(self) -> None:
        """Abort currently running program without resetting the MicroPython VM"""
