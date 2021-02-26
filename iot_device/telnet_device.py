from .device import Device
from .eval import RemoteError
from .repl_protocol import ReplProtocol

from telnetlib import Telnet
from collections import deque
import os, select, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class TelnetDevice(Device):

    def __init__(self, url):
        self.use_raw_paste = False
        self.fifo = deque()
        self.read_timeout = 10
        super().__init__(url)

    def read(self, size=1):
        while len(self.fifo) < size:
            timeout_count = 0
            data = self.__telnet.read_eager()
            if len(data):
                self.fifo.extend(data)
                timeout_count = 0
            else:
                time.sleep(0.1)
                if self.read_timeout is not None and timeout_count > 4 * self.read_timeout:
                    break
                timeout_count += 1

        data = b""
        while len(data) < size and len(self.fifo) > 0:
            data += bytes([self.fifo.popleft()])
        return data

    def write(self, data):
        if len(data) < 220:
            return self.__telnet.write(data)
        # slow to avoid communication errors
        # (esp32 notify buffer overflow)
        chunk_size = 64
        n = 0
        for i in range(0, len(data), chunk_size):
            n += self.__telnet.write(data[i:min(i+chunk_size, len(data))])
            if n < len(data):
                time.sleep(0.2)
        return n

        self.__telnet.write(data)
        return len(data)

    def inWaiting(self):
        n_waiting = len(self.fifo)
        if not n_waiting:
            data = self.__telnet.read_eager()
            self.fifo.extend(data)
            return len(data)
        else:
            return n_waiting

    def __enter__(self):
        addr, port = self.address.split(':')
        self.__telnet = Telnet(addr, port, timeout=15)
        print(f"TelnetDevice({addr}, {port}) - enter")
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
