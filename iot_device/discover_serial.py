from .discover import Discover
from .serial_device import SerialDevice
from .eval import EvalException

from serial import SerialException
import time
import logging
import serial
import serial.tools.list_ports
import threading

logger = logging.getLogger(__file__)

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
        # set of currently active ports
        self._ports = set()
        th = threading.Thread(target=self._scanner, args=(scan_rate,), name="serial scanner")
        th.setDaemon(True)
        th.start()
        self._scan_thread = th

    def scan(self):
        """Scan for new/removed devices."""
        current_ports = self._list_ports()
        added = current_ports - self._ports
        removed = self._ports - current_ports
        self._ports = current_ports
        # logger.debug(f"scan! {current_ports}\n   added {added}\n   removed {removed}")
        # notify listeners
        for port in added:
            try:
                dev = SerialDevice(port)
                # A device may be accessible simulataneously via multiple
                # protocols, e.g. a serial interface and an async task.
                # Note: uid not available in remove ...
                self._register_device(port, dev)
            except (TimeoutError, EvalException, SerialException):
                # esp32 takes time to boot ...
                self._ports.remove(port)
        for port in removed:
            self._unregister_device(port)

    def _list_ports(self):
        """Set of ports with connected microcontrollers"""
        ports = set()
        for port in serial.tools.list_ports.comports():
            if port.vid in COMPATIBLE_VID:
                ports.add(port.device)
            elif port.vid:
                logger.info(f"Found {port} with unknown VID {port.vid:02X} (ignored)")
        return ports

    def _scanner(self, scan_rate: float):
        while True:
            try:
                self.scan()
                time.sleep(scan_rate)
            except Exception as ex:
                logger.error(f"Unhandled exception in scanner: {ex}")
