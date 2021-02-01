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

    def exec(self, code, output:Output=None, *, no_response=False):
        # enter raw repl (we don't make any assumption about state of device)
        self._enter_raw_repl()
        # send code & start evaluation
        if isinstance(code, str):
            code = code.encode()
        self.device.write(code)
        self.device.write(b'\x04')
        # read output
        if no_response: return
        if not output:
            output = OutputHelper()
            self._read_response(output)
            if len(output.err_):
                raise RemoteError(f"*** Error in exec: {output.err_.decode()}")
            return output.ans_
        else:
            self._read_response(output)

    def _enter_raw_repl(self):
        # if the device just got online, it may not respond yet ...
        # keep trying, as long as we get some response ...
        start = time.monotonic()
        while (time.monotonic()-start) < 5:
            try:
                # ctrl-C twice: interrupt any running program
                self.device.write(b"\r\x03\x03")
                # enter raw repl
                self.device.write(b"\r\x01")
                self.device.read_until(b'raw REPL; CTRL-B to exit\r\n>', timeout=0.5)
                break
            except TimeoutError as e:
                # no response, give up
                logger.debug(f"enter_raw_repl: {e}")
                # raise RemoteError(e)
            except RemoteError as e:
                # got a response, just not the expected one; keep trying
                print(f"{e} from {self.device.url} while trying to enter raw repl")
                logger.debug(f"Unexpected response {e} from {self.device.url} while trying to enter raw repl")
            except OSError:
                raise RemoteError("Device disconnected")

    def softreset(self):
        """Reset MicroPython VM via repl"""
        try:
            device = self.device
            device.write(MCU_ABORT)
            device.write(MCU_RESET)
            device.write(CR)
            device.read_until(b'raw REPL; CTRL-B to exit\r\n>', 5)
        except Exception as e:
            logger.exception(f"softreset: {e}")
            raise RemoteError(f"*** Error in softreset: {e}")

    def abort(self):
        """Abort MicroPython program execution"""
        try:
            self.device.write(MCU_ABORT)
            self.device.read_until(b'KeyboardInterrupt: \r\n\x04>', 3)
        except Exception as e:
            logger.exception("abort: {e}")
            raise RemoteError(f"*** abort: {e}")

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
