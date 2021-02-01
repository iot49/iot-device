from .device import Device
from .eval import RemoteError
from .config_store import Config
from .mp_protocol import MpProtocol

import os, socket, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

VERSION = 'ns-V1'

class PasswordError(Exception):
    pass

class MpDevice(Device):

    def __init__(self, url):
        super().__init__(url)

    def read(self, size=2048):
        # timeout set in __enter__
        try:
            return self._socket.recv(size)
        except socket.timeout:
            return b''

    def readline(self, timeout=1):
        """Not blocking: incomplete 'line' may be returned."""
        res = b''
        start = time.monotonic()
        # let's give the MCU some time ...
        while (time.monotonic() - start) < timeout:
            b = self.read(1)
            if b == b'\n': return res.decode()
            res += b
        return res.decode()

    def write(self, data):
        self._socket.sendall(data)

    def writeline(self, data):
        self.write(data)
        self.write(b'\n')

    def __enter__(self):
        self._connect()
        return MpProtocol(self)

    def __exit__(self, typ, value, traceback):
        self.writeline(b'bye')
        try:
            self._socket.close()
        except:
            pass
        self._socket = None

    def _connect(self):
        try:
            ip, port = self.address.split(':')
        except ValueError:
            raise RemoteError(f"Not a valid address: {self.address}")
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(1)
        try:
            self._socket.connect((ip, int(port)))
        except (socket.gaierror, OSError):
            print(f"mpdev cannot access {self.url}")
            raise RemoteError(f"Cannot access {self.url}")
        self._socket.settimeout(0.1)
        version = self.readline()
        if version == '':
            raise RemoteError(f"No answer from {self.url}")
        if version != VERSION:
            raise RemoteError(f"Version mismatch: got '{version}', expected '{VERSION}' for {url}")
        self.writeline(Config.get_secret('password', '').encode())
        ok = self.readline()
        if ok != 'OK':
            raise RemoteError(f"{ok} ({url})")
