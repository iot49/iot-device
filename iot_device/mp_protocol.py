from .eval import Output, OutputHelper, RemoteError
from .eval_rsync import EvalRsync
import os, struct, time


EOT = b'\x04'

class MpProtocol(EvalRsync):

    def __init__(self, device):
        super().__init__(device)

    # implement abstract Exec
    def exec(self, code, output:Output=None, *, no_response=False):
        if len(code) == 0: return
        print("MpProtocol.exec", code)
        if isinstance(code, str): code = code.encode()
        device = self.device
        device.writeline(b'evex')
        device.writeline(str(len(code)).encode())
        device.write(code)
        print("read ok ...")
        ok = device.readline()
        print("ok", ok)
        if ok != 'OK': raise RemoteError(ok)
        # read response
        if no_response: return
        if output == None:
            output = OutputHelper()
            self._read_response(output)
            if len(output.err_):
                raise RemoteError(output.err_.decode())
            return output.ans_
        else:
            self._read_response(output)

    def _read_response(self, output):
        device = self.device
        while True:
            ans = device.read()
            if len(ans) == 0:
                continue
            ans = ans.split(EOT)
            if len(ans[0]): output.ans(ans[0])
            if len(ans) > 1:      # 1st EOT
                if len(ans[1]): output.err(ans[1])
                if len(ans) > 2:  # 2nd EOT
                    return
                break             # look for 2nd EOT below
        while True:
            ans = device.read().split(EOT)
            if len(ans[0]): output.err(ans[0])
            if len(ans) > 1:      # 2nd EOT
                return

    def softreset(self):
        # programmatic reset
        self.exec(_softreset)

    def abort(self):
        # abort program execution - now sure how to do this?
        # perhaps disconnecting? interrupt?
        # BIG problem
        pass

    # override ExecFileOps
    def fget(self, src, dst, chunk_size=-1):
        # client: send path
        # server: send OK or error
        # server: send file size
        # server: send file contents
        device = self.device
        device.writeline(b'fget')
        device.writeline(src.encode())
        ok = device.readline()
        if ok != 'OK': raise RemoteError(ok)
        sz = int(device.readline())
        n = 0
        with open(dst, 'wb') as f:
            n = 0
            while n < sz:
                b = device.read(min(1024, sz-n))
                f.write(b)
                n += len(b)

    # override ExecFileOps
    def fput(self, src, dst, chunk_size=1024):
        # client: send path
        # client: send file size
        # client: send file content
        # server: send OK or error
        device = self.device
        device.writeline(b"fput")
        device.writeline(dst.encode())
        device.writeline(str(os.path.getsize(src)).encode())
        with open(src, 'rb') as f:
            device.write(f.read())
        ok = device.readline()
        if ok != 'OK': raise RemoteError(ok)


_softreset = """\
try:
    import microcontroller
    microcontroller.reset()
except ImportError:
    import machine
    machine.reset()
"""
