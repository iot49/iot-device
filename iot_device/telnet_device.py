from .device import Device
from .config_store import Config
from .eval import RemoteError
from .repl_protocol import ReplProtocol

from telnetlib import Telnet
import os, select, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class TelnetDevice(Device):

    def __init__(self, url):
        super().__init__(url)

    def read(self, size=1):
        sock = self.__telnet.get_socket()
        res = b''
        while len(res) < size:
            r,_,_ = select.select([sock], [], [], 0.1)
            if r: res += sock.recv(size)
            if len(res) >= size:
                return res
            time.sleep(0.01)

    def read_all(self):
        sock = self.__telnet.get_socket()
        r,_,_ = select.select([sock], [], [], 0.1)
        return sock.recv(1024) if r else b''

    def write(self, data):
        return self.__telnet.get_socket().sent(data)
        #
        sock = self.__telnet.get_socket()
        chunk_size = 64
        n = 0
        for i in range(0, len(data), chunk_size):
            n += sock.send(data[i:min(i+chunk_size, len(data))])
            if n < len(data):
                time.sleep(0.2)
        return n

    def flush_input(self):
        """Flush input buffer - data from MCU"""
        self.read_all()

    def __enter__(self):
        addr, port = self.address.split(':')
        self.__telnet = Telnet(addr, port)
        print("TelnetDevice - enter")
        return ReplProtocol(self)

    def __exit__(self, type, value, traceback):
        try:
            print("TelnetDevice.close")
            self.__telnet.close()
            print("closed")
        except Exception as e:
            print("*** close", e)
            pass
        self.__telnet = None
