from .discover import Discover
from .device_registry import DeviceRegistry
from .serial_device import SerialDevice
from .eval import DeviceError

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

    def scan(self):
        """Scan for new/removed devices."""
        connected_ports = self._list_usb_ports()
        connected_devices = set(connected_ports.keys())
        registered_devices = {
            x.address for x in DeviceRegistry.devices() 
            if isinstance(x, SerialDevice) }
        removed = registered_devices - connected_devices
        added = connected_devices - registered_devices
        # notify listeners
        for usb_path in added:
            try:
                port = connected_ports[usb_path]
                product = port.product
                if 'CP2104' in product: product = 'CP2104 (ESP32)'
                manuf = port.manufacturer
                if 'Adafruit' in manuf: manuf = 'Adafruit'
                desc = f"{manuf} {product}, VID={port.vid:04X} PID={port.pid:04X}"
                SerialDevice(desc, usb_path)
            except (DeviceError, SerialException, BlockingIOError):
                # device unavailable
                pass
        for usb_path in removed:
            DeviceRegistry.unregister(usb_path)

    def _list_usb_ports(self):
        """Set of ports with connected microcontrollers"""
        devices = {}
        for port in serial.tools.list_ports.comports():
            if port.vid in COMPATIBLE_VID:
                devices[port.device] = port
            elif port.vid:
                logger.info(f"Found {port} with unknown VID {port.vid:02X} (ignored)")
        return devices

    def _scanner(self, scan_rate: float):
        while True:
            try:
                self.scan()
                time.sleep(scan_rate)
            except Exception as ex:
                logger.error(f"_scanner {type(ex)}: {ex}")
                # logger.exception(f"Unhandled exception in scanner: type {type(ex)}")
