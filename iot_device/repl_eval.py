from .eval import Eval, DeviceError
from .config_store import Config

from contextlib import contextmanager
from serial import SerialException
import inspect, os, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


MCU_RAW_REPL      = b'\x01'    # enter raw repl
MCU_ABORT         = b'\x03'    # abort
MCU_RESET         = b'\x04'    # reset
MCU_EVAL          = b'\r\x04'  # start evaluation (raw repl)
EOT               = b'\x04'
CR                = b'\r'


class ReplEval(Eval):

    def __init__(self, *args, **kwargs):
        super(ReplEval, self).__init__(*args, **kwargs)

    def eval(self, code, output=None):
        try:
            if output:
                self.__exec_part_1(code)
                self.__exec_part_2(output)
            else:
                ans_ = bytearray()
                err_ = bytearray()
                class Output:
                    def ans(self, val):  
                        nonlocal ans_
                        ans_ += val
                    def err(self, val):  
                        nonlocal err_
                        err_ += val

                output = Output()
                self.__exec_part_1(code)
                self.__exec_part_2(output)
                if len(err_):
                    raise DeviceError(err_.decode())
                return ans_
        except OSError:
            raise DeviceError("Device disconnected")

    def softreset(self):
        """Reset MicroPython VM"""
        try:
            self.device.write(MCU_ABORT)
            self.device.write(MCU_RESET)
            self.device.write(CR)
            self.device.read_until(b'raw REPL; CTRL-B to exit\r\n>')
            logger.debug("VM reset")
        except Exception as e:
            logger.debug("Exception in softreset")
            raise DeviceError(e)


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
            raise DeviceError(f"Expected OK, got {res} when evaluating '{code}'")

    def __exec_part_2(self, output):
        if output:
            logger.debug(f"_exec_part_2 ...")
            while True:
                ans = self.device.read_all().split(EOT)
                if len(ans[0]): output.ans(ans[0])
                if len(ans) > 1:      # 1st EOT
                    if len(ans[1]): output.err(ans[1])
                    if len(ans) > 2:  # 2nd EOT
                        return
                    break             # look for 2nd EOT below
            # read error message, if any
            while True:
                ans = self.device.read_all().split(EOT)
                if len(ans[0]): output.err(ans[0])
                if len(ans) > 1:      # 2nd EOT
                    break
        else:
            result = bytearray()
            while True:
                result.extend(self.device.read_all())
                if result.count(EOT) > 1:
                    break
            s = result.split(EOT)
            logger.debug(f"repl s={s}")
            if len(s[1]) > 0:
                # s[1] is exception
                logger.debug(f"_exec_part_2 s={s} s[1]={s[1]}")
                raise DeviceError(s[1].decode())
            return s[0]
