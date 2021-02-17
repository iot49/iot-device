from .eval import RemoteError
from .eval_rlist import EvalRlist
from .config_store import Config
from .utilities import cd

from termcolor import colored
from glob import glob
from fnmatch import fnmatch

import time, os, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

class EvalRsync(EvalRlist):
    """Add remote file synchronization"""

    def rsync(self, data_consumer, *,
            projects=['base'],
            include_patterns = ['./**/*.py', './**/*.mpy', './**/'],
            exclude_patterns = [],
            implementation='micropython',
            dry_run=True,
            upload_only=True):
        # synchronize micrcontroller flash to host
        #   project: list of projects to synchronize
        #   implementation: mpy architecture
        #   include_patterns: host_files, using glob
        #   exclude_patterns: host_files, using fnmatch
        #   dry_run: only print out differences, do not copy any files
        #   upload_only: do not delete files on microcontroller that are not also on host
        logger.debug(f"rsync projects={projects}")
        # sync mcu time to host if they differ by more than 3 seconds
        if not dry_run:
            # done by individual operations (fput, rm, ...)
            self.sync_time(3)
        mcu_files = self.rlist(self.device.root, data_consumer)
        # excludes
        mcu_files.pop("boot_out.txt", None)
        for f in list(mcu_files):
            for exclude_pattern in exclude_patterns:
                if fnmatch(f, exclude_pattern):
                    mcu_files.pop(f, None)
        host_files = self._host_files(projects, include_patterns, exclude_patterns, implementation)
        add_, del_, upd_ = self._diff(mcu_files, host_files)
        if add_ or del_ or upd_:
            # print(add_, del_, upd_)
            for d in del_:
                # delete first (protect against a bug that deletes what was just copied)
                if not upload_only:
                    data_consumer(colored(f"DELETE  {d}\n", 'red'))
                    if not dry_run:
                        self.rm_rf(os.path.join(self.device.root, d))
            for a,p in add_.items():
                src_file = os.path.expanduser(os.path.join(Config.get('host_dir'), p, a))
                dst_file = a
                # no feedback about directory creation
                if os.path.isfile(src_file):
                    data_consumer(colored(f"COPY    {a}\n", 'green'))
                if not dry_run:
                    self.fput(src_file, dst_file)
            for u,p in upd_.items():
                src_file = os.path.expanduser(os.path.join(Config.get('host_dir'), p, u))
                dst_file = u
                data_consumer(colored(f"UPDATE  {u}\n", 'blue'))
                if not dry_run:
                    self.fput(src_file, dst_file)
        else:
            data_consumer(colored("Directories match\n", 'green'))

    def _diff(self, mcu_files, host_files):
        # determine difference between host (projects) and mcu
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

    def _host_files(self, projects=['base'],
                    include_patterns = ['./**/*', './**/'],
                    exclude_patterns = [],
                    implementation='micropython'):
        # returns { dict filename -> (project, mtime, size) }
        result = {}
        for project in projects:
            try:
                with cd(os.path.join(Config.get('host_dir'), project)):
                    for include_pattern in include_patterns:
                        for src in glob(include_pattern, recursive=True):
                            # excludes
                            for exclude_pattern in exclude_patterns:
                                if fnmatch(src, exclude_pattern):
                                    src = None
                                    break
                            if not src or src == './': continue
                            src = os.path.normpath(src)
                            mtime = os.path.getmtime(src)
                            size = -1 if os.path.isdir(src) else os.path.getsize(src)
                            if os.path.isfile(src) and src.endswith('.py'):
                                # check if a compiled version is available
                                mpy = src[:-3] + '.mpy'
                                proj = f".{project}-{implementation}"
                                mpy_file = os.path.join(Config.iot49_dir(), proj, mpy)
                                if os.path.isfile(mpy_file):
                                    mpy_mtime = os.path.getmtime(mpy_file)
                                    if mpy_mtime >= mtime:
                                        # compiled file available & newer

                                        result.pop(src, None)
                                        result[mpy] = (proj, mpy_mtime, os.path.getsize(mpy_file))
                                        continue
                            result[src] = (project, mtime, size)
            except ValueError: #FileNotFoundError:
                logger.warn("Project directory not found, {project}. Skipping.")
            # for k, v in result.items(): print(f"host_file {k:30} {v}")
        return result
