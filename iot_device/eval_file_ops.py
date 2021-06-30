from .eval import RemoteError
from .eval_defaults import EvalDefaults
import logging, time, os, io, ast


logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class EvalFileOps(EvalDefaults):
    """Add file system operations"""

    def makedirs(self, path:str):
        """Make all directories required for path. No-op if directories exist."""
        self._remote_exec(f"makedirs({repr(path)})", _makedirs_func)

    def rm_rf(self, path:str, r:bool=True, f:bool=True):
        """rm -rf path"""
        self._remote_exec(f"rm_rf({repr(path)}, {repr(r)}, {repr(f)})", _rm_rf_func)

    def cat(self, path:str, data_consumer=None):
        """Show contents of path on console"""
        return self._remote_exec(f"cat({repr(path)})", _cat_func, data_consumer=data_consumer)

    def get_time(self):
        """Get struct time from mcu"""
        st = self._remote_exec(f"get_time()", _time_funcs)
        if not st:
            raise RemoteError(f"Cannot read time from {self.device.name}")
        st = eval(st.decode())
        if len(st) < 9:
            st += (-1, )
        return st

    def sync_time(self, tolerance:float=5):
        """Synchronize mcu time to host if they differ by more than tolerance seconds"""
        self._remote_exec(f"set_time({tuple(time.localtime())}, {tolerance})", _time_funcs)

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

    def _remote_exec(self, code:str, func:str, data_consumer=None) -> bytes:
        """Execute code on remote; upload code if required"""
        try:
            logger.debug(f"_remote_exec({code})")
            return self.exec(f"exec({repr(code)}, __iot49__)", data_consumer)
        except (RemoteError, OSError):
            # upload __iot49__ and try again
            logger.debug(f"_remote_exec: upload {func}")
            self.exec("if not '__iot49__' in globals(): __iot49__ = {}")
            self.exec(f"exec({repr(func)}, __iot49__)")
            logger.debug("_remote_exec: 2nd try")
            return self.exec(f"exec({repr(code)}, __iot49__)", data_consumer)


###############################################################################
# code snippets (run on remote)

_makedirs_func = """
import os
def makedirs(path):
    try:
        os.mkdir(path)
    except OSError as e:
        if e.args[0]==2:
            makedirs(path[:path.rfind('/')])
            os.mkdir(path)
        elif e.args[0]==17:
            pass
        else:
            raise
"""

_rm_rf_func = """
import os
def rm_rf(path, r, f):
    try:
        mode = os.stat(path)[0]
    except OSError:
        return
    if mode & 0x4000 != 0:
        if r:
            for file in os.listdir(path):
                rm_rf(path + '/' + file, r, f)
        if f:
            os.rmdir(path)
    else:
        os.remove(path)
"""

_cat_func = """
def cat(path):
    with open(path) as f:
        while True:
            line = f.readline()
            if not line:
                break
            print(line, end="")
"""

_time_funcs = """
import time
def get_time():
    print(tuple(time.localtime()), end="")

def set_time(st, tolerance=5):
    host  = time.mktime(st)
    local = time.time()
    # delete this comment, stops working with ws
    if abs(host-local) < tolerance:
        return
    try:
        import rtc
        rtc.RTC().datetime = st
    except ImportError:
        import machine as m
        st = list(st)
        st.insert(3, st[6])
        st[7] = 0
        m.RTC().datetime(st[:8])
"""
