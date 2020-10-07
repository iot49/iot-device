#!/usr/bin/env python3

from .default_config import default_config, default_docs
from .version import __version__
import sys
import os

"""Singleton for accssing config.py, hosts.py and default_config.py"""


class Config:

    __config_cache = {}

    @staticmethod
    def get(name, default=None):
        """Return setting or default."""
        return Config.config().get(name, default)

    @staticmethod
    def getdoc(name):
        """Documentation for configuration variables"""
        return default_docs.get(name, "")

    @staticmethod
    def config():
        """Config as a dict."""
        return Config.get_config('config.py')

    @staticmethod
    def hosts():
        """Hosts as a dict."""
        return Config.get_config('hosts.py').get('hosts', {})

    @staticmethod
    def hostname2uid(host_name):
        """uid from host_name."""
        # brute force search is ok assuming small hosts table ...
        for k,v in Config.hosts().items():
            if isinstance(v, str) and v == host_name:
                return k
            if isinstance(v, dict) and v.get('name') == host_name:
                return k
        return host_name

    @staticmethod
    def uid2hostname(uid):
        """host_name from uid."""
        h = Config.hosts().get(uid)
        if isinstance(h, str):
            return h
        elif isinstance(h, dict):
            return h.get('name')
        return uid

    @staticmethod
    def host_projects(uid):
        """Projects list from uid."""
        h = Config.hosts().get(uid)
        if isinstance(h, dict):
            return h.get('projects')
        return ['base']

    @staticmethod
    def get_config(file='config.py'):
        """Load configuration from cache or disk."""
        config = default_config.copy()
        # check mtime
        iot49_dir = os.path.expanduser(os.getenv('IOT49', '~'))
        config_file = os.path.join(iot49_dir, 'mcu/base', file)
        if os.path.isfile(config_file):
            mtime = os.path.getmtime(config_file)
            # check cache
            config, last_mtime = Config.__config_cache.get(file, (None, 0))
            if not config or mtime > last_mtime:
                try:
                    config = default_config.copy()
                    with open(config_file) as f:
                        exec(f.read(), config)
                    del config['__builtins__']
                    config['version'] = __version__
                    Config.__config_cache[file] = (config, mtime)
                except NameError as ne:
                    sys.exit("{} while reading {}".format(ne, config_file))
                except OSError as ose:
                    sys.exit("{} while reading {}".format(ose, config_file))
                except SyntaxError as se:
                    sys.exit("{} in {}".format(se, config_file))
        return config


def main():
    print("Queries:")
    queries = [
        ('wifi_ssid', None),
        ('repl_adv_port', None),
        ('none', None),
    ]
    for q in queries:
        print("  {:20}  {}".format(q[0], Config.get(*q)))

    print("\nAll configuration values:")
    for k, v in Config.config().items():
        print("  {:20}  {}".format(k, v))

    print("\nHosts:")
    for k,v in Config.hosts().items():
        print(f"{k:50} -> {v}")

    print("\nHostname --> UID:")
    queries = [ 'nrf52', 'aqi_xenon', 'demo', 'scale_m4', 'esp32', 'hello_world' ]
    for q in queries:
        print("  {:20} {}".format(q, Config.hostname2uid(q)))

    print("\nUID --> Hostname:")
    uid = [ '0d:df:67:a7:f6:93:f4:39', 'cf:ec:09:07:44:72:94:6f', 'weird:uid:09:07:44' ]
    for u in uid:
        print("  {:40}  {:20}  {}".format(u,
                repr(Config.uid2hostname(u)),
                repr(Config.host_projects(u))))


if __name__ == "__main__":
    main()
