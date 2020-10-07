from iot_device import DeviceRegistry, DiscoverSerial, DiscoverNet, EvalException, Config
import sys, time


class Output:
    def ans(self, value):
        if isinstance(value, bytes): value = value.decode()
        print(value, flush=True, end="")

    def err(self, value):
        if isinstance(value, bytes): value = value.decode()
        print(value, flush=True, end="")


def main():
    # catalog of availble devices
    registry = DeviceRegistry()

    # create device scanners
    DiscoverSerial().register_listener(registry)
    DiscoverNet().register_listener(registry)

    # run code on all discovered devices
    while True:
        for dev in registry.devices():
            try:
                print(f"\n{'*'*20} {dev.name} {dev.connection} {'*'*(80-len(str(dev.name))-len(dev.connection))}")
                with dev as repl:
                    print(repl.eval("print('power of 3', 3**10)").decode())
                    output = Output()
                    repl.eval("print('power of 2', 2**10)", output)
                    print("\n----- cat boot.by")
                    repl.cat(output, "boot.py")
                    print("\n----- rlist")
                    repl.rlist(output)
            except:
                pass
        time.sleep(1)


if __name__ == "__main__":
    main()