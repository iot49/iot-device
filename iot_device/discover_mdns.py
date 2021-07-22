from .discover import Discover

from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange
import os, socket, logging, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DiscoverMdns(Discover):
    """zeroconf device discovery"""

    def __init__(self, scan_rate:float=5):
        super().__init__()

    def scan(self):
        # return url's of devices that are online
        self.urls = set()
        if False:
            # asyncio ... task exception error (see below)
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

    def update_service(self, zeroconf, service_type, name):
        self.add_service(zeroconf, service_type, name)

    def remove_service(self, zeroconf, service_type, name):
        pass


"""
13.07.21 17:02:20 (-0700)  jupyter  ERROR:asyncio:Task exception was never retrieved
13.07.21 17:02:20 (-0700)  jupyter  future: <Task finished name='Task-1' coro=<AsyncEngine._async_setup() done, defined at /usr/local/lib/python3.8/site-packages/zeroconf/_core.py:104> exception=OSError(9, 'Bad file descriptor')>
13.07.21 17:02:20 (-0700)  jupyter  Traceback (most recent call last):
13.07.21 17:02:20 (-0700)  jupyter    File "/usr/local/lib/python3.8/site-packages/zeroconf/_core.py", line 107, in _async_setup
13.07.21 17:02:20 (-0700)  jupyter      await self._async_create_endpoints()
13.07.21 17:02:20 (-0700)  jupyter    File "/usr/local/lib/python3.8/site-packages/zeroconf/_core.py", line 133, in _async_create_endpoints
13.07.21 17:02:20 (-0700)  jupyter      transport, protocol = await loop.create_datagram_endpoint(lambda: AsyncListener(self.zc), sock=s)
13.07.21 17:02:20 (-0700)  jupyter    File "/usr/local/lib/python3.8/asyncio/base_events.py", line 1231, in create_datagram_endpoint
13.07.21 17:02:20 (-0700)  jupyter      sock.setblocking(False)
13.07.21 17:02:20 (-0700)  jupyter  OSError: [Errno 9] Bad file descriptor
"""