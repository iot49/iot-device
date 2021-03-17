from .pyboard import Pyboard, PyboardError

import logging, time, os

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

RAW_REPL_MSG = b"raw REPL; CTRL-B to exit\r\n"

MCU_RAW_REPL      = b'\x01'    # ctrl-A enter raw repl
MCU_FRIENDLY_REPL = b'\x02'    # ctrl-B enter friendly repl
MCU_ABORT         = b'\x03'    # ctrl-C abort
MCU_RESET         = b'\x04'    # ctrl-D softreset
MCU_EVAL          = b'\r\x04'  # start evaluation (raw repl)
EOT               = b'\x04'
CR                = b'\r'


class Pydevice(Pyboard):

    def __init__(self, device):
        """Pyboard with a different initializer."""
        if not hasattr(device, 'use_raw_paste'):
            device.use_raw_paste = True
        self.use_raw_paste = device.use_raw_paste
        self.serial = device

    def read_until(self, min_num_bytes, ending, timeout=10, data_consumer=None):
        # patch: don't call data_consumer on single chars (if more data is available)
        #        kernal print is very slow on Pi
        # if data_consumer is used then data is not accumulated and the ending must be 1 byte long
        assert data_consumer is None or len(ending) == 1
        data = self.serial.read(min_num_bytes)
        timeout_count = 0
        while True:
            if data.endswith(ending):
                if data_consumer:
                    data_consumer(data)
                break
            if self.serial.inWaiting() > 0:
                new_data = self.serial.read(1)
                data = data + new_data
                timeout_count = 0
            else:
                if data_consumer and len(data) > 0:
                    data_consumer(data)
                    data = b''
                timeout_count += 1
                if timeout is not None and timeout_count >= 100 * timeout:
                    break
                time.sleep(0.01)
        return data

    def enter_raw_repl(self):
        self.serial.write(b"\r\x03\x03")  # ctrl-C twice: interrupt any running program

        # flush input (without relying on serial.flushInput())
        n = self.serial.inWaiting()
        while n > 0:
            self.serial.read(n)
            n = self.serial.inWaiting()

        self.serial.write(b"\r\x01")  # ctrl-A: enter raw REPL
        data = self.read_until(1, RAW_REPL_MSG)
        if not data.endswith(RAW_REPL_MSG):
            print(data)
            raise PyboardError(f"could not enter raw repl:\n  expected '{RAW_REPL_MSG}'\n  got '{data}'")

    def exec(self, command, data_consumer=None):
        self.exec_raw_no_follow(command)
        ret, ret_err = self.follow(timeout=None, data_consumer=data_consumer)
        if ret_err:
            raise PyboardError("exception", ret, ret_err)
        return ret

    def softreset(self):
        device = self.serial
        device.write(MCU_ABORT)
        device.write(MCU_RESET)
        device.write(CR)
        data = self.read_until(1, RAW_REPL_MSG)
        if not data.endswith(RAW_REPL_MSG):
            raise PyboardError(f"could not reset board:\n  expected '{RAW_REPL_MSG}'\n  got '{data}'")
