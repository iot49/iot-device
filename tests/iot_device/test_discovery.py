import pytest, time
from iot_device import RemoteError

from conftest import registry

def test_register_bogus_url():
    global registry
    with pytest.raises(ValueError):
        registry.register("foo")
    with pytest.raises(RemoteError):
        registry.register("mp://google.com:80")
    with pytest.raises(RemoteError):
        registry.register("mp://10.39.40.100:80")

def test_unregister():
    global registry
    with pytest.raises(ValueError):
        registry.unregister("foo")
    # unregister all
    devs = registry.devices
    n = len(devs)
    for dev in registry.devices:
        registry.unregister(dev.uid)
    # gone
    assert len(registry._devices) == 0
    # register again
    assert len(registry.devices) == n

devices = [
    ('test-esp32',      'serial'),
    ('test-esp32',      'ws'),
    # not available concurrently with mp
    # ('test-argon',      'serial'),
    ('test-argon',      'mp'),
    ('test-stm32',      'serial'),
    ('test-stm32-cop',  'serial'),
    ('test-samd',       'serial'),
]

@pytest.mark.parametrize("name, scheme", devices)
def test_suite(name, scheme):
    global registry
    for i in range(5):
        dev = registry.get_device(name, schemes=[scheme])
        if dev != None: break
        time.sleep(1)
    assert dev != None, f"Device {name}, {scheme} not present"
    assert dev.name  == name
    assert dev.scheme == scheme
