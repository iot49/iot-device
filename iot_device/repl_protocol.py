from .eval import RemoteError
from .eval_rsync import EvalRsync
from .config_store import Config
from .pyboard import PyboardError
from .pydevice import Pydevice
import logging, os

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class ReplProtocol(EvalRsync):
    """Concrete class of Eval (implements exec etc)"""

    def __init__(self, device):
        super().__init__(device)
        self.pyboard = Pydevice(device)
        self.pyboard.enter_raw_repl()

    def close(self):
        self.pyboard.exit_raw_repl()

    def exec(self, code: str, data_consumer=None) -> bytes:
        try:
            return self.pyboard.exec(code, data_consumer)
        except PyboardError as e:
            raise RemoteError(*e.args)

    def softreset(self) -> None:
        try:
            self.pyboard.softreset()
        except PyboardError as e:
            logger.exception(f"softreset: {e}")
            raise RemoteError(*e.args)

    def abort(self) -> None:
        try:
            # enter_raw_repl aborts running program (if any)
            self.pyboard.enter_raw_repl()
        except PyboardError as e:
            logger.exception("abort: {e}")
            raise RemoteError(*e.args)
