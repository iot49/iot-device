from .discover import Discover
from .repl import ReplException
from .serial_device import SerialDevice

from serial import SerialException
import time
import logging
import serial
import serial.tools.list_ports

logger = logging.getLogger(__file__)

# Vendor IDs
ADAFRUIT_VID = 0x239A  # Adafruit board
PARTICLE_VID = 0x2B04  # Particle
ESP32_VID    = 0x10C4  # ESP32 via CP2104
STM32_VID    = 0xf055  # STM32 usb port

COMPATIBLE_VID = { ADAFRUIT_VID, PARTICLE_VID, STM32_VID, ESP32_VID }


class DiscoverSerial(Discover):

    def __init__(self):
        super().__init__()

    def scan(self):
        # scan & replicate serial ports
        try:
            for port in serial.tools.list_ports.comports():
                if port.vid in COMPATIBLE_VID:
                    if not self.has_key(port.device):
                        logger.info(f"Found {port.device}")
                        dev = SerialDevice(port.device, f"{port.product} by {port.manufacturer}")
                        self.add_device(dev)
                elif port.vid:
                    logger.info("Found {} with unknown VID {:02X} (ignored)".format(port, port.vid))
        except Exception as e:
            logger.exception(f"Error in scan: {e}")


def main():
    dn = DiscoverSerial()
    print("scanning ...")
    dn.scan()
    with dn as devices:
        for dev in devices:
            print(f"Found {dev}")

if __name__ == "__main__":
    main()
