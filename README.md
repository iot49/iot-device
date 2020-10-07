# IoT Device

Interface with Microcontrollers running MicroPython (or a derivative).
Supports device discovery, serial and wireless connections, code
evaluation and file upload and download.

See "examples/" folder for usage.

## Classes

* `DeviceRegistry`
  * catalog of currently available devices
  * maintained by `Discover` agents (`DiscoverNet`, `DiscoverSerial`)
  * devices automatically join and leave registry, e.g. in response to connecting to usb
  * `get_device(uid)` returns `Device` matching `uid` (obtained from microcontroller)
  
* abstract `Device`
  * implementations `SerialDevice`, `NetDevice`
  * Not instantiated directly, get from `DeviceRegistry`
  * Property `uid` - unique, read from device and cached
  * Property `locked` - True if device is in used (e.g. `eval` from different process)
  * Context manager `with dev as repl: ...`
    * `repl.eval`, `softreset`, `rsync`
    
* `Config` (singleton), reads configuration from:
  * `DefaultConfig`
  * `$IOT49/mcu/config.py` (see examples/config.py)
  * `$IOT49/mcu/hosts.py` (see examples/hosts.py)

* `certificate` - Used to encrypt repl over internet (`DeviceServer`)