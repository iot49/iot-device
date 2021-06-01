from .device import Device
from .eval import RemoteError
from .secrets import Secrets
from .mp_protocol import MpProtocol

import os, socket, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

VERSION = 'ns-V1'

class PasswordError(Exception):
    pass

class MpDevice(Device):

    def __init__(self, url):
        super().__init__(url)

    def __enter__(self):
        assert self.scheme == "mp"
        addr, port = self.address.split(':')
        self.sock = s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger.debug(f"connect ({addr}, {port})")
        s.settimeout(1)
        s.connect((addr, int(port)))
        version = self.readline()
        logger.debug(f"version {version}")
        if version == '': raise RemoteError(f"Device is offline")
        if version != VERSION: raise RemoteError(f"Wrong mp version: client={repr(VERSION)}, server={repr(version)}")
        s.sendall(Secrets.get_attr("mp_pwd", "?").encode())
        s.sendall(b'\n')
        ok = self.readline()
        logger.debug(f"ok = {ok}")
        if ok != 'OK': raise RemoteError(f"Expected OK, got {ok}")
        return MpProtocol(self)

    def __exit__(self, typ, value, traceback):
        self.sock.sendall(b'bye\n')
        try:
            self.sock.close()
        except:
            pass
        self.sock = None

    def readline(self, timeout=1):
        """Blocking"""
        res = b''
        start = time.monotonic()
        # let's give the MCU some time ...
        while (time.monotonic() - start) < timeout:
            try:
                b = self.sock.recv(1)
            except socket.timeout:
                time.sleep(0.1)
                continue
            if b == b'':
                raise Exception("connection closed")
            if b == b'\n':
                return res.decode()
            res += b
        return res.decode()

    def read(self, size):
        raise RuntimeError("MpDevice read()")

    def write(self, data):
        raise RuntimeError("MpDevice write()")

    def inWaiting(self):
        raise RuntimeError("MpDevice inWaiting()")
