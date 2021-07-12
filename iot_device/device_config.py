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
    path: $IOT_PROJECTS
    resources:
        - pystone.py: /flash
        - copy.py
        - abc.py:
        - boot: 
            path: my_project/code
            unpack: true
            install-dir: /flash
            include-patterns:
                - "./**/*.py"
        - boot: 
            lib: ~/my_own_library
            unpack: false
            install-dir: /flash

"""

class DeviceConfig:
    
    def __init__(self, name, uid, spec, file):
        """Not usually called directly. Use get_device_config(s)"""
        self._name = name
        self._uid = uid
        self._spec = spec
        self._file = file
    
    @property
    def name(self):
        return self._name
    
    @property
    def uid(self):
        return self._uid

    @property
    def file(self):
        return self._file

    def __str__(self):
        from io import StringIO
        s = StringIO()
        s.write(f"Configuration (in {self.file}):\n")
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
        raise ValueError(f"No configuration found for: '{name_or_uid}'")

    @staticmethod
    def get_device_configs():
        """Return dict name --> DeviceConfig"""
        result = {}
        names = set()
        uids  = set()
        try:
            with cd(Env.iot_devices()):
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
                            result[name] = DeviceConfig(name, uid, spec, file)
        except FileNotFoundError as e:
            # folder Env.iot_devices() does not exist
            pass
        return result

    @property
    def resources(self):
        return [ _Resource(self, r) for r in self._spec.get('resources', []) ]
    
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
                host_path = Env.expand_path(os.path.join(r.path, f))
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

class _Resource:
    """Single Resource specified in yaml file"""

    def __init__(self, dev, spec):
        self._dev = dev
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
        path = os.path.join(self.path, self.name)
        if os.path.isfile(Env.expand_path(path)): return [ self.name ]
        try:
            with cd(path):
                for inc in includes:
                    for file in glob(inc, recursive=True):
                        if not os.path.isfile(file): continue
                        for ex in excludes:
                            if fnmatch(file, ex): continue
                        result.append(os.path.normpath(os.path.join(self.name, file)))
        except OSError:
            pass
        return result

    @property
    def unpack(self):
        """Upload directory (unpack False) or contents (unpack True)"""
        if 'unpack' in self._param:
            return self._param['unpack'] 
        full_path = os.path.join(self.path, self.name)
        return os.path.isdir(full_path) and not os.path.isfile(os.path.join(full_path, '__init__.py'))

    @property
    def install_dir(self):
        """Directory on mcu in which this resource is located"""
        d = self._param.get('install-dir', self._dev._spec.get('install-dir', '/'))
        return d if d.startswith('/') else '/' + d

    @property
    def path(self):
        """Library (folder) where this resource is located on the host."""
        p = self._param.get('path', self._dev._spec.get('path', Env.iot_projects()))
        p = Env.expand_path(p)
        if not os.path.isabs(p):
            p = os.path.join(Env.iot_projects(), p)
            p = Env.expand_path(p)
        return p

    def __str__(self):
        # return f"{self.lib}/{self.name} -> {self.install_dir}"
        return f"Res {self.name:22} install-dir={self.install_dir:22} path={self.path}"
    