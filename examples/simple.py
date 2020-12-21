from iot_device import DeviceRegistry, DiscoverSerial, DiscoverNet
from iot_device import RemoteError, Config
import sys, time


class Output:
    def ans(self, value):
        if isinstance(value, bytes): value = value.decode()
        print(value, flush=True, end="")

    def err(self, value):
        if isinstance(value, bytes): value = value.decode()
        print(value, flush=True, end="")


def main():
    # create device scanners
    DiscoverSerial()
    DiscoverNet()

    # give discovery some time
    time.sleep(1)

    devices = DeviceRegistry.devices()
    for dev in devices:
        print("{} {} {} {}\n".format(
            dev.name, ', '.join(dev.projects), dev.connection, dev.uid))


    # run code on all devices discovered so far
    for dev in DeviceRegistry.devices():
        print(f"\n{'*'*20} {dev.name} {dev.connection} {'*'*(80-len(str(dev.name))-len(dev.connection))}")
        with dev as repl:
            output = Output()
            print("softreset ...")
            repl.softreset()
            print("rlist ...")
            files = repl.rlist('/', output, show=True)
            for k,v in repl.rlist('/', output).items():
                print("{:20} {}".format(k, v))
            break
            print("get_time", repl.get_time())
            repl.sync_time(tolerance=1)
            print("get_time", repl.get_time())
            repl.eval_exec('globals()', output)
            repl.eval_exec("5-9", output)
            repl.eval_exec("a = 'hello world!'", output)
            repl.eval_exec("a", output)
            repl.exec("import sys; print(sys.platform)", output)
            print(f"\nimplementation: {repl.implementation()}")
            print("\n----- cat boot.by")
            repl.cat("boot.py", output)
            repl.makedirs("/flash/a/b/c")
            print("\n----- rlist")
            repl.rlist('/', output)
            repl.rm("/flash/a")
            repl.eval_exec('globals()', output)



if __name__ == "__main__":
    main()
