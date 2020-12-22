from .remote_exec import RemoteExec, RemoteError
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


class OutputHelper:
    def __init__(self):
        self.ans_ = bytearray()
        self.err_ = bytearray()
    def ans(self, val):
        self.ans_ += val
    def err(self, val):
        self.err_ += val

class RemoteRepl(RemoteExec):
    """Concrete class of RemoteExec"""

    def exec(self, code, output=None, timeout=None):
        try:
            self.__exec_part_1(code)
            if not output:
                output = OutputHelper()
            self.__exec_part_2(output, timeout)
            if isinstance(output, OutputHelper):
                if len(output.err_):
                    raise RemoteError(output.err_.decode())
                return output.ans_
        except OSError:
            raise RemoteError("Device disconnected")

    # superseded by machine.reset()
    def repl_reset(self):
        """Reset MicroPython VM via repl"""
        try:
            self.device.write(MCU_ABORT)
            self.device.write(MCU_RESET)
            self.device.write(CR)
            # SKIP ?: device may be disconnected after reset and
            #         take some time to reconnect
            self.device.read_until(b'raw REPL; CTRL-B to exit\r\n>')
            logger.debug("VM reset")
        except Exception as e:
            logger.debug("Exception in softreset")
            logger.exception("softreset: {e}")
            raise RemoteError(e)

    def __exec_part_1(self, code):
        if isinstance(code, str):
            code = code.encode()

        # ctrl-C twice: interrupt any running program
        self.device.write(b"\r\x03\x03")
        self.device.flush_input()

        # enter raw repl
        self.device.write(b"\r\x01")
        self.device.read_until(b'raw REPL; CTRL-B to exit\r\n>')

        # send code & start evaluation
        for i in range(0, len(code), 256):
            self.device.write(code[i : min(i + 256, len(code))])
            time.sleep(0.01)
        self.device.write(b'\x04')

        # process result, format "OK _answer_ EOT _error_message_ EOT>"
        res = self.device.read(2)
        if res != b'OK':
            raise RemoteError(f"Expected OK, got {res} when evaluating '{code}'")

    def __exec_part_2(self, output, timeout=None):
        stop = time.monotonic() + (timeout if timeout else 1e20)
        if output:
            logger.debug(f"_exec_part_2 ...")
            while time.monotonic() < stop:
                ans = self.device.read_all().split(EOT)
                if len(ans[0]): output.ans(ans[0])
                if len(ans) > 1:      # 1st EOT
                    if len(ans[1]): output.err(ans[1])
                    if len(ans) > 2:  # 2nd EOT
                        return
                    break             # look for 2nd EOT below
            # read error message, if any
            while time.monotonic() < stop:
                ans = self.device.read_all().split(EOT)
                if len(ans[0]): output.err(ans[0])
                if len(ans) > 1:      # 2nd EOT
                    break
        else:
            result = bytearray()
            while time.monotonic() < stop:
                result.extend(self.device.read_all())
                if result.count(EOT) > 1:
                    break
            s = result.split(EOT)
            logger.debug(f"repl s={s}")
            if len(s[1]) > 0:
                # s[1] is exception
                logger.debug(f"_exec_part_2 s={s} s[1]={s[1]}")
                raise RemoteError(s[1].decode())
            return s[0]
