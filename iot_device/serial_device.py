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

    def read(self, size=1):
        return self.__serial.read(size)

    def read_all(self):
        return self.__serial.read_all()

    def write(self, data):
        n = 0
        for i in range(0, len(data), 256):
            n += self.__serial.write(data[i:min(i+256, len(data))])
            time.sleep(0.01)
        return n

    def flush_input(self):
        """Flush input buffer - data from MCU"""
        self.__serial.reset_input_buffer

    def __enter__(self):
        try:
            self.__serial = Serial(self.address, 115200, parity='N',
                timeout=1.5,            # read timeout
                write_timeout=1.5,
                exclusive= True         # exclusive access mode (POSIX only)
            )
            return ReplProtocol(self)
        except (BlockingIOError, SerialException):
            raise RemoteError(f"Device {self.url} not available (in use?)")
        except Exception as e:
            raise RemoteError(f"Device {self.url} encountered problem: {e}")

    def __exit__(self, type, value, traceback):
        self.__serial.close()
        self.__serial = None
