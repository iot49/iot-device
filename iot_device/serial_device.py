from .device import Device
from .config_store import Config

from serial import Serial, SerialException
import time
import logging

logger = logging.getLogger(__file__)

class SerialDevice(Device):

    def __init__(self, port, baudrate=115200):
        self.__port = port
        self.__baudrate = baudrate
        super().__init__()

    @property
    def address(self):
        return self.__port

    @property
    def connection(self):
        return 'serial'

    def __connect(self):
        try:
            self.__serial = Serial(self.__port, self.__baudrate, parity='N', timeout=0.5)
        except SerialException as se:
            logger.error(f"SerialDevice: __connect failed {se}")

    def read(self, size=1):
        for _ in range(2):
            try:
                return self.__serial.read(size)
            except (SerialException, OSError):
                self.__connect()
        raise SerialException("read failed")

    def read_all(self):
        for _ in range(2):
            try:
                return self.__serial.read_all()
            except (SerialException, OSError):
                self.__connect()
        raise SerialException("read_all failed")

    def write(self, data):
        for _ in range(2):
            try:
                n = 0
                for i in range(0, len(data), 256):
                    n += self.__serial.write(data[i:min(i+256, len(data))])
                    time.sleep(0.01)
                return n
            except (SerialException, OSError):
                self.__connect()
        raise SerialException("write failed")

    def close(self):
        self.__serial.close()

    def __enter__(self):
        res = super().__enter__()
        self.__connect()
        return res

    def __eq__(self, other):
        return isinstance(other, SerialDevice) and self.__port == other.__port

    def __repr__(self) -> str:
        return f"SerialDevice {self.name} ({self.uid}) at {self.__port}"

    def __hash__(self) -> int:
        return hash(self.__port)
        