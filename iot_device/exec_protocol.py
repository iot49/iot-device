from .eval import Output, OutputHelper, RemoteError
from .eval_rsync import EvalRsync
import socket, os, struct, time


EOT = b'\x04'

class OutputHelper(Output):
    def __init__(self):
        self.ans_ = bytearray()
        self.err_ = bytearray()
    def ans(self, val):
        self.ans_ += val
    def err(self, val):
        self.err_ += val

    def exec(self, code, output:Output=None, timeout=None):
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

class ExecProtocol(EvalRsync):

    def __init__(self, device):
        super().__init__(device)

    # implement abstract Exec
    def exec(self, code, output:Output=None, timeout=None):
        return self._remote_eval("exec", code, output, timeout)

    # override ExecDefaults
    def eval_exec(self, code, output:Output=None, timeout=None):
        return self._remote_eval("eval", code, output, timeout)

    def _remote_eval(self, instruction, code, output, timeout):
        if not timeout: timeout = 1e20
        if not output: output = OutputHelper()
        self.device.write(f"{instruction}\x04{len(code)}\n".encode())
        self.device.write(code.encode())
        self._read_response(output, timeout)
        if isinstance(output, OutputHelper):
            if len(output.err_):
                raise RemoteError(output.err_.decode())
            return output.ans_

    def _read_response(self, output, timeout):
        # process response, format "OK _answer_ EOT _error_message_ EOT>"
        assert self.device.read(2) == b'OK'
        max_time = time.monotonic() + timeout
        while True:
            ans = self.device.read_all().split(EOT)
            if len(ans[0]): output.ans(ans[0])
            if len(ans) > 1:      # 1st EOT
                if len(ans[1]): output.err(ans[1])
                if len(ans) > 2:  # 2nd EOT
                    return
                break             # look for 2nd EOT below
            if time.monotonic() > max_time:
                raise(RemoteError("Timeout waiting for response"))
        # read error message, if any
        while True:
            ans = self.device.read_all().split(EOT)
            if len(ans[0]): output.err(ans[0])
            if len(ans) > 1:      # 2nd EOT
                break
            if time.monotonic() > max_time:
                raise(RemoteError("Timeout waiting for exception"))

    # override ExecFileOps
    def fget(self, src, dst, chunk_size=1024):
        self.device.write(f"fget\x04{src}\n".encode())
        size = struct.unpack('!I', self.device.read(4))[0]
        with open(dst, 'wb') as f:
            while size > 0:
                data = self.device.read(min(chunk_size, size))
                f.write(data)
                size -= len(data)

    # override ExecFileOps
    def fput(self, src, dst, chunk_size=1024):
        self.disable_write_protection()
        sz = os.path.getsize(src)
        self.device.write(f"fput\x04{dst}\x04{sz}\n".encode())
        with open(src, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data: break
                self.device.write(data)
