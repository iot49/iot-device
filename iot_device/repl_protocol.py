from .eval import RemoteError, Output, OutputHelper
from .eval_rsync import EvalRsync
from .config_store import Config

from contextlib import contextmanager
from serial import SerialException
import inspect, os, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


MCU_RAW_REPL      = b'\x01'    # ctrl-A enter raw repl
MCU_FRIENDLY_REPL = b'\x02'    # ctrl-B enter friendly repl
MCU_ABORT         = b'\x03'    # ctrl-C abort
MCU_RESET         = b'\x04'    # ctrl-D softreset
MCU_EVAL          = b'\r\x04'  # start evaluation (raw repl)
EOT               = b'\x04'
CR                = b'\r'


class ReplProtocol(EvalRsync):
    """Concrete class of Eval (implements exec)"""

    def __init__(self, device):
        super().__init__(device)

    def exec(self, code, output:Output=None):
        if isinstance(code, str):
            code = code.encode()
        try:
            # ctrl-C twice: interrupt any running program
            self.device.write(b"\r\x03\x03")
            self.device.flush_input()
            # enter raw repl
            self.device.write(b"\r\x01")
            self.device.read_until(b'raw REPL; CTRL-B to exit\r\n>')
            # send code & start evaluation
            self.device.write(code)
            self.device.write(b'\x04')

            # read response
            if not output:
                output = OutputHelper()
                self._read_response(output)
                if len(output.err_):
                    raise RemoteError(output.err_.decode())
                return output.ans_
            else:
                self._read_response(output)
        except OSError:
            raise RemoteError("Device disconnected")

    def softreset(self):
        """Reset MicroPython VM via repl"""
        try:
            self.device.write(MCU_ABORT)
            self.device.write(MCU_RESET)
            self.device.write(CR)
            # Not sure this should be here. Device boot time?
            time.sleep(0.5)
        except Exception as e:
            logger.exception("softreset: {e}")
            raise RemoteError(e)

    def abort(self):
        """Abort MicroPython program execution"""
        try:
            self.device.write(MCU_ABORT)
            time.sleep(0.5)
        except Exception as e:
            logger.exception("abort: {e}")
            raise RemoteError(e)

    def _read_response(self, output):
        # process result, format "OK _answer_ EOT _error_message_ EOT>"
        self.device.read_until(b'OK')
        while True:
            ans = self.device.read()
            if not len(ans):
                time.sleep(0.1)
                continue
            ans = ans.split(EOT)
            if len(ans[0]): output.ans(ans[0])
            if len(ans) > 1:      # 1st EOT
                if len(ans[1]): output.err(ans[1])
                if len(ans) > 2:  # 2nd EOT
                    return
                break             # look for 2nd EOT below
        while True:
            ans = self.device.read().split(EOT)
            if len(ans[0]): output.err(ans[0])
            if len(ans) > 1:      # 2nd EOT
                return
