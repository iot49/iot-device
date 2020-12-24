from .eval import RemoteError
from .serial_device import SerialDevice
from .net_device import NetDevice
import os, logging, threading, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DeviceRegistry:

    ###############################################################
    # device registry: all currently available devices
    # singleton, implemented as class instance

    # map url -> device
    __devices = {}
    __devices_lock = threading.Lock()
    __listener = None

    @classmethod
    def _purge(cls):
        # purge "old" devices from database
        now = time.monotonic()
        with cls.__devices_lock:
            devices = {}
            for k,v in cls.__devices.items():
                # only keep devices recently seen
                if not v.max_age or (now-v.last_seen) < v.max_age:
                    devices[k] = v
            cls.__devices = devices

    @classmethod
    def devices(cls) -> frozenset:
        cls._purge()
        with cls.__devices_lock:
            return frozenset(cls.__devices.values())

    @classmethod
    def get_device(cls, uid_or_url: str):
        """Return device with given uid or url."""
        cls._purge()
        with cls.__devices_lock:
            if uid_or_url in cls.__devices:
                return cls.__devices[uid_or_url]
            for d in cls.__devices.values():
                if d.uid == uid_or_url:
                    return d
            return None

    @classmethod
    def register(cls, url: str, max_age:float=None):
        """Create device for given url and register in database.
        :param: max_age:float  Device automatically unregistered
                     if no activity (register) in specified interval.
                     Default: None, no automatic unregistering.
                     Calling register (repeatedly) resets age to 0.
        """
        if url in cls.__devices:
            # already in database
            cls.__devices[url].last_seen = time.monotonic()
            return
        with cls.__devices_lock:
            # create a new device
            scheme, _ = url.split('://')
            if scheme == 'serial':
                device = SerialDevice(url)
            elif scheme == 'exec':
                device = NetDevice(url)
            else:
                raise ValueError(f"Unknown scheme {scheme}")
            device.max_age = max_age
            device.last_seen = time.monotonic()
            cls.__devices[url] = device
            if cls.__listener:
                cls.__listener.register_device(url, device)

    @classmethod
    def unregister(cls, device:str):
        """Unregister device (by name, uid, or url)"""
        with cls.__devices_lock:
            url = None
            if device in cls.__devices:
                url = device
            else:
                for k,v in cls.__devices.items():
                    if device == v.uid or device == v.name:
                        url = k
                        break
            if not url:
                raise ValueError(f"device not in registry: {url}")
            logger.info(f"unregistering {url}")
            del cls.__devices[url]
            if cls.__listener:
                cls.__listener.unregister_device(url)

    @classmethod
    def register_listener(cls, listener):
        cls.__listener = listener
