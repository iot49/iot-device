import socket, os, struct


EOT = b'\x04'

class Client:

    def __init__(self, host, port):
        self._host = host
        self._port = port

    def exec(self, code):
        code_bytes = code.encode()
        self._sock.sendall(f"exec\x04{len(code)}\n".encode())
        self._sock.sendall(code_bytes)
        return self.__read_response()

    def eval_exec(self, code):
        code_bytes = code.encode()
        self._sock.sendall(f"eval\x04{len(code)}\n".encode())
        self._sock.sendall(code_bytes)
        return self.__read_response()

    def fput(self, src, dst, chunk_size=256):
        sz = os.path.getsize(src)
        self._sock.sendall(f"fput\x04{dst}\x04{sz}\n".encode())
        with open(src, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data: break
                self._sock.sendall(data)

    def fget(self, src, dst):
        self._sock.sendall(f"fget\x04{src}\n".encode())
        size = struct.unpack('!I', self._sock.recv(4))[0]
        with open(dst, 'wb') as f:
            while size > 0:
                data = self._sock.recv(min(1024, size))
                f.write(data)
                size -= len(data)

    def __read_response(self):
        # process response, format "OK _answer_ EOT _error_message_ EOT>"
        assert self._sock.recv(2) == b'OK'
        while True:
            ans = self._sock.recv(1024).split(EOT)
            if len(ans[0]): print(ans[0].decode())
            if len(ans) > 1:      # 1st EOT
                if len(ans[1]): print("ERR", ans[1].decode())
                if len(ans) > 2:  # 2nd EOT
                    return
                break             # look for 2nd EOT below
        # read error message, if any
        while True:
            ans = self._sock.recv(1024).split(EOT)
            if len(ans[0]): print("ERR", ans[0].decode())
            if len(ans) > 1:      # 2nd EOT
                break

    def __enter__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("connecting ...")
        self._sock.connect((self._host, self._port))
        return self

    def __exit__(self, *args):
        self._sock.sendall(b'bye\n')
        self._sock.close()


host = '10.39.40.129'
port = 65432


with Client(host, port) as client:
    client.fput('a.txt', 'dummy.txt')
    client.fget('dummy.txt', 'b.txt')
    print("EXEC", client.exec('print(5)'))
    code = [
        'import sys; a=5; b=7; b',
        '5-9',
        '2**948',
        'print(77)',
        'for i in range(5):\n    i**2',
        'dir(network)',
        'a=5',
        'a',
        'b=7; a',
        'a/0',
    ]
    for c in code:
        print(c)
        print(f"-->")
        client.eval_exec(c)
        print()
