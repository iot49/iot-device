from .config_store import Config
from termcolor import colored    # pylint: disable=import-error

from datetime import datetime
import os
import logging

logger = logging.getLogger(__file__)


"""
Device with added features:
* get/put files
* rlist, rdiff, rsync
"""


class EvalRsync:

    def __init__(self, *args, **kwargs):
        super(EvalRsync, self).__init__(*args, **kwargs)

    def rlist(self, output, path='/'):
        logger.debug(f"rlist {path}")
        self.__mcu_list(ListOutput(output), path)

    def rdiff(self, output, path='/', projects=['base']):
        mcu_files = self.mcu_files(output, path)
        host_files = self.host_files(path, projects)
        # add files from host
        to_add = host_files.keys() - mcu_files.keys()
        # delete files not on host
        to_delete = mcu_files.keys() - host_files.keys()
        # in both: may need updating
        to_update = set()
        for u in mcu_files.keys() & host_files.keys():
            mcu_time, mcu_size = mcu_files[u]
            _, host_time, host_size = host_files[u]
            # size < 0 indicates directory
            if (mcu_size != host_size) or ((mcu_time < host_time) and mcu_size >= 0):
                to_update.add(u)
        # convert to_add and to_update to dicts pointing to project
        return (
            { k: host_files[k][0] for k in to_add },
            sorted(to_delete, reverse=True),
            { k: host_files[k][0] for k in to_update }
        )

    def rsync(self, output, path='/', projects=['base'], dry_run=True):
        logger.debug(f"rsync {path} projects={projects}")
        if not dry_run:
            # sync mcu time to host if they differ by more than 3 seconds
            self.sync_time(3)
        add_, del_, upd_ = self.rdiff(output, path, projects)
        if add_ or del_ or upd_:
            for a,p in add_.items():
                # do not report redundant directory creation
                src_file = os.path.expanduser(os.path.join(Config.get('host_dir'), p, a))
                dst_file = a
                if os.path.isfile(src_file):
                    output.ans(colored(f"COPY    {a}\n", 'green'))
                if not dry_run:
                     self.fput(src_file, dst_file)
            for d in del_:
                output.ans(colored(f"DELETE  {d}\n", 'red'))
                if not dry_run:
                    self.rm_rf(d, recursive=True)
            for u,p in upd_.items():
                output.ans(colored(f"UPDATE  {u}\n", 'blue'))
                src_file = os.path.expanduser(os.path.join(Config.get('host_dir'), p, u))
                dst_file = u
                if not dry_run:
                    self.fput(src_file, dst_file)
        else:
            output.ans("Directories match\n")

    def mcu_files(self, output, path):
        """Dict of all files and directories on MCU.
            name -> ()
        """
        if path.endswith('/'):    path = path[:-1]
        if path.startswith('/'):  path = path[1:]
        path_output = PathOutput(output)
        self.__mcu_list(path_output, path)
        # output.ans('\n')
        return path_output.files

    def host_files(self, path, projects=['base']):
        """Dict of all files and directories on MCU.
            name -> ()
        """
        if path.endswith('/'):    path = path[:-1]
        if path.startswith('/'):  path = path[1:]
        files = dict()
        for proj in projects:
            full_path = os.path.join(Config.get('host_dir', '~'), proj)
            full_path = os.path.expanduser(full_path)
            self.__host_list(files, full_path, proj, path)
        return files

    def __mcu_list(self, output, path):
        """Request MCU to list files and process resuls via output objects"""
        # drop trailing and leading / from path
        self.eval_func(_mcu_list, path, 0, output=output)

    def __host_list(self, files, root, project, path, level=0):
        # add all files in root root/path to files dict
        full_path = os.path.join(root, path)
        if not os.path.exists(full_path): return
        mtime = os.path.getmtime(full_path)
        if os.path.isdir(full_path):
            # directory
            if len(path):
                files[path] = (project, mtime, -1)
            for p in os.listdir(full_path):
                if p.startswith('.'): continue
                self.__host_list(files, root, project, os.path.join(path, p), level+1)
        elif os.path.isfile(full_path):
            size = os.path.getsize(full_path)
            # file
            files[path] = (project, mtime, size)


#########################################################################
# code running on MCU

def _mcu_list(path, level):
    import os
    t_off = 0
    try:
        import machine
        t_off = 946684800
        machine
    except ImportError:
        pass
    try:
        stat = os.stat(path)
        fsize = stat[6]
        mtime = stat[7] + t_off
        if stat[0] & 0x4000:
            print(" D,{},{},{},0".format(level, repr(path), mtime))
            os.chdir(path)
            for p in os.listdir():
                _mcu_list(p, level+1)
            try:
                # esp32 throws error when in /flash
                os.chdir('..')
            except:
                pass
        else:
            print(" F,{},{},{},{}".format(level, repr(path), mtime, fsize))
    except:
        pass


#########################################################################
# Collect output from _mcu_list

class ListOutput:

    def __init__(self, output):
        self.output = output
        self._level_offset = 0

    def indent(self, level):
        return ' '*4*(level + self._level_offset)

    def ans(self, b):
        line = b.strip()
        if line:
            kind, level, path, mtime, size = line.split(b',')
            path = eval(path)
            if len(path)<=0: return
            level = int(level)
            ts = datetime.fromtimestamp(int(mtime))
            mtime = ts.strftime("%b %d %H:%M %Y")
            if kind == b'D':
                if level != 0:
                    path = path if path.endswith('/') else path+'/'
                    self.output.ans(f"{' '*7}  {mtime}  {self.indent(level)}{colored(path, 'green')}\n")
                else:
                    self._level_offset = -1
            else:
                self.output.ans(f"{int(size):7}  {mtime}  {self.indent(level)}{colored(path, 'blue')}\n")

    def err(self, b):
        self.output.err(b)


class PathOutput:

    def __init__(self, output):
        self.path_stack = []
        self.files = {}
        self.output = output

    def ans(self, b):
        line = b.strip()
        if line:
            kind, level, path, mtime, size = line.split(b',')
            path  = eval(path)
            # ignore files and directories with names that start with a period
            # these files, when created on the mcu, won't be deleted by rsync
            if len(path)<=0 or path.startswith('.'):
                return
            level = int(level)
            mtime = int(mtime)
            size  = int(size)
            full_path = os.path.join(*self.path_stack[:level], path)
            if kind == b'D':
                self.files[full_path] = (mtime, -1)
                while len(self.path_stack) < level+1:
                    self.path_stack.append('')
                self.path_stack[level] = path
            else:
                self.files[full_path] = (mtime, size)
                if len(self.files) > 50 and len(self.files) % 10 == 0:
                    self.output.ans('.')

    def err(self, b):
        self.output.err(b)
