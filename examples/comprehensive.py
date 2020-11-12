from iot_device import DeviceRegistry, DiscoverSerial, DiscoverNet, EvalException, Config
import sys, time, logging

logger = logging.getLogger(__file__)


class Output:
    def ans(self, value):
        if isinstance(value, bytes): value = value.decode()
        print(value, flush=True, end="")

    def err(self, value):
        if isinstance(value, bytes): value = value.decode()
        print(value, flush=True, end="")

code = [

b"print(2**10)",

"""
for i in range(3):
    print(i, i**2, i**3)
""",

"print('4/sf)",

"""import time
time.sleep(2)""",

"a = 5",
"print(a)",
"softreset",
"print(a)"

]

def demo_eval(repl):
    for c in code:
        print("demo_eval")
        try:
            if c == "softreset":
                print("SOFTRESET")
                repl.softreset()
            elif c == "uid":
                print(f"UID {repl.uid}")
            else:
                print(f"EVAL {c}")
                repl.eval(c, Output())
        except EvalException as re:
            print(f"***** ERROR {re}")
        finally:
            print('-'*50)


def listfiles():
    # this function runs on the MCU ...
    from os import listdir
    return listdir()

def demo_functions(repl):
    print(f"listfiles (on mcu): {repl.eval_func(listfiles)}")
    fn = 'boot.py'
    print(f"cat({fn}):")
    repl.cat(Output(), fn)
    if (True): return
    print('\n', '-'*10)
    fn = 'delete_me.txt'
    repl.fget('lib/adafruit_requests.py', f'tmp/{fn}')
    print('\n', '-'*10)
    fn = 'delete_me.txt'
    repl.fput(f'tmp/{fn}', fn)
    print('\n', '-'*10)
    print(f"cat({fn})")
    repl.cat(Output(), fn)
    print(f"new file {fn} on mcu ...")
    print(f"listfiles: {repl.eval_func(listfiles)}")
    print("after rm ...")
    repl.rm_rf(fn)
    print(f"listfiles: {repl.eval_func(listfiles)}")

def demo_rsync(repl):
    # sync time ...
    print(f"before sync: get_time = {repl.get_time()}")
    repl.sync_time()
    print(f"after  sync: get_time = {repl.get_time()}")
    # rsync
    print('-'*10, 'rlist')
    repl.rlist(Output())
    print('-'*10, 'rdiff')
    repl.rdiff(Output())
    print('-'*10, 'rsync')
    repl.rsync(Output())


def main():
    logging.getLogger().setLevel(logging.INFO)

    # create device scanners
    DiscoverSerial()
    DiscoverNet()

    # run code on all discovered devices
    while True:
        for dev in DeviceRegistry.devices():
            try:
                print(f"\n{'*'*20} {dev.name} {dev.connection} {'*'*(80-len(str(dev.name))-len(dev.connection))}")
                with dev as repl:
                    output = Output()
                    demo_eval(repl)
                    demo_functions(repl)
                    demo_rsync(repl)
            except (ConnectionResetError, ConnectionRefusedError):
                pass
        time.sleep(1)


if __name__ == "__main__":
    main()