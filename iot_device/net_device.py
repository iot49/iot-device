from .device import Device
from .config_store import Config
from .exec_protocol import ExecProtocol

import os, socket, ssl, json, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class PasswordError(Exception):
    pass

class NetDevice(Device):

    def __init__(self, url):
        super().__init__(url)

    def read(self, size=1):
        res = bytearray()
        while len(res) < size:
            try:
                b = self.__socket.recv(size-len(res))
            except ssl.SSLWantReadError as sre:
                logger.error(f"read, {sre}")
            if b:
                res.extend(b)
            else:
                raise ConnectionResetError(f"Connection to {self.url} closed")
        return res

    def read_all(self):
        try:
            b = self.__socket.recv(8)
        except ssl.SSLWantReadError as e:
            logger.error(f"NetDevice.read_all, {e}")
        except socket.timeout as e:
            print("TimeoutError in net_device.read_all", e)
            return b""
        except Exception as e:
            print(f"Unspecified exception in net_device.read_all: {type(e)} {e}")
            return b""
        if b:
            return b
        else:
            print("b == None --> Connection reset")
            raise ConnectionResetError(f"Connection to {self.url} closed")

    def write(self, data):
        self.__socket.sendall(data)

    def __enter__(self):
        self.__connect()
        return ExecProtocol(self)

    def __exit__(self, typ, value, traceback):
        print(f"{self.name} bye")
        self.write(b'bye\n')
        # make sure all data is sent???
        time.sleep(0.2)
        self.__socket.close()
        self.__socket = None

    def __connect(self):
        # establish connection to server
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host, port = self.address.split(':')
        # don't wait long for the connection
        self.__socket.settimeout(2)
        self.__socket.connect((host, int(port)))
        # give more time for later communication, eg. fetching results
        self.__socket.settimeout(10)
        self.__socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # password check
        msg = { 'password': Config.get_secret('net_pwd', '???') }
        msg = json.dumps(msg).encode()
        self.write(msg)
        self.write(b'\n')
        msg = self.read_all()
        if msg != b'ok':
            raise PasswordError(msg)
