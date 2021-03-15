#!/usr/bin/env python3

print('\n'*10)

from iot_device import device_registry
from examples import simple, comprehensive

examples = [
    device_registry.main,   # 0
    simple.main,            # 1
    comprehensive.main,     # 2
]

examples[1]()
