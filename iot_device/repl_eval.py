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

# esp32 cannot handle more than 255 bytes per transfer
# not sure why ...
# what's the performance penalty on nrf52?
BUFFER_SIZE = 254 # 2048


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

    def fget(self, mcu_file, host_file):
        filesize = self.file_size(mcu_file)
        if filesize < 0:
            return False
        return self.__eval_func(_mcu_read, mcu_file, host_file, filesize, xfer_func=_host_write)

    def fput(self, host_file, mcu_file):
        # upload file to MCU
        if os.path.isdir(host_file):
            # Copy files only, not directories
            return False
        with open(host_file, 'rb') as f:
            # Check if it's a binary file that could upset REPL (ctrl-C, ...)
            include = [ord(x) for x in '\a\b\f\n\t\v']
            exclude = bytes([ x for x in range(32) if not x in include ])
            binary = any([x in exclude for x in f.read()])
        filesize = os.path.getsize(host_file)
        self.makedirs(os.path.dirname(mcu_file))
        res = self.__eval_func(_mcu_write, host_file, mcu_file, filesize, binary, xfer_func=_host_read)
        return res

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

    def __eval_func(self, func, *args, xfer_func=None, output=None, **kwargs):
        """Call func(*args, **kwargs) on (Micro)Python board."""
        try:
            args_arr = [repr(i) for i in args]
            kwargs_arr = ["{}={}".format(k, repr(v)) for k, v in kwargs.items()]
            func_str = inspect.getsource(func).replace('BUFFER_SIZE', str(BUFFER_SIZE))
            func_str += 'import os\n'
            func_str += 'os.chdir("/")\n'
            func_str += 'output = ' + func.__name__ + '('
            func_str += ', '.join(args_arr + kwargs_arr)
            func_str += ')\n'
            func_str += 'if output != None: print(output)\n'
            # logger.debug(f"eval_func: {func_str}")
            start_time = time.monotonic()
            self.__exec_part_1(func_str)
            if xfer_func:
                xfer_func(self.device, *args, **kwargs)
                logger.debug(f"returned from xfer_func")
            output = self.__exec_part_2(output)
            logger.debug("eval_func: {}({}) --> {},   in {:.3} s)".format(
                func.__name__,
                repr(args)[1:-1],
                output,
                time.monotonic()-start_time))
            if output:
                try:
                    output = output.decode().strip()
                except UnicodeDecodeError:
                    pass
            return output
        except SyntaxError as se:
            logger.error(f"Syntax {se}")


##########################################################################
# Code running on MCU for fput, fget

def _mcu_write(host_file, mcu_file, filesize, binary):
    # receives file from host and writes to flash as `filename`
    import sys
    try:
        if binary:
            import binascii
        with open(mcu_file, 'wb') as dst_file:
            bytes_remaining = filesize
            if binary: bytes_remaining *= 2    # hexlify doubles size
            write_buf = bytearray(BUFFER_SIZE)
            read_buf  = bytearray(BUFFER_SIZE)
            while bytes_remaining > 0:
                read_size = min(bytes_remaining, BUFFER_SIZE)
                buf_remaining = read_size
                buf_index = 0
                while buf_remaining > 0:
                    bytes_read = sys.stdin.readinto(read_buf, bytes_remaining)  # pylint: disable=no-member
                    if bytes_read > 0:
                        write_buf[buf_index:bytes_read] = read_buf[0:bytes_read]
                        buf_index += bytes_read
                        buf_remaining -= bytes_read
                dst_file.write(binascii.unhexlify(write_buf[0:read_size]) if binary else write_buf[0:read_size])
                # Send back an ack as a form of flow control
                sys.stdout.write(b'\x06')
                bytes_remaining -= read_size
    except:
        # signal error (anything but b'\x06')
        sys.stdout.write(b'\x07')
        raise

def _host_read(device, host_file, mcu_file, filesize, binary):
    # reads file from host and sends to MCU
    # pass to `ReplOps.eval_func` as the xfer_func argument
    # matches up with mcu_write
    host_dir = os.path.expanduser(Config.get('host_dir'))
    src_file_name = os.path.join(host_dir, host_file)
    buf_size = BUFFER_SIZE // 2 if binary else BUFFER_SIZE
    with open(src_file_name, 'rb') as src_file:
        bytes_remaining = filesize
        while bytes_remaining > 0:
            read_size = min(bytes_remaining, buf_size)
            buf = src_file.read(read_size)
            if binary:
                buf = binascii.hexlify(buf)
            device.write(buf)
            # Wait for ack so we don't get too far ahead of the remote
            ack = device.read(1)
            if ack != b'\x06':
                logger.error(f"got {ack}, expected b'\\x06'")
                return False
            bytes_remaining -= read_size
    return True
    
def _mcu_read(mcu_file, host_file, filesize):
    # reads file from flash and sends to host
    import sys
    with open(mcu_file, 'rb') as src_file:
        bytes_remaining = filesize
        while bytes_remaining > 0:
            read_size = min(bytes_remaining, BUFFER_SIZE)
            buf = src_file.read(read_size)
            # buffer is necessary!
            # But not available on samd51
            sys.stdout.buffer.write(buf)
            bytes_remaining -= read_size
            # Wait for an ack so we don't get ahead of the remote
            ack = sys.stdin.read(1)
            if ack != '\x06':
                raise ValueError("Expected '\\x06', got '{}'".format(ord(ack)))

def _host_write(device, mcu_file, host_file, filesize):
    # receives file from MCU and saves on host
    # pass to `ReplOps.eval_func` as the xfer_func argument
    # matches up with mcu_read
    host_dir = os.path.expanduser(Config.get('host_dir'))
    dst_file_name = os.path.join(host_dir, host_file)
    with open(dst_file_name, 'wb') as dst_file:
        bytes_remaining = filesize
        write_buf = bytearray(BUFFER_SIZE)
        while bytes_remaining > 0:
            read_size = min(bytes_remaining, BUFFER_SIZE)
            buf_remaining = read_size
            buf_index = 0
            while buf_remaining > 0:
                read_buf = device.read(buf_remaining)
                bytes_read = len(read_buf)
                if bytes_read:
                    write_buf[buf_index:bytes_read] = read_buf[0:bytes_read]
                    buf_index += bytes_read
                    buf_remaining -= bytes_read
            dst_file.write((write_buf[0:read_size]))
            # Send an ack to the remote as a form of flow control
            device.write(b'\x06')   # ASCII ACK is 0x06
            bytes_remaining -= read_size


##########################################################################
# Code running on MCU

def _uid():
    try:
        import machine   # pylint: disable=import-error
        _id = machine.unique_id()
    except:
        try:
            import microcontroller   # pylint: disable=import-error
            _id = microcontroller.cpu.uid
        except:
            return None
    return ":".join("{:02x}".format(x) for x in _id)

