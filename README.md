# IoT Device

Interface with Microcontrollers running MicroPython (or a derivative).
Supports device discovery, serial and wireless connections, code
evaluation and file upload and download.

Used by `iot-kernel` repo.

## Classes

* `DeviceRegistry`
  * catalog of currently available devices
  * maintained by `Discover` agents (`DiscoverNet`, `DiscoverSerial`)
  * devices automatically join and leave registry, e.g. in response to connecting to usb

* abstract `Device`
  * implementations `SerialDevice`, `NetDevice`
  * Not instantiated directly, get from `DeviceRegistry`
  * Property `uid` - unique, read from device and cached
  * Property `locked` - True if device is in used (e.g. `eval` from different process)
  * Context manager `with dev as repl: ...`
    * `repl.eval`, `softreset`, `rsync`

* `Config` (singleton)

* `certificate` - Used to encrypt repl over internet (`DeviceServer`)
