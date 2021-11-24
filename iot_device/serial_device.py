from .device import Device
from .eval import RemoteError
from .repl_protocol import ReplProtocol
from .pyboard import PyboardError

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
        except (BlockingIOError, SerialException):
            raise
            # raise RemoteError(f"Device {self.url} not available (in use?)")
        except Exception as e:
            raise RemoteError(f"Device {self.url} encountered problem: {e}")
        try:
            self._repl_protocol = ReplProtocol(self)
        except PyboardError as e:
            # could not enter raw repl
            self.__serial.close()
            raise RemoteError(f"{e} (unexpected output, perhaps from main.py?)")
        return self._repl_protocol

    def __exit__(self, type, value, traceback):
        try:
            self._repl_protocol.close()
        finally:
            self.__serial.close()
            self.__serial = None
