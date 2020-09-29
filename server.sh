#!/usr/bin/env python3

import logging
logging.getLogger().setLevel(logging.INFO)

from iot_device import device_server
device_server.main()
