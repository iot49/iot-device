from .discover import Discover
from .secrets import Secrets

from threading import Thread, Lock

import socket, threading, os, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DiscoverBroadcasts(Discover):

    def __init__(self, max_age=5):
        """Start a daemon thread that collects advertisements and discards them after max_age seconds."""
        super().__init__()
        self._lock = _lock = Lock()
        self._urls = _urls = dict()
        self._max_age = max_age

        def scanner():
            nonlocal _urls, _lock
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            # see https://stackoverflow.com/questions/14388706
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            client.bind(("", Secrets.get_attr('broadcast_port', 50000)))
            try:
                while True:
                    data, addr = client.recvfrom(256)
                    try:
                        url, uid = data.split(b'\n')
                        # TODO: discard devices without device_config
                        with _lock:
                            _urls[url.decode()] = time.monotonic()
                    except (AttributeError, ValueError):
                        logger.DEBUG(f"received malformed advertisement {data} from {addr}")
            finally:
                client.close()


        self._thread = Thread(target=scanner)
        self._thread.start()

    def scan(self):
        with self._lock:
            # set of urls seen in last _max_age seconds
            return { url for url, t in self._urls.items() if (time.monotonic()-t) < self._max_age }