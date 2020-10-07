import binascii
import os
import logging
import time

logger = logging.getLogger(__file__)


class EvalFops:

    def __init__(self, *args, **kwargs):
        super(EvalFops, self).__init__(*args, **kwargs)

    def file_size(self, path):
        return int(self.eval_func(_file_size, path))

    def makedirs(self, path):
        return self.eval_func(_makedirs, path)

    def rm_rf(self, path, recursive=False):
        return self.eval_func(_rm_rf, path, recursive)

    def cat(self, output, filename):
        self.eval_func(_cat, filename, output=output)

    def get_time(self):
        """Get struct time from mcu"""
        st = eval(self.eval_func(_get_time))
        if len(st) < 9:
            st += (-1, )
        return st

    def sync_time(self, tolerance=10):
        """Synchronize mcu time to host if difference is more than tolerance [sec]"""
        self.eval_func(_set_time, tuple(time.localtime()), tolerance)

    def device_characteristics(self):
        return eval(self.eval_func(_device_characteristics))


##########################################################################
# Code running on MCU

def _file_size(filepath):
    import os
    try:
        return os.stat(filepath)[6]
    except:
        return -1

# create directories recursively
def _makedirs(path):
    import os
    try:
        os.mkdir(path)
        return True
    except OSError as e:
        if e.args[0] == 2:
            # no such file or directory
            try:
                _makedirs(path[:path.rfind('/')])
                os.mkdir(path)
            except:
                return False
    return True

# equivalent of rm -rf path
def _rm_rf(path, recursive):
    import os
    try:
        mode = os.stat(path)[0]
        if mode & 0x4000 != 0:
            # directory
            if recursive:
                for file in os.listdir(path):
                    success = _rm_rf(path + '/' + file, recursive)
                    if not success:
                        return False
            os.rmdir(path)
        else:
            os.remove(path)
    except:
        return False
    return True

def _cat(path):
    with open(path) as f:
        while True:
            line = f.readline()
            if not line:
                break
            print(line, end="")

def _get_time():
    import time
    return tuple(time.localtime())

# set mcu time to timestamp if they differ by more than tolerance seconds
def _set_time(st, tolerance=5):
    import time
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

def _device_characteristics():
    import sys, time
    try:
        sys.stdout.buffer
        sys.stdin.buffer
        has_buffer = True
    except AttributeError:
        has_buffer = False

    try:
        import binascii
        has_binascii = True
        binascii
    except ImportError:
        has_binascii = False

    #     year  m  d  H  M  S   W  dy
    st = (2000, 1, 1, 0, 0, 0, -1, -1, -1)
    epoch = 946684800-time.mktime(st)

    return { 'has_buffer': has_buffer, 'has_binascii': has_binascii, 'time_offset': epoch }
