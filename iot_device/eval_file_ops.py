from .eval import RemoteError
from .eval_defaults import EvalDefaults
import logging, time, os, io, ast


logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class EvalFileOps(EvalDefaults):
    """Add file system operations"""

    def makedirs(self, path:str):
        """Make all directories required for path. No-op if directories exist."""
        self._remote_exec(f"makedirs({repr(path)})")

    def rm_rf(self, path:str, r:bool=True, f:bool=True):
        """rm -rf path"""
        self._remote_exec(f"rm_rf({repr(path)}, {repr(r)}, {repr(f)})")

    def cat(self, path:str, data_consumer=None):
        """Show contents of path on console"""
        return self._remote_exec(f"cat({repr(path)})", data_consumer)

    def get_time(self):
        """Get struct time from mcu"""
        st = self._remote_exec(f"get_time()")
        if not st:
            raise RemoteError(f"Cannot read time from {self.device.name}")
        st = eval(st.decode())
        if len(st) < 9:
            st += (-1, )
        return st

    def sync_time(self, tolerance:float=5):
        """Synchronize mcu time to host if they differ by more than tolerance seconds"""
        self._remote_exec(f"set_time({tuple(time.localtime())}, {tolerance})")

    def rlist(self, path:str, data_consumer=None):
        return self._remote_exec(f"rlist({repr(path)})", data_consumer)

    def fget(self, mcu_file:str, host_file:str, chunk_size:int=256):
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

    def fput(self, host_file:str, mcu_file:str, chunk_size:int=256):
        """Copy from host to microcontroller"""
        self.makedirs(os.path.dirname(mcu_file))
        if not os.path.isfile(host_file): return
        self.exec(f"f=open('{mcu_file}','wb')\nw=f.write")
        with open(host_file, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data: break
                self.exec(f"w({repr(data)})")
        self.exec("f.close()")

    def _remote_exec(self, code:str, data_consumer=None) -> bytes:
        """Execute code on remote; upload code if required"""
        try:
            return self.exec(f"exec({repr(code)}, __iot49__)", data_consumer)
        except (RemoteError, OSError) as e:
            if b'__iot49__' in e.traceback:
                # upload __iot49__ and try again
                self.exec(f"import os\n__iot49__ = {'{}'}\nexec({repr(_remote_functions)}, __iot49__)")
                return self.exec(f"exec({repr(code)}, __iot49__)", data_consumer)
            else:
                raise


###############################################################################
# code snippet (runs on remote)

_remote_functions = """
import os, time

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

def rm_rf(path, r, f):
    mode = os.stat(path)[0]
    if mode & 0x4000 != 0:
        if r:
            for file in os.listdir(path):
                rm_rf(path + '/' + file, r, f)
        if f:
            os.rmdir(path)
    else:
        os.remove(path)

def cat(path):
    with open(path) as f:
        while True:
            line = f.readline()
            if not line:
                break
            print(line, end="")

def get_time():
    print(tuple(time.localtime()), end="")

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
        os.chdir(path)
        d = os.listdir()
        print("D,{},{},{},{}".format(level, repr(path), mtime, len(d)))
        for p in sorted(d):
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
