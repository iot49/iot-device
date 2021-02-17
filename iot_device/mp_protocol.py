from .eval import RemoteError
from .eval_rsync import EvalRsync
import socket, os, struct, time


EOT = b'\x04'

class MpProtocol(EvalRsync):

    def __init__(self, device):
        assert device.scheme == "mp"
        super().__init__(device)

    # implement abstract exec
    def exec(self, code: str, data_consumer=None) -> bytes:
        if len(code) == 0: return
        if isinstance(code, str): code = code.encode()
        self.sendall(b'evex\n')
        self.sendall(str(len(code)).encode())
        self.sendall(b'\n')
        self.sendall(code)
        # compilation may take a long time!
        ok = self.readline(60)
        if ok != 'OK': raise RemoteError(f"eval: expected OK, got {ok}")
        # read result
        res = self.read_until_eot(data_consumer)
        err = self.read_until_eot(None)
        if len(err) > 0:
            raise RemoteError("", res, err)
        return res

    def fget(self, src, dst, chunk_size=-1):
        self.sendall(b'fget\n')
        self.sendall(src.encode())
        self.sendall(b'\n')
        ok = self.readline()
        if ok != 'OK': raise RemoteError(f"fget: expected OK, got {ok}")
        sz = int(self.readline())
        n = 0
        with open(dst, 'wb') as f:
            n = 0
            while n < sz:
                b = self.recv(min(1024, sz-n))
                f.write(b)
                n += len(b)

    # override ExecFileOps
    def fput(self, src, dst):
        sz = os.path.getsize(src)
        self.sendall(b"fput\n")
        self.sendall(dst.encode())
        self.sendall(b'\n')
        self.sendall(str(sz).encode())
        self.sendall(b'\n')
        with open(src, 'rb') as f:
            self.sendall(f.read())
        ok = self.readline(timeout=10)
        if ok != 'OK': raise RemoteError(f"fput: expected OK, got {ok}")

    def softreset(self):
        raise RemoteError("softreset not implemented for 'mp' protocol")
        # programmatic reset
        # self.exec(_softreset)

    def abort(self):
        # abort program execution - now sure how to do this?
        # perhaps disconnecting? interrupt?
        pass

    def recv(self, sz=1):
        return self.device.sock.recv(sz)

    def sendall(self, data):
        return self.device.sock.sendall(data)

    def readline(self, timeout=1):
        return self.device.readline(timeout)

    def read_until_eot(self, data_consumer):
        res = b""
        while True:
            try:
                b = self.recv(1)
            except socket.timeout:
                # print("MpProtocol.read_until_eof timed out! (ignored)")
                b = b""
            if b == EOT: return res
            if data_consumer: data_consumer(b)
            res += b



_softreset = """\
try:
    import microcontroller
    microcontroller.reset()
except ImportError:
    import machine
    machine.soft_reset()
"""
