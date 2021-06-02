from .discover import Discover
from .eval import RemoteError

from serial import SerialException
import serial.tools.list_ports
import os, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


# Vendor IDs
ADAFRUIT_VID = 0x239A  # Adafruit board
PARTICLE_VID = 0x2B04  # Particle
ESP32_VID    = 0x10C4  # ESP32 via CP2104
STM32_VID    = 0xf055  # STM32 usb port

COMPATIBLE_VID = { ADAFRUIT_VID, PARTICLE_VID, STM32_VID, ESP32_VID }


class DiscoverSerial(Discover):

    def __init__(self, scan_rate:float=1):
        """Start a daemon thread that continually scans ports every scan_rate seconds."""
        super().__init__()

    def scan(self):
        # return url's of devices that are online
        res = set()
        for port in serial.tools.list_ports.comports():
            if port.vid in COMPATIBLE_VID:
                res.add(f"serial://{port.device}")
            elif port.vid:
                logger.info(f"Found {port} with unknown VID {port.vid:02X} (ignored)")
        return res
