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
    def exec(self, code: str, output=None, timeout=None) -> bytes:
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

    def eval_exec(self, code: str, output=None, timeout=None) -> None:
        """Try eval, then exec if the former fails"""
        self.exec(_eval_exec.format(repr(code)), output, timeout)

    def softreset(self, output, timeout=5):
        self.exec(_softreset, output=output, timeout=timeout)


###############################################################################
# code snippets (run on remote)

# NameError clause if for ports that don't support compile
# (CircuitPython)

_eval_exec = """
_iot49_ = {}
try:
    eval(compile(_iot49_, '<string>', 'single'))
except SyntaxError:
    exec(_iot49_)
except NameError:
    try:
        print(eval(_iot49_))
    except SyntaxError:
        exec(_iot49_)
finally:
    del _iot49_
"""


_softreset = """
try:
    import microcontroller
    microcontroller.reset()
except ImportError:
    import machine
    machine.reset()
"""
