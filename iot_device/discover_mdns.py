from .discover import Discover

from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import os, socket, logging, threading, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DiscoverMdns(Discover):
    """zeroconf device discovery"""

    def __init__(self, scan_rate:float=5):
        """Start a daemon thread that continually scans ports every scan_rate seconds."""
        super().__init__()
        self.scan_rate = scan_rate
        self.url_lock = threading.Lock()
        self.urls = {}
        th = threading.Thread(target=self._scanner, name="zeroconf scanner")
        th.setDaemon(True)
        th.start()

    def scan(self):
        # return url's of devices that are online
        res = set()
        with self.url_lock:
            for u,t in self.urls.items():
                if time.monotonic() - t < 3*self.scan_rate:
                    res.add(u)
        return res

    def _url(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if info == None: return
        ip = socket.inet_ntoa(info.addresses[0])
        port = info.port
        url = f"{self.scheme(service_type)}://{ip}:{port}"
        return url

    def add_service(self, zeroconf, service_type, name):
        self.urls[self._url(zeroconf, service_type, name)] = time.monotonic()

    def remove_service(self, zeroconf, service_type, name):
        del self.urls[self._url(zeroconf, service_type, name)]

    def _scanner(self):
        # keep rescanning: remove_service not called if server (e.g. ESP32)
        # crashes or is reset without calling mdns_remove_service
        while True:
            zc = Zeroconf()
            try:
                ServiceBrowser(zc, "_mp._tcp.local.", self)
                ServiceBrowser(zc, "_ws._tcp.local.", self)
                ServiceBrowser(zc, "_telnet._tcp.local.", self)
                self.discovered = []
                time.sleep(self.scan_rate)
            except Exception as ex:
                print(ex)
                logger.exception(f"Unhandled exception in DiscoverMdns._scanner")
            finally:
                zc.close()

    def scheme(self, type):
        return type.split('.')[0][1:]
