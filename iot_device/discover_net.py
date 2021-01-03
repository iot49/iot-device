from .discover import Discover
from .net_device import NetDevice
from .device_registry import DeviceRegistry

from zeroconf import ServiceBrowser, Zeroconf
import os, socket, logging, threading, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DiscoverNet(Discover):

    def __init__(self, scan_rate:float=1):
        """Start a daemon thread that continually scans ports every scan_rate seconds."""
        super().__init__()
        self.scan_rate = scan_rate
        th = threading.Thread(target=self._scanner, args=(scan_rate,), name="zeroconf scanner")
        th.setDaemon(True)
        th.start()
        self._scan_thread = th

    def _on_change(self, zeroconf, service_type, name, state_change):
        info = zeroconf.get_service_info(service_type, name)
        ip = socket.inet_ntoa(info.addresses[0])
        port = info.port
        url = f"{self.scheme(service_type)}://{ip}:{port}"
        self.discovered.append(url)

    def _register(self):
        # Note: don't register from on_change as this may result in a race condition
        for url in self.discovered:
            try:
                logger.info(f"register {url}")
                DeviceRegistry.register(url, 2*self.scan_rate)
            except ConnectionResetError:
                logger.warn(f"Connection to {url} reset")
            except ConnectionRefusedError:
                logger.warn(f"Connection to {url} refused")
            except Exception as e:
                logger.exception(f"Unhandled exception in DiscoverNet._register")

    def _scanner(self, scan_rate: float):
        while True:
            # Discover
            zc = Zeroconf()
            self.discovered = []
            try:
                ServiceBrowser(zc, "_net._tcp.local.", handlers=[self._on_change])
                time.sleep(scan_rate)
            except Exception as ex:
                print(ex)
                logger.exception(f"Unhandled exception in DiscoverNet._scanner")
            finally:
                zc.close()
            self._register()



    def scheme(self, type):
        return type.split('.')[0][1:]
