from .certificate import create_key_cert_pair
from .config_store import Config

from serial import SerialException
import socket
import selectors
import ssl
import threading
import json
import time
import tempfile
import logging

logger = logging.getLogger(__file__)


class DeviceServer():

    def __init__(self, discovery, max_age=2*Config.get('device_scan_interval', 1)):
        # serve devices in discovery
        self.__discovery = discovery
        self.__max_age = max_age
        self.__ip = self.__my_ip()
        self.__ssl_context = self.__make_ssl_context()
        # start connection server
        th = threading.Thread(target=self.__device_server, name="Serve Devices")
        th.setDaemon(True)
        th.start()
        # start advertising deamon
        th = threading.Thread(target=self.__advertise, name="Advertise")
        th.setDaemon(True)
        th.start()

    def __device_server(self):
        # serve multiple connections to different devices in parallel
        self.__sel = selectors.DefaultSelector()
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = Config.get('connection_server_port', 50003)
        lsock.bind(('', port))
        lsock.listen()
        logger.info(f"Listening for connections on {self.__ip}:{port}")
        lsock.setblocking(False)
        self.__sel.register(lsock, selectors.EVENT_READ, data=None)
        while True:
            events = self.__sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    # connect request (key.fileobj is socket)
                    self.__accept_wrapper(key.fileobj)
                else:
                    # client connection
                    self.__service_connection(key, mask)

    def __accept_wrapper(self, sock):
        # accept connection
        conn, addr = sock.accept()
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
        uid = uid_pwd.get('uid', '?')
        device = self.__discovery.get_device(uid)
        logger.debug(f"Request from {addr} to {uid}")
        # check password & device status
        ans = None
        if uid_pwd.get('password') != Config.get('password'):
            ans = b'wrong password'
        elif not device:
            ans = b'no such device'
        elif device.locked:
            ans = b'device busy'
        if ans:
            conn.write(ans)
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
        except (SerialException, ConnectionResetError) as e:
            logger.info(f"Communication with {device.uid} failed, closing connection ({e})")
            self.__sel.unregister(sock)
            sock.close()
            device.__exit__(None, None, None)

    def __advertise(self):
        s = None
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                advertise_port = Config.get('advertise_port')
                self.__discovery.scan()
                with self.__discovery as devices:
                    for dev in devices:
                        if dev.age > self.__max_age: 
                            # logger.debug(f"Not advertising {dev}, age {dev.age} > {self.max_age}")
                            continue
                        msg = {
                            'uid': dev.uid,
                            'ip_addr': self.__ip,
                            'ip_port': Config.get('connection_server_port'),
                            'protocol': 'repl',
                            'last_seen': dev.last_seen,
                        }
                        data = json.dumps(msg)
                        s.sendto(data.encode(), ('255.255.255.255', advertise_port))
                        # logger.debug(f"Advertise {dev}")
            except Exception as e:
                # restart, e.g. in case of [Errno 51] Network is unreachable
                logger.exception(f"Network unreachabl (advertise), attempting to reconnect: {e}")
                if s:
                    try:
                        s.close()
                    except:
                        pass
                time.sleep(5)
            time.sleep(Config.get('device_scan_interval', 1))

    def __my_ip(self):
        # determine host's ip address
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # fake address, does not need to be reachable
            s.connect(('10.1.1.1', 1))
            return s.getsockname()[0]

    def __make_ssl_context(self):
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
    import sys
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s %(filename)s: %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

    from .discover_serial import DiscoverSerial
    discover = DiscoverSerial()
    server = DeviceServer(discover, 2*Config.get('device_scan_interval', 1))
    print("started server", server)

    while True:
        time.sleep(10)

if __name__ == "__main__":
    main()