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


class RemoteExec:
    """Abstract class encapsulating code evaluation on microcontroller.
    Implemented by RemoteRepl.
    """

    def __init__(self, device):
        self._device = device

    @property
    def device(self):
        return self._device

    @abstractmethod
    def exec(self, code: str, output=None) -> bytes:
        """Exec code on remote (Micro)Python VM.

        If output is None, evaluation results are returned from the function
        or a ReplExeption is raised in case of an error.

        Otherwise, output is a call-back handler class of the form

           class Output:
              def ans(value: bytes): pass
              def err(value: bytes): pass

        that receives results as they are sent from the microcontroller.
        Useful for interactive interfaces.
        """
        pass

    @abstractmethod
    def softreset(self):
        """Release all resources (variables and peripherals)"""
        pass
