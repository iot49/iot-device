from abc import ABC, abstractmethod
import threading
import logging

logger = logging.getLogger(__file__)

"""
Thread-safe dict uid-->device.
Iterate over all known devices (regardless of age). Example:

    ds = DiscoverSerial()
    with ds as devices:
        for d in devices:
            print(d)
"""

class Discover(ABC):

    def __init__(self):
        # __devices: hash --> device
        self.__devices = {}
        self.__devices_lock = threading.Lock()

    def add_device(self, device):
        assert not device.__hash__() in self.__devices
        """Add device to dict; set age to zero if it is already in the dict."""           
        logger.debug(f"add_device {device}")
        with self.__devices_lock:
            self.__devices[device.__hash__()] = device             

    def get_device(self, uid):
        with self.__devices_lock:
            for d in self.__devices.values():
                if d.uid == uid: return d
        return None

    def has_key(self, key) -> bool:
        # true if device key (hash) already stored in __devices
        with self.__devices_lock:
            if key in self.__devices:
                self.__devices[key].seen()
                return True
        return False

    def clear_devices(self):
        self.__devices = {}

    def __enter__(self):
        self.__devices_lock.acquire()
        return self.__devices.values()

    def __exit__(self, type, value, traceback):
        self.__devices_lock.release()


def main():
    from . import DiscoverSerial
    from . import DiscoverNet
    dn = DiscoverSerial()
    print("scanning serial ...")
    dn.scan()
    with dn as devices:
        for dev in devices:
            print(f"   Found {dev}")
    dn = DiscoverNet()
    print("\nscanning net ...")
    dn.scan()
    with dn as devices:
        for dev in devices:
            print(f"   Found {dev}")

if __name__ == "__main__":
    main()
