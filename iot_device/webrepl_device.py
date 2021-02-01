from .device import Device
from .config_store import Config
from .eval import RemoteError
from .repl_protocol import ReplProtocol

from websocket import create_connection, WebSocketException
import os, time, logging, select

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class WebreplDevice(Device):

    def __init__(self, url):
        super().__init__(url)

    def read(self, size=1):
        res = b''
        while len(res) < size:
            r,_,_ = select.select([self.__ws], [], [], 0.1)
            if r: res += self.__ws.recv().encode()
            if len(res) >= size:
                return res
            time.sleep(0.01)

    def read_all(self):
        r,_,_ = select.select([self.__ws], [], [], 0.5)
        res = self.__ws.recv().encode() if r else b''
        return res

    def write(self, data):
        # glacially slow to avoid communication errors
        chunk_size = 64
        n = 0
        for i in range(0, len(data), chunk_size):
            n += self.__ws.send(data[i:min(i+chunk_size, len(data))])
            if n < len(data):
                time.sleep(0.2)
        return n

    def flush_input(self):
        """Flush input buffer - data from MCU"""
        pass

    def __enter__(self):
        try:
            self.__ws = create_connection(self.url, 3)
            self.__ws.settimeout(100)
            self.read_until(b'Password: ')
            self.write(Config.get_secret('webrepl_pwd', '???').encode())
            self.write(b'\r\n')
            self.read_until(b'>>> ')
            return ReplProtocol(self)
        except WebSocketException as e:
            raise RemoteError(f"Websocket exception: {e}")

    def __exit__(self, type, value, traceback):
        # takes ages ...
        try:
            self.__ws.close()
        except WebSocketException as e:
            pass
        self.__ws = None
