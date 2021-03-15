from .discover import Discover

from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import os, socket, logging, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DiscoverMdns(Discover):
    """zeroconf device discovery"""

    def __init__(self, scan_rate:float=5):
        """Start a daemon thread that continually scans ports every scan_rate seconds."""
        super().__init__()

    def scan(self):
        # return url's of devices that are online
        self.urls = set()
        zc = Zeroconf()
        try:
            ServiceBrowser(zc, "_mp._tcp.local.", self)
            ServiceBrowser(zc, "_ws._tcp.local.", self)
            ServiceBrowser(zc, "_telnet._tcp.local.", self)
            # give the scanner some time to find everything ...
            time.sleep(1)
        except Exception as ex:
            print(ex)
            logger.exception(f"Unhandled exception in DiscoverMdns._scanner")
        finally:
            zc.close()
        return self.urls

    def _url(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if info == None: return
        ip = socket.inet_ntoa(info.addresses[0])
        port = info.port
        scheme = service_type.split('.')[0][1:]
        url = f"{scheme}://{ip}:{port}"
        return url

    def add_service(self, zeroconf, service_type, name):
        self.urls.add(self._url(zeroconf, service_type, name))

    def remove_service(self, zeroconf, service_type, name):
        pass

    def update_service(self, zeroconf, service_type, name):
        pass
