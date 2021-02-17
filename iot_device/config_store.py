#!/usr/bin/env python3

from .version import __version__
import sys
import os
import logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


"""Singleton for accssing configuration files"""


class Config:

    __CONFIG_FOLDER = os.path.expanduser(os.getenv('IOT49', '~/iot49'))
    __CONFIG_CACHE = {}
    __DEFAULT_KEY = {
        'config.py': 'value',
        'devices.py': 'uid',
    }

    @staticmethod
    def iot49_dir():
        return Config.__CONFIG_FOLDER

    @staticmethod
    def get(name, default=None, *, attribute=None):
        """Get configuration value
        Examples:
            get('wifi_pwd')
            get('wifi_pwd', 'secret')
            get('wifi_pwd', 'no doc', attribute='doc')
        """
        config = Config.get_config('config.py')
        c = config.get(name, {} if attribute else default)
        if attribute:
            return c.get(attribute, default)
        return c

    @staticmethod
    def get_secret(name, default=None):
        secrets = Config.get_config('../secrets/secrets.py')
        return secrets.get(name, default)

    @staticmethod
    def get_device(name_or_uid, attribute, default=None):
        """Get device attribute
        Examples:
            get_device('esp32', 'projects', ['base'])
            get_device('esp32', 'uid')
            get_device('esp32', 'name')
        """
        devices = Config.get_config('devices.py').get('devices', {})
        return devices.get(name_or_uid, {}).get(attribute, default)

    @staticmethod
    def get_config(file='config.py'):
        """Load configuration from cache or disk."""
        config = {}
        # check mtime
        config_file = os.path.join(Config.__CONFIG_FOLDER, 'config', file)
        if os.path.isfile(config_file):
            mtime = os.path.getmtime(config_file)
            # check cache
            config, last_mtime = Config.__CONFIG_CACHE.get(file, (None, 0))
            if config and mtime <= last_mtime:
                return config
            try:
                config = {}
                exec("""
devices = {}

def device(**kwargs):
    if not 'uid' in kwargs:
        raise ValueError(f'devices.py: "uid" not defined in {kwargs}')
    if not 'name' in kwargs:
        raise ValueError(f'devices.py: "name" not defined in {kwargs}')
    devices[kwargs['uid']]  = kwargs
    devices[kwargs['name']] = kwargs
                """, config)
                exec(f"host_dir = '{Config.__CONFIG_FOLDER}'", config)
                with open(config_file) as f:
                    exec(f.read(), config)
                del config['__builtins__']
                Config.__CONFIG_CACHE[file] = (config, mtime)
            except (NameError, OSError) as ne:
                logger.error("{} while reading {}".format(ne, config_file))
                raise
            except SyntaxError as se:
                logger.error("{} in {}".format(se, config_file))
                raise
        return config
