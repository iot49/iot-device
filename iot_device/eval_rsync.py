from .config_store import Config

from termcolor import colored
from glob import glob
from datetime import datetime
import os, time, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


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

    def rdiff(self, output, projects=['base'], implementation='micropython'):
        mcu_files = self.mcu_files(output)
        host_files = self.host_files(projects, implementation)
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
                # print(f"***** update {u}:  (m {mcu_size} != h {host_size}) or (({mcu_time < host_time}) and {mcu_size >= 0})")
                # print(f"mcu_time={mcu_time}  host_time={host_time}  m-h={mcu_time - host_time}")
                to_update.add(u)
        # convert to_add and to_update to dicts pointing to project
        return (
            { k: host_files[k][0] for k in to_add },
            sorted(to_delete, reverse=True),
            { k: host_files[k][0] for k in to_update }
        )

    def rsync(self, output, projects=['base'], implementation='micropython', dry_run=True, upload_only=True):
        # synchronize micrcontroller flash to host
        #   project: list of projects to synchronize
        #   implementation: mpy architecture
        #   dry_run: only print out differences, do not copy any files
        #   upload_only: do not delete files on microcontroller that are not also on host
        logger.debug(f"rsync projects={projects}")
        if not dry_run:
            # sync mcu time to host if they differ by more than 3 seconds
            self.sync_time(3)
        add_, del_, upd_ = self.rdiff(output, projects, implementation)
        if add_ or del_ or upd_:
            for a,p in add_.items():
                src_file = os.path.expanduser(os.path.join(Config.get('host_dir'), p, a))
                dst_file = a
                # no feedback about directory creation
                if os.path.isfile(src_file):
                    output.ans(colored(f"COPY    {a}\n", 'green'))
                if not dry_run:
                    self.fput(src_file, dst_file)
            for d in del_:
                output.ans(colored(f"DELETE  {d}\n", 'red'))
                if not dry_run and not upload_only:
                    self.rm_rf(d, recursive=True)
            for u,p in upd_.items():
                output.ans(colored(f"UPDATE  {u}\n", 'blue'))
                src_file = os.path.expanduser(os.path.join(Config.get('host_dir'), p, u))
                dst_file = u
                if not dry_run:
                    self.fput(src_file, dst_file)
        else:
            output.ans(colored("Directories match\n", 'green'))

    def mcu_files(self, output):
        """Dict of all files and directories on MCU.
            name -> (level, path, mtime, size)
        """
        path_output = PathOutput(output)
        self.__mcu_list(path_output, '')
        return path_output.files

    def host_files(self, projects=['base'], implementation='micropython'):
        from iot_device import cd
        result = {}
        for project in projects:
            with cd(os.path.join(Config.get('host_dir'), project)):
                for src in glob('./**/*', recursive=True):
                    src = os.path.normpath(src)
                    mtime = os.path.getmtime(src)
                    size = -1 if os.path.isdir(src) else os.path.getsize(src)
                    if os.path.isfile(src) and src.endswith('.py'):
                        # check if a compiled version is available
                        mpy = src[:-3] + '.mpy'
                        proj = f".{project}-{implementation}"
                        mpy_file = os.path.join('..', proj, mpy)
                        if os.path.isfile(mpy_file):
                            mpy_mtime = os.path.getmtime(mpy_file)
                            if mpy_mtime >= mtime:
                                # compiled file available
                                result.pop(src, None)
                                result[mpy] = (proj, mpy_mtime, os.path.getsize(mpy_file))
                                continue                
                    result[src] = (project, mtime, size)
        # for k, v in result.items(): print(f"host_file {k:30} {v}")
        return result

    def __mcu_list(self, output, path):
        """Request MCU to list files and process resuls via output objects"""
        # drop trailing and leading / from path
        self.eval_func(_mcu_list, path, 0, output=output)


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

class ListOutput(TZ):

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
            ts = datetime.fromtimestamp(int(self.local2gmtime(int(mtime))))
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


class PathOutput(TZ):

    def __init__(self, output):
        self.path_stack = []
        self.files = {}
        self.output = output

    def ans(self, b):
        line = b.strip()
        if line:
            kind, level, path, mtime, size = line.split(b',')
            path  = eval(path)
            if len(path)<=0:  return
            level = int(level)
            mtime = int(self.local2gmtime(int(mtime)))
            size  = int(size)
            full_path = os.path.join(*self.path_stack[:level], path)
            if kind == b'D':
                self.files[full_path] = (mtime, -1)
                while len(self.path_stack) < level+1:
                    self.path_stack.append('')
                self.path_stack[level] = path
            else:
                # ignore files with names that start with a period
                # these files, when created on the mcu, won't be deleted by rsync
                if path.startswith('.'):
                    return
                self.files[full_path] = (mtime, size)
                if len(self.files) > 50 and len(self.files) % 10 == 0:
                    self.output.ans('.')

    def err(self, b):
        self.output.err(b)