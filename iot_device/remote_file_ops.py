from .remote_exec import RemoteError
from .remote_functions import RemoteFunctions
import logging, time, os, ast

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class OutputWrapper:
    def __init__(self, output):
        self.output = output
    def ans(self, val):
        if self.output:
            self.output.ans(val)
    def err(self, val):
        raise RemoteError(val)

class RemoteFileOps(RemoteFunctions):

    def _remote_exec(self, code, output=None):
        try:
            return self._remote.exec(f"exec({repr(code)}, __iot49__)", OutputWrapper(output))
        except RemoteError:
            # upload function code
            self._remote.exec(f"import os\n__iot49__ = {'{}'}\nexec({repr(_remote_functions)}, __iot49__)")
            # try again ...
            return self._remote.exec(f"exec({repr(code)}, __iot49__)", output)

    def makedirs(self, path):
        """Make all directories required for path. No-op if directories exist."""
        self.disable_write_protection()
        self._remote_exec(f"makedirs({repr(path)})")

    def rm_rf(self, path):
        """rm -rf path"""
        self.disable_write_protection()
        self._remote_exec(f"rm_rf({repr(path)})")

    def cat(self, path, output):
        """Show contents of path on console"""
        self._remote_exec(f"cat({repr(path)})", output)

    def get_time(self):
        """Get struct time from mcu"""
        st = self._remote_exec(f"get_time()").decode()
        if len(st) < 9:
            st += (-1, )
        return st

    def sync_time(self, tolerance=5):
        """Synchronize mcu time to host if they differ by more than tolerance seconds"""
        self._remote_exec(f"set_time({tuple(time.localtime())}, {tolerance})")

    def rlist(self, path, output=None):
        return self._remote_exec(f"rlist({repr(path)})", output)

    def fget(self, mcu_file, host_file, chunk_size=256):
        """Copy from microcontroller to host"""
        self.exec(f"f=open('{mcu_file}', 'rb')\nr=f.read")
        with open(host_file, 'wb') as f:
            while True:
                data = bytearray()
                data.extend(self.exec(f"print(r({chunk_size}))"))
                assert data.endswith(b"\r\n")
                try:
                    data = ast.literal_eval(str(data[:-2], "ascii"))
                    if not isinstance(data, bytes):
                        raise ValueError("Not bytes")
                except (UnicodeDecodeError, ValueError) as e:
                    raise RemoteError(f"fget: Could not interpret received data: {str(e)}")
                if not data: break
                f.write(data)
        self.exec("f.close()")

    def fput(self, host_file, mcu_file, chunk_size=256):
        """Copy from host to microcontroller"""
        logger.error(f"fput({host_file}, {mcu_file})")
        self.disable_write_protection()
        self.makedirs(os.path.dirname(mcu_file))
        if not os.path.isfile(host_file): return
        self.exec(f"f=open('{mcu_file}','wb')\nw=f.write")
        with open(host_file, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data: break
                self.exec(f"w({repr(data)})")
        self.exec("f.close()")

    def disable_write_protection(self):
        # disable CircuitPython flash write protection
        self._remote_exec(f"unprotect()")



###############################################################################
# code snippet (runs on remote)

_remote_functions = """
import os, time

def unprotect():
    try:
        import storage
        storage.remount('/', readonly=False)
    except ImportError:
        pass

def makedirs(path):
    try:
        os.mkdir(path)
    except OSError as e:
        if e.args[0] == 2:
            # no such file or directory, create parent first
            makedirs(path[:path.rfind('/')])
            os.mkdir(path)
        elif e.args[0] == 17:
            pass
        else:
            raise

def rm_rf(path):
    try:
        mode = os.stat(path)[0]
        if mode & 0x4000 != 0:
            for file in os.listdir(path):
                rm_rf(path + '/' + file)
            os.rmdir(path)
        else:
            os.remove(path)
    except OSError as e:
        if e.args[0] == 2:
            pass
        else:
            raise

def cat(path):
    with open(path) as f:
        while True:
            line = f.readline()
            if not line:
                break
            print(line, end="")

def get_time():
    print(time.localtime(), end="")

def set_time(st, tolerance=5):
    host  = time.mktime(st)
    local = time.time()
    if abs(host-local) < tolerance:
        return
    try:
        # CircuitPython
        import rtc
        rtc.RTC().datetime = st
    except ImportError:
        # MicroPython
        import machine
        # convert to Micropython's non-standard ordering ...
        st = list(st)
        st.insert(3, st[6])
        st[7] = 0
        machine.RTC().datetime(st[:8])

t_off = 0
try:
    import machine
    t_off = 946684800
except ImportError:
    pass

def rlist(path, level=0):
    stat = os.stat(path)
    fsize = stat[6]
    mtime = stat[7] + t_off
    if stat[0] & 0x4000:
        print("D,{},{},{},0".format(level, repr(path), mtime))
        os.chdir(path)
        for p in sorted(os.listdir()):
            if p.startswith('.'): continue
            rlist(p, level+1)
        try:
            # loboris esp32 throws error when in /flash
            os.chdir('..')
        except:
            pass
    else:
        print("F,{},{},{},{}".format(level, repr(path), mtime, fsize))
"""
