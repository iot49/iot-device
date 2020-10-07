from .discover import Discover
from .net_device import NetDevice

from zeroconf import ServiceBrowser, Zeroconf
import socket
import logging

logger = logging.getLogger(__file__)

class DiscoverNet(Discover):

    def __init__(self):
        """Find & serve devices advertised online using zeroconf"""
        super().__init__()
        ServiceBrowser(Zeroconf(), type_="_repl._tcp.local.", handlers=self)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        ip = socket.inet_ntoa(info.addresses[0])
        port = info.port
        uid = info.properties.get(b'uid').decode()
        dev = NetDevice(uid, (ip, port))
        self._register_device(name, dev)

    def remove_service(self, zeroconf, type, name):
        self._unregister_device(name)

    def update_service(self, zeroconf, type, name):
        logging.warn(f"update_service received for {name}")
