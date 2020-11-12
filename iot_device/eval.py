from abc import ABC, abstractmethod
import os, inspect, logging, time

logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


class DeviceError(Exception):
    pass


class Eval:
    """Abstract class encapsulating code evaluation on microcontroller, 
    extended by ReplEval."""

    def __init__(self, device):
        self._device = device

    @property
    def device(self):
        return self._device

    @property
    def uid(self) -> str:
        # Note: Device caches this, could retrieve from there
        # But - beware of recursion - Device calls Repl.uid!
        return self.eval_func(_uid)

    @property
    def implementation(self) -> str:
        # sys.implementation.name, e.g. micropython, circuitpython
        return self.eval_func(_implementation)

    @abstractmethod
    def eval(self, code: str, output=None) -> bytes:
        """Eval code on remote (Micro)Python VM.
           
        If output is None, evaluation results are returned from the function
        or a ReplExeption is raised in case of an error.

        Otherwise, output is a call-back handler class of the form

           class Output:
              def ans(value: bytes): pass
              def err(value: bytes): pass

        that receives results as they are sent from the microcontroller.
        Useful for interactive interfaces.
        """
        pass

    @abstractmethod
    def softreset(self):
        """Release all resources (variables and peripherals)"""
        pass

    def eval_func(self, func, *args, output=None, **kwargs) -> str:
        """Call func(*args, **kwargs) on (Micro)Python board."""
        try:
            logger.debug(f"eval_func: {func}({args})")
            args_arr = [repr(i) for i in args]
            kwargs_arr = ["{}={}".format(k, repr(v)) for k, v in kwargs.items()]
            func_str = inspect.getsource(func)
            func_str += 'import os\n'
            func_str += 'os.chdir("/")\n'
            func_str += 'result = ' + func.__name__ + '('
            func_str += ', '.join(args_arr + kwargs_arr)
            func_str += ')\n'
            func_str += 'if result: print(result)\n'
            logger.debug(f"eval_func: {func_str}")
            start_time = time.monotonic()
            result = self.eval(func_str, output)
            if result:
                try:
                    result = result.decode().strip()
                except UnicodeDecodeError:
                    logger.error(f"UnicodeDecodeError {result}")
                    result = str(result)
            logger.debug(f"eval_func: {func.__name__}({repr(args)[1:-1]}) --> {result},   in {time.monotonic()-start_time:.3} s")
            return result
        except SyntaxError as se:
            logger.error(f"Syntax {se}")


##########################################################################
# Code running on MCU

def _uid():
    try:
        import machine   # pylint: disable=import-error
        _id = machine.unique_id()
    except:
        try:
            import microcontroller   # pylint: disable=import-error
            _id = microcontroller.cpu.uid
        except:
            return None
    return ":".join("{:02x}".format(x) for x in _id)


def _implementation():
    import sys
    return sys.implementation.name
