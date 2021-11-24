from .eval import RemoteError
from .eval_rsync import EvalRsync
from .pyboard import PyboardError
from .pydevice import Pydevice
from websocket import WebSocketException
import logging, os, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class ReplProtocol(EvalRsync):
    """Concrete class of Eval (implements exec etc)"""

    def __init__(self, device):
        super().__init__(device)
        self.pyboard = Pydevice(device)
        self.pyboard.enter_raw_repl(soft_reset=False)

    def close(self):
        # CircuitPython resets when exiting raw repl (ugh!)
        if self.device.implementation != 'circuitpython':
            self.pyboard.exit_raw_repl()

    def exec(self, code: str, *, data_consumer=None, timeout=None) -> bytes:
        try:
            res = self.pyboard.exec(code, data_consumer=data_consumer, timeout=timeout)
            # Don't try to use raw-paste mode again unless supported by this device
            self.device.use_raw_paste = self.pyboard.use_raw_paste
            return res
        except OSError as e:
            raise RemoteError("Device disconnected")
        except PyboardError as e:
            raise RemoteError(*e.args)

    def abort(self) -> None:
        self.pyboard.abort()

    def softreset(self) -> None:
        try:
            self.pyboard.softreset()
        except WebSocketException as e:
            # Connection is already closed
            # webrepl needs some time to restart
            time.sleep(3)
        except PyboardError as e:
            logger.exception(f"softreset: {e}")
            raise RemoteError(*e.args)

    def hardreset(self, printer, timeout) -> None:
        self.pyboard.hardreset(printer, timeout)