import pytest, os, tempfile
from iot_device import DeviceRegistry, RemoteError

registry = DeviceRegistry()

def ex(repl, code):
    return repl.exec(code).decode().strip()

class DataConsumer:
    def __init__(self):
        self.data = ""
    def data_consumer(self, data):
        self.data += data


@pytest.mark.parametrize("device", registry.devices)
def test_mkdirs_rm(device):
    # create and delete folders
    with device as repl:
        # start from known state
        repl.rsync(DataConsumer().data_consumer, projects=device.projects, dry_run=False, upload_only=False)

        # create directories
        repl.makedirs('a/b/c')
        assert ex(repl, "import os;  print(os.listdir('a/b'))") == "['c']"

        # delete directories
        repl.rm_rf('a')
        assert 'a' not in eval(ex(repl, 'import os; print(os.listdir())')), "rsync folder delete"

        # verify back to original
        out = DataConsumer()
        repl.rsync(out.data_consumer, projects=device.projects, dry_run=False, upload_only=False)
        assert "Directories match" in out.data

@pytest.mark.parametrize("device", registry.devices)
def test_cp(device):
    # Copy file with random binary data to mcu and back, verify contents
    with device as repl:
        with tempfile.TemporaryDirectory() as dir:
            # print('created temporary directory', dir)
            fname1 = os.path.join(dir, 'data1.bin')
            fname2 = os.path.join(dir, 'data2.bin')
            N = 1000
            data = bytes(os.urandom(N))
            with open(fname1, 'wb') as f:
                f.write(data)
            repl.fput(fname1, 'x.bin')
            repl.fget('x.bin', fname2)
            with open(fname2, 'rb') as f:
                assert f.read() == data
            repl.rm_rf('x.bin')
