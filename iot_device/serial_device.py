from .device import Device
from .config_store import Config
from .eval import DeviceError

from serial import Serial, SerialException
import os, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class SerialDevice(Device):

    def __init__(self, desc: str, port: str, baudrate=115200):
        self.__port = port
        self.__baudrate = baudrate
        super().__init__(id=port, desc=desc)

    @property
    def address(self):
        return self.__port

    @property
    def connection(self):
        return 'serial'

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
            self.__serial = Serial(self.__port, self.__baudrate, parity='N', 
                timeout=1.5,            # read timeout
                write_timeout=1.5,
                exclusive= True         # exclusive access mode (POSIX only)
            )
            return super().__enter__()
        except (BlockingIOError, SerialException):
            raise DeviceError(f"Device {self.address} not available (in use?)")

    def __exit__(self, type, value, traceback):
        self.__serial.close()
        self.__serial = None

    def __repr__(self) -> str:
        try:
            name = self.name
            uid = self.uid
            return f"SerialDevice {name} ({uid}) at {self.__port}"
        except SerialException:
            return f"SerialDevice {self.description} at {self.__port}"
