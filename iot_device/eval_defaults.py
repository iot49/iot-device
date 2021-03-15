from .eval import Eval, RemoteError
import os, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class EvalDefaults(Eval):
    """Default implementations for select abstract methods of Eval"""

    @property
    def implementation(self):
        return self.exec("import sys; print(sys.implementation.name, end='')").decode()

    @property
    def platform(self):
        return self.exec("import sys; print(sys.platform, end='')").decode()
