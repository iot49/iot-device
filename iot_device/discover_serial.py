from .discover import Discover
from .device_registry import DeviceRegistry

from serial import SerialException
import serial.tools.list_ports
import os, time, logging ,threading

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


# Vendor IDs
ADAFRUIT_VID = 0x239A  # Adafruit board
PARTICLE_VID = 0x2B04  # Particle
ESP32_VID    = 0x10C4  # ESP32 via CP2104
STM32_VID    = 0xf055  # STM32 usb port

COMPATIBLE_VID = { ADAFRUIT_VID, PARTICLE_VID, STM32_VID, ESP32_VID }


class DiscoverSerial(Discover):

    def __init__(self, scan_rate: float = 0.2):
        """Start a daemon thread that continually scans ports every scan_rate seconds."""
        super().__init__()
        th = threading.Thread(target=self._scanner, args=(scan_rate,), name="serial scanner")
        th.setDaemon(True)
        th.start()
        self._scan_thread = th

    def _scanner(self, scan_rate: float):
        while True:
            try:
                for port in serial.tools.list_ports.comports():
                    if port.vid in COMPATIBLE_VID:
                        DeviceRegistry.register(f"serial://{port.device}", max_age=2*scan_rate)
                    elif port.vid:
                        logger.info(f"Found {port} with unknown VID {port.vid:02X} (ignored)")
                time.sleep(scan_rate)
            except Exception as ex:
                logger.exception(f"Unhandled exception in scanner: type {type(ex)}", ex)
