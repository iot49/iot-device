# device_conifg.py

from .env import Env
from .utilities import cd
from glob import glob
from fnmatch import fnmatch
import yaml, os

"""
DeviceConfig (from yaml): name, uid, resources (rsync)

Sample yaml description:

robot-stm:
    uid: 2d:00:49:00:09:50:52:42:4e:30:39:20
    install-dir: /spi/lib
    include-patterns: 
        - "./**/*.py"
        - "./**/*.mpy"
        - "./**/"
    exclude-patterns:
        - "boot_out.txt"
        - "/data"
    libs:    # override IOT_LIBS
        - $IOT49/libs
        - iot49/libs
        - "~"
    resources:
        - pystone.py: /flash
        - copy.py
        - abc.py:
        - boot: 
            lib: $IOT49/boards/stm32/code
            unpack: true
            install-dir: /flash
            include-patterns:
                - "./**/*.py"
        - boot: 
            lib: $IOT49/boards/stm32/code
            unpack: false
            install-dir: /flash

"""

class DeviceConfig:
    
    def __init__(self, name, uid, spec):
        self._name = name
        self._uid = uid
        self._spec = spec
    
    @property
    def name(self):
        return self._name
    
    @property
    def uid(self):
        return self._uid

    @property
    def resource_files(self):
        """Returns a dict
           path_on_mcu -> (mtime, size, path_on_host)
        """
        result = {}
        sep = os.path.sep
        for r in self.resources:
            for f in r.files:
                mcu_file = sep.join(f.strip(sep).split(sep)[1:]) if r.unpack else f
                mcu_path = os.path.join(r.install_dir, mcu_file)
                host_path = Env.abs_path(os.path.join(r.lib, f))
                # add folders so rsync won't delete them
                p = mcu_path
                while p != '/':
                    p = os.path.dirname(p)
                    result[os.path.normpath(p)] = (0, -1, '')
                # add the file
                result[mcu_path] = (
                    os.path.getmtime(host_path), 
                    os.path.getsize(host_path), 
                    host_path
                )            
        return result

    @property
    def resources(self):
        return [ _Resource(self, r) for r in self._spec.get('resources', []) ]
    
    def __str__(self):
        from io import StringIO
        s = StringIO()
        s.write(f"DeviceConfig for {self.name} [{self.uid}]:\n")
        for r in self.resources:
            s.write(f"  {r}\n")
        # s.write(f"    spec:                 {self._spec}\n")
        return s.getvalue()

    @staticmethod
    def get_device_config(name_or_uid):
        """Return DeviceConfig for device with given name or uid
        Raises ValueError if device not found.
        """
        devs = DeviceConfig.get_device_configs()
        # check for name
        if devs.get(name_or_uid): return devs.get(name_or_uid)
        # search for uid
        for dev in devs.values():
            if dev.uid == name_or_uid: return dev
        raise ValueError(f"No such device: '{name_or_uid}'")

    @staticmethod
    def get_device_configs():
        """Return dict name --> DeviceConfig"""
        result = {}
        names = set()
        uids  = set()
        for dir in Env.iot_device_dirs():
            with cd(dir):
                for file in glob("*.yaml") + glob("*.yml"):
                    with open(file) as f:
                        for name, spec in yaml.safe_load(f.read()).items():
                            if name in names:
                                raise ValueError(f"File {file}: device '{name}' redefined")
                            names.add(name)
                            uid = spec.get('uid')
                            if not uid:
                                raise ValueError(f"File {file} device '{name}': field 'uid' is mandatory")
                            uids.add(uid)
                            result[name] = DeviceConfig(name, uid, spec)
        return result


"""Helpers"""

class _Library:
    """Folder with resources (e.g. Python files or packages, images, etc)"""
    
    def __init__(self, path):
        self._path = path
        p = Env.abs_path(path)
        if not os.path.isdir(p):
            raise ValueError(f"Library: '{path}' @ '{p}' is not a directory")
        self._resources = os.listdir(p)
        
    def has_resource(self, name):
        return name in self._resources
    
    @property
    def path(self):
        return self._path


class _Resource:
    """Single Resource specified in yaml file"""

    def __init__(self, dev, spec):
        self._dev = dev
        self._libs_cache = {}
        if isinstance(spec, str):
            self._resource = spec
            self._param = {}
        elif isinstance(spec, dict):
            self._resource = next(iter(spec.keys()))
            self._param = spec[self._resource]
            if not self._param:
                self._param = {}
            elif isinstance(self._param, str):
                self._param = { 'install-dir': self._param }
        else:
            # should never happen
            raise ValueError(f"Resource: expected dict, got {type(spec)}")

    @property
    def name(self):
        """Resource name, also file or directory name"""
        return self._resource
    
    @property
    def files(self):
        """List of files in this resource, path relative lib"""
        result = []
        includes = self._param.get('include-patterns', self._dev._spec.get('include-patterns', [ './**/*.py', './**/*.mpy', './**/' ]))
        excludes = self._param.get('exclude-patterns', self._dev._spec.get('exclude-patterns', [ 'boot_out.txt' ]))
        if isinstance(includes, str): includes = [ includes ]
        if isinstance(excludes, str): excludes = [ excludes ]
        path = os.path.join(self.lib, self.name)
        if os.path.isfile(Env.abs_path(path)): return [ self.name ]
        with cd(path):
            for inc in includes:
                for file in glob(inc, recursive=True):
                    if not os.path.isfile(file): continue
                    for ex in excludes:
                        if fnmatch(file, ex): continue
                    result.append(os.path.normpath(os.path.join(self.name, file)))
        return result

    @property
    def unpack(self):
        """"""
        return self._param.get('unpack', False) 

    @property
    def install_dir(self):
        """Directory on mcu in which this resource is located"""
        d = self._param.get('install-dir', self._dev._spec.get('install-dir', '/lib'))
        return d if d.startswith('/') else '/' + d

    @property
    def lib(self):
        """Library (folder) where this resource is located on the host.
        Checks libs in order & returns first match."""       
        for lib_name in self._libs:
            if not lib_name: continue
            if not lib_name in self._libs_cache:
                self._libs_cache[lib_name] = _Library(lib_name)
            l = self._libs_cache.get(lib_name)
            if l.has_resource(self.name):
                return l.path
        raise ValueError(f"Resource {self.name} not found in libraries {self._libs}")

    @property
    def _libs(self):
        """Path of libraries to search for this resource"""
        libs = self._param.get('lib', self._dev._spec.get('libs', Env.iot_lib_dirs()))
        return libs if isinstance(libs, list) else [ libs ]

    def __str__(self):
        return f"Res {self.name:22} install-dir={self.install_dir:22} lib={self.lib}"