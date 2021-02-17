from .device import Device
from .config_store import Config
from .eval import RemoteError
from .repl_protocol import ReplProtocol

from websocket import create_connection, WebSocketException
import os, time, logging, select

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class WebreplDevice(Device):

    def __init__(self, url):
        self.use_raw_paste = False
        super().__init__(url)

    def inWaiting(self):
        r,_,_ = select.select([self.__ws], [], [], 0.1)
        return 1 if r else 0

    def read(self, size=1):
        res = b''
        while len(res) < size:
            r,_,_ = select.select([self.__ws], [], [], 0.1)
            if r: res += self.__ws.recv().encode()
            if len(res) >= size:
                return res
            time.sleep(0.01)

    def write(self, data):
        if len(data) < 252:
            return self.__ws.send(data)
        # slow down to avoid communication errors
        chunk_size = 64
        n = 0
        for i in range(0, len(data), chunk_size):
            logger.debug(f"webrepl_device.write({data[i:min(i+chunk_size, len(data))]})")
            n += self.__ws.send(data[i:min(i+chunk_size, len(data))])
            if n < len(data):
                time.sleep(0.5)
        return n

    def __enter__(self):
        try:
            self.__ws = create_connection(self.url, 3)
            self.__ws.settimeout(100)
            p = b'Password: '
            pp = self.read(len(p))
            self.write(Config.get_secret('webrepl_pwd', '???').encode())
            self.write(b'\r\n')
            return ReplProtocol(self)
        except WebSocketException as e:
            raise RemoteError(f"Websocket exception: {e}")

    def __exit__(self, type, value, traceback):
        try:
            # takes ages ...
            self.__ws.close()
        except Exception as e:
            logger.exception(f"***** Webrepdevice.close {e}")
        self.__ws = None
