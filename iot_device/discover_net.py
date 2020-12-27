from .discover import Discover
from .net_device import NetDevice
from .device_registry import DeviceRegistry

from zeroconf import ServiceBrowser, Zeroconf
import os, socket, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DiscoverNet(Discover):

    def __init__(self):
        """Find & serve devices advertised online using zeroconf"""
        super().__init__()
        ServiceBrowser(Zeroconf(), type_="_repl._tcp.local.", handlers=self)
        ServiceBrowser(Zeroconf(), type_="_exec._tcp.local.", handlers=self)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        ip = socket.inet_ntoa(info.addresses[0])
        port = info.port
        DeviceRegistry.register(f"{self.scheme(type)}://{port.device}")

    def update_service(self, zeroconf, type, name):
        add_serice(self, zeroconf, type, name)

    def remove_service(self, zeroconf, type, name):
        DeviceRegistry.register(f"{self.scheme(type)}://{port.device}")

    def scheme(self, type):
        return type.split('.')[0][1:]
