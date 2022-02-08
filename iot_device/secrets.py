from .env import Env


class Secrets:

    @staticmethod
    def get_attr(name, default=None):
        with open(Env.iot_secrets()) as f:
            cfg = {}
            exec(f.read(), cfg)
        return cfg.get(name, default)
