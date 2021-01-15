from .eval import Eval, Output, RemoteError
import os, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class EvalDefaults(Eval):
    """Default implementations for select abstract methods of Eval"""

    def uid(self):
        """uid of remote, no permanent code upload"""
        return self.exec(_uid).decode()

    def implementation(self):
        return self.exec("import sys; print(sys.implementation.name, end='')").decode()

    def platform(self):
        return self.exec("import sys; print(sys.platform, end='')").decode()

    def eval_exec(self, code: str, output:Output=None) -> None:
        """Try eval, then exec if the former fails"""
        return self.exec(_eval_exec.format(repr(code)), output)
        # return self.exec(code, output)

###############################################################################
# code snippets (run on remote)

_uid = """
uid = bytes(6)
try:
    import machine
    uid = machine.unique_id()
except:
    import microcontroller
    uid = microcontroller.cpu.uid
print(":".join("{:02x}".format(x) for x in uid), end="")
"""

# NameError clause if for ports that don't support compile
# (CircuitPython)

_eval_exec = """
_iot49_ = {}
try:
    eval(compile(_iot49_, '<string>', 'single'))
except SyntaxError:
    exec(_iot49_)
except NameError:
    try:
        r = eval(_iot49_)
        if r:
            print(r)
    except SyntaxError:
        exec(_iot49_)
finally:
    del _iot49_
"""
