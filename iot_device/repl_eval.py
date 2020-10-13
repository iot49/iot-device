from .eval import Eval, EvalException
from .config_store import Config

from contextlib import contextmanager
from serial import SerialException
import inspect, os, time, logging

logger = logging.getLogger(__file__)

MCU_RAW_REPL      = b'\x01'    # enter raw repl
MCU_ABORT         = b'\x03'    # abort
MCU_RESET         = b'\x04'    # reset
MCU_EVAL          = b'\r\x04'  # start evaluation (raw repl)
EOT               = b'\x04'


class ReplEval(Eval):

    def __init__(self, *args, **kwargs):
        super(ReplEval, self).__init__(*args, **kwargs)

    def eval(self, code, output=None):
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
                raise EvalException(err_.decode())
            return ans_

    def softreset(self):
        """Reset MicroPython VM"""
        try:
            self.device.write(MCU_ABORT)
            self.device.write(MCU_RESET)
            self.device.write(b'\n')
            self.device.read_until(b'raw REPL; CTRL-B to exit\r\n>', timeout=0.5)
            logger.debug("VM reset")
        except Exception as e:
            logger.debug("Exception in softreset")
            raise EvalException(e)


    def __exec_part_1(self, code):
        if isinstance(code, str):
            code = code.encode()
        # logger.debug(f"EVAL {code.decode()}")
        self.device.write(MCU_ABORT)
        self.device.write(MCU_ABORT)
        self.device.write(MCU_RAW_REPL)
        self.device.read_until(b'raw REPL; CTRL-B to exit\r\n>', timeout=0.5)
        self.device.write(code)
        self.device.write(MCU_EVAL)
        # process result of format "OK _answer_ EOT _error_message_ EOT>"
        if self.device.read(2) != b'OK':
            raise EvalException(f"Cannot eval '{code}'")

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
                raise EvalException(s[1].decode())
            return s[0]
