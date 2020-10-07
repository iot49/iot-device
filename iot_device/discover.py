from .device import Device

from abc import ABC, abstractmethod
from contextlib import contextmanager
from serial import SerialException
import logging, threading, time

logger = logging.getLogger(__file__)


class Discover(ABC):
    """Base class for device discovery"""

    def __init__(self):
        self._listeners = set()

    def register_listener(self, listener):
        """Subscribe to un/register_device events"""
        self._listeners.add(listener)

    def unregister_listener(self, listener):
        """Subscribe to un/register_device events"""
        self._listeners.remove(listener)

    def _register_device(self, id: str, device: Device):
        """Event dispatacher, used by derived classes."""
        for l in self._listeners:
            l.register_device(id, device)

    def _unregister_device(self, id: str):
        """Event dispatacher, used by derived classes."""
        for l in self._listeners:
            l.unregister_device(id)
