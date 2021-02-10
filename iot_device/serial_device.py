from .device import Device
from .config_store import Config
from .eval import RemoteError
from .repl_protocol import ReplProtocol

from serial import Serial, SerialException
import os, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class SerialDevice(Device):

    def __init__(self, url):
        super().__init__(url)

    def read(self, size):
        return self.__serial.read(size)

    def write(self, data):
        return self.__serial.write(data)

    def inWaiting(self):
        return self.__serial.in_waiting

    def __enter__(self):
        try:
            self.__serial = Serial(self.address, 115200, parity='N',
                timeout=0.5,            # read timeout
                write_timeout=2,
                exclusive= True         # exclusive access mode (POSIX only)
            )
            return ReplProtocol(self)
        except (BlockingIOError, SerialException):
            raise
            # raise RemoteError(f"Device {self.url} not available (in use?)")
        except Exception as e:
            raise RemoteError(f"Device {self.url} encountered problem: {e}")

    def __exit__(self, type, value, traceback):
        self.__serial.close()
        self.__serial = None
