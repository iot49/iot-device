import pytest
from iot_device import DeviceRegistry, RemoteError

registry = DeviceRegistry()

@pytest.mark.parametrize("device", registry.devices)
def test_exec(device):
    # test remote code execution
    with device as repl:
        assert repl.exec("print(4*9)").decode().strip() == '36'
        impl = repl.exec("import sys; print(sys.implementation.name)").decode().strip()
        assert impl == "micropython" or impl == "circuitpython"

@pytest.mark.parametrize("device", registry.devices)
def test_device_info(device):
    # test device info helpers
    with device as repl:
        platform = repl.platform
        assert platform != None and len(platform) > 3

        impl = repl.implementation
        assert impl == 'micropython' or impl == 'circuitpython'
