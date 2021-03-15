import pytest
from iot_device import DeviceRegistry, RemoteError

registry = DeviceRegistry()

@pytest.mark.parametrize("device", registry.devices)
def test_softreset(device):
    with device as repl:
        repl.exec("a = 1234")
        assert repl.exec("print(a)").decode().strip() == '1234'
        repl.softreset()
        try:
            repl.exec("print(a)")
        except RemoteError as e:
            assert "NameError" in str(e)


@pytest.mark.parametrize("device", registry.devices)
def test_abort(device):
    with device as repl:
        assert repl.exec("print(2**8)").decode().strip() == '256'
        # doesn't really do anything since no program is running anyway ...
        repl.abort()
        assert repl.exec("print(2**10)").decode().strip() == '1024'
