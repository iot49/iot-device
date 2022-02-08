from .eval import RemoteError
from .eval_rlist import EvalRlist
from .utilities import cd
from .env import Env

from termcolor import colored
from glob import glob
from fnmatch import fnmatch
from collections import OrderedDict

import time, os, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

"""File dicts:

mcu_files:
    dict[full_path] = (mtime, size)

host_files:
    host_path = os.path.join(package, file_path)
    dict[full_path] = (mtime, size, host_path)
"""

class EvalRsync(EvalRlist):
    """Add remote file synchronization"""

    def rsync(self, data_consumer, *,
            dry_run=True,
            upload_only=True):
        # synchronize micrcontroller flash to host
        #   dry_run: only print out differences, do not copy any files
        #   upload_only: do not delete files on microcontroller that are not also on host
        if not dry_run:
            # sync mcu time to host if they differ by more than 3 seconds
            self.sync_time(3)
        # mcu files & excludes
        mcu_files = self.rlist('/', data_consumer)
        mcu_files.pop("/boot_out.txt", None)
        # host files
        host_files = self.device.config.resource_files
        del_, add_, upd_ = self._diff(mcu_files, host_files)
        same = True
        for dst_file in del_:
            # delete first (protect against a bug that deletes what was just copied)
            if not upload_only:
                same = False
                data_consumer(colored(f"DELETE  {dst_file}\n", 'red'))
                if not dry_run:
                    self.rm_rf(dst_file)
        for dst_file, src_file in add_.items():
            # no feedback about directory creation
            if os.path.isfile(src_file):
                same = False
                data_consumer(colored(f"ADD     {dst_file}\n", 'green'))
            if not dry_run:
                self.fput(src_file, dst_file)
        for dst_file, src_file in upd_.items():
            same = False
            data_consumer(colored(f"UPDATE  {dst_file}\n", 'blue'))
            if not dry_run:
                self.fput(src_file, dst_file)
        if same:
            data_consumer(colored("Directories match\n", 'green'))

    def _diff(self, mcu_files, host_files):
        # determine difference between host (projects) and mcu
        # delete files not on host
        to_delete = mcu_files.keys() - host_files.keys()
        # add files from host
        to_add = host_files.keys() - mcu_files.keys()
        # in both: may need updating
        to_update = set()
        for u in mcu_files.keys() & host_files.keys():
            mcu_time, mcu_size = mcu_files[u]
            host_time, host_size, _ = host_files[u]
            # mcu_size < 0 indicates directory
            if mcu_size < 0: continue
            if mcu_size != host_size or mcu_time < host_time:
                to_update.add(u)
        # convert to_add and to_update to ordered dicts full_path --> host_path
        return (
            sorted(to_delete, reverse=True),
            OrderedDict(sorted({ k: host_files[k][-1] for k in to_add }.items())),
            OrderedDict(sorted({ k: host_files[k][-1] for k in to_update }.items()))
        )
