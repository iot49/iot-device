from glob import glob
from fnmatch import fnmatch
from types import ModuleType
import inspect, io, os, logging

logger = logging.getLogger('config')


class Config:

    @staticmethod
    def iot49_dir():
        return os.path.expanduser(os.getenv('IOT49', '~/iot49'))

    @staticmethod
    def get_attributes():
        def filt(elem):
            k, v = elem
            skip = isinstance(v, ModuleType) or callable(v) or k == 'logger'
            return not skip
        cfg = Config.get_config()
        del cfg['__builtins__']
        return dict(filter(filt, cfg.items()))

    @staticmethod
    def get_attr(name, default=None):
        c = Config.get_config()
        return c.get(name, default)

    @staticmethod
    def get_packages():
        c = Config.get_config()
        return c['Package'].get_packages()

    @staticmethod
    def get_package(name):
        c = Config.get_config()
        return c['Package'].get_package(name)

    @staticmethod
    def get_device_configs():
        c = Config.get_config()
        return c['DeviceConfig'].get_devices()

    @staticmethod
    def get_device_config(name_or_uid):
        c = Config.get_config()
        return c['DeviceConfig'].get_device(name_or_uid)

    @staticmethod
    def get_config():
        """Load configuration from cache or disk."""
        from .utilities import cd
        from . import config
        cfg = {}
        src = inspect.getsource(config)
        exec(src, cfg)
        file = 'config'
        try:
            with cd(os.path.join(Config.iot49_dir(), 'config')):
                for file in glob('./**/*.py', recursive=True):
                    with open(file) as f:
                        try:
                            exec(f.read(), cfg)
                        except SyntaxError as e:
                            raise SyntaxError(f"{e.text.strip()}: {e.msg}, line {e.lineno} file {file}")
        except (NameError, OSError) as ne:
            logger.error("{} while reading {}".format(ne, file))
            raise
        except SyntaxError as se:
            logger.error("{} in {}".format(se, file))
            raise
        return cfg


class Package:

    # dict name -> Package
    __PACKAGES = {}

    @staticmethod
    def get_packages():
        return Package.__PACKAGES

    @staticmethod
    def get_package(name):
        if '/' in name:
            # path, not package name: create package on the fly
            return Package(name, name)
        return Package.__PACKAGES.get(name)

    def __init__(self, name, src, dst='', requires=[], includes=None, excludes=None):
        # src: list of dirs or files relative to $IOT49
        #      may also the name of a single dir or file
        # dst: path prefix where files will be installed on microcontroller, e.g. lib
        if name in Package.__PACKAGES:
            raise ValueError(f"Redefinition of Package '{name}'")
        self._name = name
        if isinstance(src, str): src = [src]
        self._src = src
        self._mcu_dest = dst
        if isinstance(requires, str): requires = [requires]
        self._requires = requires
        self._includes = includes or ['./**/*.py', './**/*.mpy', './**/']
        self._excludes = excludes or ['boot_out.txt']
        # don't register "on the fly" packages
        if not '/' in name:
            Package.__PACKAGES[name] = self

    @property
    def name(self):
        return self._name

    @property
    def mcu_dest(self):
        # path where files are to be installed on the MCU
        # e.g. 'lib'
        return self._mcu_dest

    def files(self):
        result = {}  # file -> path
        for req in self._requires:
            result.update(self.get_package(req).files())
        for src in self._src:
            path = os.path.join(Config.iot49_dir(), src)
            if os.path.isfile(path):
                p_, f_ = os.path.split(src)
                result[f_] = p_
                continue
            if not os.path.isdir(path):
                logger.warn(f"Folder/file '{path}' not found (ignored)")
                continue
            from iot_device import cd
            with cd(path):
                for inc in self._includes:
                    for file in glob(inc, recursive=True):
                        for ex in self._excludes:
                            if fnmatch(file, ex): continue
                        file = os.path.normpath(file)
                        result[file] = src
        return result

    def description(self):
        s = io.StringIO()
        s.write(f"Package {self._name}:\n")
        files = dict(sorted(self.files().items(), key=lambda item: item[0]))
        for a, b in files.items():
            s.write(f"  {a:40} from {b}\n")
        return s.getvalue()

    def __str__(self):
        return self._name



class DeviceConfig:

    # dict name --> device
    __DEVICES = {}

    @staticmethod
    def get_devices():
        return DeviceConfig.__DEVICES

    @classmethod
    def get_device(cls, name):
        dev = cls.__DEVICES.get(name)
        if dev: return dev
        # search for uid
        for dev in cls.__DEVICES.values():
            if dev.uid == name: return dev
        raise ValueError(f"No configuration for device '{name}'")

    def __init__(self, name, uid, **kwargs):
        self._dict = {
            'name': name,
            'uid': uid,
        }
        self._dict.update(kwargs)
        DeviceConfig.__DEVICES[name] = self

    def get_packages(self):
        names = self._dict.get('packages', [])
        if isinstance(names, str): names = [names]
        res = []
        for name in names:
            if not isinstance(name, str): name = name[0]
            p = Package.get_package(name)
            if p:
                res.append(p)
            else:
                logger.warn(f"No such package: '{name}' (skipped)")
        return res

    def files(self):
        """Returns a dict with:

        key:    file path
        value:  tuple of
                    mcu_path:  path prefix on mcu (relative to '/')
                    host_path: path prefix on host (relative to $IOT49)
        """
        res = {}
        default_dest = self._dict.get('dest', '')
        for pkg_name in self._dict.get('packages', []):
            if isinstance(pkg_name, str):
                dest = default_dest
                name = pkg_name
            else:
                dest = pkg_name[1]
                name = pkg_name[0]
            pkg = Package.get_package(name)
            dest = os.path.join('/', dest, pkg.mcu_dest)
            for k,v in pkg.files().items():
                res[k] = (dest, v)
        return res

    def __getattr__(self, name):
        return self._dict.get(name)

    def description(self):
        s = io.StringIO()
        s.write(f"Device {self._dict.get('name')}:")
        for k,v in self._dict.items():
            if k == 'name': continue
            s.write(f"    {k} = {v}\n")
        return s.getvalue()

    def __str__(self):
        return f"DeviceConfig for {self._dict.get('name')} ({self._dict.get('uid')})"
