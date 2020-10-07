from .device import Device

import logging, threading

logger = logging.getLogger(__file__)

class DeviceRegistry:
    """Thread-safe registry of currently available devices."""

    def __init__(self):
        self._devices = {}
        self._devices_lock = threading.Lock()

    def register_device(self, id, device):
        with self as devices:
            if id in devices:
                # do not modify already registered device
                logger.warn(f"re-registering {id} -> {device}")
            else:
                logger.info(f"registering {id} -> {device}")
                devices[id] = device

    def unregister_device(self, id):
        with self as devices:
            if not id in devices:
                logger.warn(f"unregistering device {id} which not in database")
            else:
                logger.info(f"unregistering {id}")
                del devices[id]

    def devices(self) -> frozenset:
        with self as devices:
            return frozenset(devices.values())

    def get_devices(self, uid) -> frozenset:
        result = set()
        with self as devices:
            for d in devices.values():
                if d.uid == uid: result.add(d)
        return result

    def get_device(self, uid, protocol='any') -> Device:
        """Return device matching uid and the protocol.
        Protocol 'any' returns any device with given uid.
        Returns None if no devices matche the specification."""
        devs = self.get_devices(uid)
        if devs:
            if protocol == 'any':
                return next(iter(devs))
            else:
                for d in devs:
                    if d.protocol == protocol: return d
        return None

    def __enter__(self):
        """Contextmanager returning pointer to devices in database.        
        raises TimeoutError"""
        if not self._devices_lock.acquire(timeout=10):
            raise TimeoutError("DeviceRegistry failed to acquire lock")
        return self._devices

    def __exit__(self, *args):
        self._devices_lock.release()



##########################################################################
# Example

def main():
    from .discover_serial import DiscoverSerial
    from .discover_net import DiscoverNet
    import sys, time

    logging.getLogger().setLevel(logging.INFO)

    # catalog of availble devices
    registry = DeviceRegistry()

    # create device scanners
    DiscoverSerial().register_listener(registry)
    DiscoverNet().register_listener(registry)

    while True:
        if registry.devices():
            print("active devices:")
            for d in registry.devices():
                print(f"    {d}")
        else:
            print("found no devices")
        time.sleep(1)

if __name__ == "__main__":
    # main()
    print("*** REG")