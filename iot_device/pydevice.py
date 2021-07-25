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
        #        kernel print is very slow on Pi
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

    def enter_raw_repl(self, soft_reset):
        # patch: soft_reset is mandatory
        super().enter_raw_repl(soft_reset)

    def exec(self, command, data_consumer=None):
        ret, ret_err = self.exec_raw(command, data_consumer=data_consumer)
        if ret_err:
            raise PyboardError(ret_err.decode())
        return ret

    def softreset(self):
        self.enter_raw_repl(soft_reset=True)
        self.exit_raw_repl()
