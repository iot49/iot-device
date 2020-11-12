from abc import ABC, abstractmethod
import os, logging, threading

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DeviceRegistry(ABC):

    ###############################################################
    # device registry: all currently available devices
    # class instance

    __devices = {}
    __devices_lock = threading.Lock()
    __listener = None

    @classmethod
    def devices(cls) -> frozenset:
        with cls.__devices_lock:
            return frozenset(cls.__devices.values())

    @classmethod
    def get_devices(cls, uid:str) -> frozenset:
        with cls.__devices_lock:
            result = set()
            for d in cls.__devices.values():
                if d.uid == uid: result.add(d)
            return result

    @classmethod
    def get_device(cls, uid:str, protocol='any'):
        """Return device matching uid and the protocol.
        Protocol 'any' returns any device with given uid.
        Returns None if no devices matche the specification."""
        devs = cls.get_devices(uid)
        if devs:
            if protocol == 'any':
                return next(iter(devs))
            else:
                for d in devs:
                    if d.protocol == protocol: return d
        return None

    @classmethod
    def register(cls, id: str, device):
        logger.info(f"registering {device}")
        with cls.__devices_lock:
            if cls.__devices.get(id):
                logger.warn(f"re-registering device {id}")
            cls.__devices[id] = device
            if cls.__listener:
                cls.__listener.register_device(id, device)

    @classmethod
    def unregister(cls, id: str):
        with cls.__devices_lock:
            if not id in cls.__devices:
                logger.warn(f"unregistering device {id} which not in database")
            else:
                logger.info(f"unregistering {id}")
                del cls.__devices[id]
                if cls.__listener:
                    cls.__listener.unregister_device(id)

    @classmethod
    def register_listener(cls, listener):
        cls.__listener = listener
