from .discover import Discover
from .net_device import NetDevice
from .config_store import Config

import socket
import json
import time
import logging

logger = logging.getLogger(__file__)

class DiscoverNet(Discover):

    def __init__(self):
        # find & serve devices advertised online
        super().__init__()

    def scan(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Note: port 255.255.255.255 fails with OSError: 
            #     [Errno 49] Can't assign requested address
            # ??? get OSError 98 when server is not running???
            port = Config.get('advertise_port')
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(6)
            try:
                s.bind(('0.0.0.0', port))
            except:
                logger.error("Cannot bind to port {}".format(port))
                raise
            start = time.monotonic()
            while (time.monotonic() - start) < 4:
                try:
                    msg = json.loads(s.recv(1024).decode())
                    if msg['protocol'] != 'repl':
                        logger.error(f"Found device with unknown protocol {msg['protocol'] (msg)}")
                        continue
                    logger.debug(f"Discovered {msg}")
                    if not self.has_key(msg['uid']):
                        self.add_device(NetDevice(msg))
                except socket.timeout:
                    logger.debug("Timeout in discovery")
                except json.JSONDecodeError:
                    logger.debug(f"Received malformed advertisement: {msg}")


def main():
    dn = DiscoverNet()
    print("scanning ...")
    dn.scan()
    with dn as devices:
        for dev in devices:
            print(f"Found {dev}")

if __name__ == "__main__":
    main()
