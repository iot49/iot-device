from .device_registry import DeviceRegistry
from .certificate import create_key_cert_pair
from .secrets import Secrets

from zeroconf import ServiceInfo, Zeroconf
from serial import SerialException
import os
import socket
import selectors
import ssl
import threading
import json
import time
import tempfile
import logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


def _my_ip():
    # determine host's ip address
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # fake address, does not need to be reachable
        s.connect(('10.1.1.1', 1))
        return s.getsockname()[0]


class AdvertiseServer:

    def __init__(self):
        self._zeroconf = Zeroconf()
        self._addresses = [socket.inet_aton(_my_ip())]
        self._id2info = {}

    def register_device(self, id, device):
        info = ServiceInfo(
            type_="_repl._tcp.local.",
            name=device.name + "." + "_repl._tcp.local.",
            port=Secrets.get_attr('server_port', '34567'),
            properties = { "uid": device.uid, "name": device.name },
            addresses=self._addresses)
        self._id2info[id] = info
        self._zeroconf.register_service(info, allow_name_change=True)
        logger.debug(f"advertise {id}")

    def unregister_device(self, id):
        try:
            logger.debug(f"no longer advertise {id}")
            info = self._id2info[id]
            if info:
                self._zeroconf.unregister_service(info)
                del self._id2info[id]
        except AttributeError:
            pass


class DeviceServer():

    def __init__(self):
        # serve devices in device_registry
        self.__ip = _my_ip()
        self.__ssl_context = self.__make_ssl_context()

    def serve(self):
        """Serve multiple connections to different devices in parallel. Never returns."""
        self.__sel = selectors.DefaultSelector()
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = Secrets.get_attr('server_port', '34567')
        lsock.bind(('', port))
        lsock.listen()
        logger.info(f"Listening for connections on {self.__ip}:{port}")
        lsock.setblocking(False)
        self.__sel.register(lsock, selectors.EVENT_READ, data=None)
        while True:
            try:
                events = self.__sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        # connect request (key.fileobj is socket)
                        self.__accept_wrapper(key.fileobj)
                    else:
                        # client connection
                        self.__service_connection(key, mask)
            except Exception as e:
                logger.exception("unhandled exception")


    def __accept_wrapper(self, sock):
        # accept connection
        conn, addr = sock.accept()
        logger.debug(f"accept connection at {(conn, addr)}")
        conn = self.__ssl_context.wrap_socket(conn, server_side=True)
        # More quickly detect bad clients who quit without closing the
        # connection: After 1 second of idle, start sending TCP keep-alive
        # packets every 1 second. If 3 consecutive keep-alive packets
        # fail, assume the client is gone and close the connection.
        try:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except AttributeError:
            pass  # not available on windows
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # get uid and password (blocking recv)
        # TODO: check for incomplete message!
        try:
            uid_pwd = json.loads(conn.recv(1024).decode())
        except ssl.SSLWantReadError:
            logger.error("SSLWantReadError in device_server.__accept_wrapper")
        except (ConnectionResetError, Exception):
            conn.close()
            return
        uid = uid_pwd.get('uid', '?')
        device = DeviceRegistry.get_device(uid)
        logger.debug(f"Request from {addr} to {uid}")
        # check password & device status
        ans = None
        if uid_pwd.get('password') != Secrets.get_attr('password', '?'):
            ans = f'wrong password for {uid}'
        elif not device:
            ans = f'no device {uid}'
        if ans:
            conn.write(ans.encode())
            conn.close()
        else:
            conn.write(b'ok')
            conn.setblocking(False)
            device.__enter__()
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
            self.__sel.register(conn, events, data=device)

    def __service_connection(self, key, mask):
        try:
            sock = key.fileobj
            device = key.data
            if mask & selectors.EVENT_READ:
                # debug code for dealing with SSLWantReadError
                # from Python docs:
                #    exception ssl.SSLWantReadError
                #    A subclass of SSLError raised by a non-blocking SSL socket when
                #    trying to read or write data, but more data needs to be received
                #    on the underlying TCP transport before the request can be fulfilled.
                for _ in range(10):
                    try:
                        recv_data = sock.recv(256)
                        break
                    except ssl.SSLWantReadError:
                        logger.warning("SSLWantReadError in device_server.__service_connection")
                        time.sleep(0.5)
                if recv_data:
                    device.write(recv_data)
                else:
                    logger.info(f"Closing connection to {device.uid}")
                    self.__sel.unregister(sock)
                    sock.close()
                    device.__exit__(None, None, None)
            if mask & selectors.EVENT_WRITE:
                # forward data from device, if any
                msg = device.read_all()
                if len(msg) > 0:
                    sock.sendall(msg)
        except (SerialException, ConnectionResetError, OSError) as e:
            logger.info(f"Communication with {device.uid} failed, closing connection ({e})")
            self.__sel.unregister(sock)
            sock.close()
            device.__exit__(None, None, None)

    @staticmethod
    def __make_ssl_context():
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        with tempfile.NamedTemporaryFile() as cert_file:
            key, cert = create_key_cert_pair()
            cert_file.write(key)
            cert_file.write(cert)
            cert_file.seek(0)
            context.load_cert_chain(certfile=cert_file.name)
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        context.set_ciphers('EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH')
        return context


##########################################################################
# Main

def main():
    from .discover_serial import DiscoverSerial
    import sys

    logging.basicConfig()
    logging.getLogger('device_server').setLevel(logging.INFO)

    # scan serial ports and advertise
    DiscoverSerial()
    DeviceRegistry.register_listener(AdvertiseServer())

    # accept connections and device communication
    DeviceServer().serve()


if __name__ == "__main__":
    main()
