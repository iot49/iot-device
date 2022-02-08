import pytest
from iot_device import DeviceRegistry, RemoteError

registry = DeviceRegistry()

devices = [
    ('test-argon',      'serial'),
]

@pytest.fixture
def device(request):
    name = request.param[0]
    scheme = request.param[1]
    device = registry.get_device(name, schemes=[scheme])
    assert device != None, f"Device {name}, {scheme} not present"
    return device

@pytest.mark.parametrize('device', devices, indirect=True)
def test_repl(device):
    assert device.name == 'test-argon', f"Device {device}"
