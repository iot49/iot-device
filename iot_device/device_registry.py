from .eval import RemoteError
from .device import Device
from .discover_serial import DiscoverSerial
from .discover_mdns import DiscoverMdns
from serial import SerialException
import os, logging, threading, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DeviceRegistry:
    """Keeps track of currently available devices"""

    def __init__(self):
        self._discover_serial = DiscoverSerial()
        self._discover_mdns = DiscoverMdns()
        # map url -> device
        self._devices = {}
        # map url -> time of last attempt
        self._registration_failed = {}

    @property
    def devices(self) -> frozenset:
        """List of all devices that are currently online. Includes InaccessibleDevice."""
        self._update()
        return frozenset(self._devices.values())

    def get_device(self, name: str, schemes=None) -> Device:
        """Device with given name/uid/url & schemes."""
        if schemes == None or len(schemes) == 0:
            schemes = ['serial', 'ws', 'mp']
        self._update()
        for scheme in schemes:
            for dev in self._devices.values():
                if (dev.name == name or dev.uid == name or dev.url == name) and dev.scheme == scheme:
                    return dev
        return None

    def _update(self):
        # update database ...
        urls = self._discover_serial.scan() | self._discover_mdns.scan()
        # 1) purge database of devices that are no longer available
        now = time.monotonic()
        for k in list(self._devices.keys()):
            if k in urls: continue
            v = self._devices[k]
            if not v.max_age: continue
            if (now-v.last_seen) > v.max_age:
                del self._devices[k]
        # 2) register newly discovered devices (not already in database)
        for url in urls:
            try:
                self.register(url, 0.5)
            except (ValueError, RemoteError) as e:
                # leave this print statement - will show up in jupyter!
                print(f"\nFailed to register {url}:\n{e}\n")
                logger.info(f"Failed to register {url}: {e}")

    def register(self, url:str, max_age:float=None):
        """Create device for given url and register in database.
        :param: max_age:float  Device automatically unregistered
                     if no activity (register) in specified interval.
                     Default: None, no automatic unregistering.
                     Calling register (repeatedly) resets age to 0.
        """
        if url in self._registration_failed.keys():
            if (time.monotonic() - self._registration_failed[url]) < 10:
                logger.info(f"skipping failed registration for '{url}'")
                return
            del self._registration_failed[url]
        if url in self._devices.keys():
            # already in database
            self._devices[url].last_seen = time.monotonic()
            return
        # create a new device
        logger.debug(f"register {url}")
        device_class = find_device_class(url)
        try:
            device = device_class(url)
        except Exception as e:
            self._registration_failed[url] = time.monotonic()
            print(f"Registration failed for {url}: {e}")
            logger.error(f"Registration failed for {url}: {e}")
            return
        device.max_age = max_age
        device.last_seen = time.monotonic()
        self._devices[url] = device
        logger.info(f"registered {device.name} {device.uid} {url}")

    def unregister(self, name:str):
        """Unregister device (by name, uid, or url)"""
        url = None
        for v in self._devices.values():
            if name == v.uid or name == v.name or name == v.url:
                url = v.url
                break
        if not url:
            raise ValueError(f"Device '{name}' not in registry")
        del self._devices[url]
        logger.debug(f"unregisted '{url}'")


def find_device_class(url):
    from .serial_device import SerialDevice
    from .mp_device import MpDevice
    from .telnet_device import TelnetDevice
    from .webrepl_device import WebreplDevice
    classes = {}
    classes['serial'] = SerialDevice
    classes['mp']     = MpDevice
    classes['ws']     = WebreplDevice
    classes['wss']    = WebreplDevice
    classes['telnet'] = TelnetDevice
    try:
        scheme, _ = url.split('://')
    except ValueError as e:
        raise ValueError(f"Invalid url: {url}")
    c = classes.get(scheme)
    if c: return c
    raise ValueError(f"Unknown scheme: {scheme}")
