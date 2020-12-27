from .eval import RemoteError
from .eval_file_ops import EvalFileOps
from datetime import datetime
from termcolor import colored

import time, os, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class EvalRlist(EvalFileOps):
    """Add file listing capabilities"""

    def rlist(self, path, output=None, show=False):
        """Return and opionally display files stored on remote"""
        out = RlistOutput(output, show)
        self.exec('import os')
        cwd = self.exec('print(os.getcwd(), end="")').decode()
        try:
            self.exec(f'os.chdir({repr(path)})')
            self._remote_exec(f"rlist('')", out)
        finally:
            self.exec(f'os.chdir({repr(cwd)})')
        return out.files


###############################################################################
# Collect output from _mcu_list

class TZ:
    # convert micropython localtime (e.g. mtime) to gmtime

    __ts = time.time()
    __localtime_gmtime = (datetime.fromtimestamp(__ts) - datetime.utcfromtimestamp(__ts)).total_seconds()

    @staticmethod
    def local2gmtime(local_time):
        return local_time - TZ.__localtime_gmtime

    @staticmethod
    def gmtime2local(gm_time):
        return gm_time + TZ.__localtime_gmtime


class RlistOutput(TZ):

    def __init__(self, output=None, show=False):
        # show: prints file list to output
        # (otherwise just progress, if output not None)
        self._output = output
        self._show = show
        self._level_offset = 0
        self._path_stack = []
        self._files = {}
        self._line_buffer = bytes()

    @property
    def files(self):
        return self._files

    def _indent(self, level):
        return ' '*4*(level + self._level_offset)

    def ans(self, b):
        # b could be any fragment or combination of lines!
        self._line_buffer += b
        while b'\r\n' in self._line_buffer:
            line, self._line_buffer = self._line_buffer.split(b'\r\n', 1)
            # print(f"line = {line}")
            kind, level, path, mtime, size = line.split(b',')
            path = eval(path)
            if len(path)<=0: continue
            level = int(level)
            size  = int(size)
            mtime = int(self.local2gmtime(int(mtime)))
            mtime_fmt = datetime.fromtimestamp(mtime).strftime("%b %d %H:%M %Y")
            full_path = os.path.join(*self._path_stack[:level], path)
            if kind == b'D':
                if size == 0:
                    # empty directory
                    self._files[full_path] = (mtime, -1)
                while len(self._path_stack) < level+1:
                    self._path_stack.append('')
                self._path_stack[level] = path
                if level != 0:
                    if self._show and self._output:
                        path += '/'
                        self._output.ans(f"{' '*7}  {mtime_fmt}  {self._indent(level)}{colored(path, 'green')}\n")
                else:
                    self._level_offset = -1
            else:
                self._files[full_path] = (mtime, size)
                if self._output:
                    if self._show:
                        self._output.ans(f"{int(size):7}  {mtime_fmt}  {self._indent(level)}{colored(path, 'blue')}\n")
                    elif len(self._files) > 50 and len(self._files) % 10 == 0:
                        # show progress
                        self._output.ans('.')

    def err(self, b):
        self._output.err(b)
