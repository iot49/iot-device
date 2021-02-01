from abc import ABC, abstractmethod


class Discover(ABC):
    """Base class for device discovery"""

    def __init__(self):
        pass

    @abstractmethod
    def scan(self) -> list:
        """url's of devices that are online"""
