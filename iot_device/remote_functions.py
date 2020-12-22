from .remote_exec import RemoteExec, RemoteError
import os, logging

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class RemoteFunctions:

    def __init__(self, remote_exec):
        self._remote = remote_exec

    def uid(self):
        """uid of remote, no permanent code upload"""
        return self.exec(_uid).decode()

    def implementation(self):
        return self.exec("import sys; print(sys.implementation.name, end='')").decode()

    """
    iot_device distinguishes between communication (Device and derivatives) and
    code execution (RemoteXXX).
    RemoteExec is the (abstract) base for code execution and provides "exec".
    Presently RemoteRepl is the only concrete implementation and provides "exec" via
    the MicroPython raw repl. Future implementations may use other means.

    Classes RemoteFileOps, RemoteRlist, RemoteRsync provide higher level functionality
    based on "exec". Since exec can be provided by several different implementations
    (e.g. RemoteRepl), these classes do not inherit from RemoteExec. Instead
    RemoteFunctions provides the features of RemoteExec by composition.
    (Multiple inheritance would be another option to achieve this.)

    Hence the delegates below.
    """
    def exec(self, code, output=None, timeout=None):
        return self._remote.exec(code, output, timeout)

    def eval_exec(self, code: str, output=None, timeout=None) -> None:
        """Try eval, then exec if the former fails"""
        self._remote.eval_exec(code, output, timeout)

    def softreset(self, output):
        self._remote.softreset(output)

    @property
    def device(self):
        return self._remote.device



###############################################################################
# code snippets (run on remote)

_uid = """
try:
    import machine
    print(":".join("{:02x}".format(x) for x in machine.unique_id()), end="")
except:
    import microcontroller
    print(":".join("{:02x}".format(x) for x in microcontroller.cpu.uid), end="")
"""
