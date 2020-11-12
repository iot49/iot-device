from .device import Device
from .config_store import Config

import os, socket, ssl, json, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class PasswordError(Exception):
    pass

class NetDevice(Device):

    def __init__(self, id, uid, address):
        self.__socket = None
        self.__address = address
        super().__init__(id=id, desc=f"net device {uid}", uid=uid)

    @property
    def address(self):
        return self.__address

    @property
    def connection(self):
        return 'net'
        
    def read(self, size=1):
        res = bytearray()
        while len(res) < size:
            try:
                b = self.__socket.recv(size-len(res))
            except ssl.SSLWantReadError as sre:
                logger.error(f"NetDevice.read, {sre}")
            if b:
                res.extend(b)
            else:
                raise ConnectionResetError(f"Connection to {self.uid} closed")
        return res

    def read_all(self):
        try:
            b = self.__socket.recv(1024)
        except ssl.SSLWantReadError as sre:
            logger.error(f"NetDevice.read_all, {sre}")        
        if b: 
            return b
        else:
            raise ConnectionResetError(f"Connection to {self.uid} closed")

    def write(self, data):
        self.__socket.sendall(data)

    def __enter__(self):
        self.__connect()
        return super().__enter__()

    def __exit__(self, typ, value, traceback):
        self.__socket.close()
        self.__socket = None

    def __connect(self):
        # establish connection to server
        self.__socket = socket.socket()
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # optional
        # self signed certificate: disable verification
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.__socket = context.wrap_socket(self.__socket)
        self.__socket.connect(self.__address)
        self.__socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # password check
        msg = { 'uid': self.uid, 'password': Config.get('password') }
        self.write(json.dumps(msg).encode())
        msg = self.read_all()
        if msg != b'ok':
            raise PasswordError(msg)

    def __repr__(self):
        return f"NetDevice {self.name} ({self.uid}) at {self.__address}"

    def __hash__(self) -> int:
        return hash(self.__repr__())
        