from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sonic_platform_base import device_base
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.eeprom_rw import EepromReadWriteMixin


class OeId(Enum):
    BROADCOM_DAVISSON = 1


class ElsfpId(Enum):
    pass


@dataclass
class CpoHardwareInfo:
    oe_id: OeId
    elsfp_id: Optional[ElsfpId]
    elsfp_low_mem_offset: int = 0


class CpoApiFactory(ABC):
    def __init__(self, device: "CpoDeviceBase"):
        self._device = device

    def _create_api(self, codes_class, mem_map_class, api_class):
        mem_map = mem_map_class(codes_class, self._device.bank)
        eeprom = XcvrEeprom(self._device.read_eeprom, self._device.write_eeprom, mem_map)
        return api_class(eeprom)

    @abstractmethod
    def create_api(self):
        raise NotImplementedError


class CpoDeviceBase(device_base.DeviceBase, EepromReadWriteMixin):
    def __init__(self, hardware_id: CpoHardwareInfo, bank: int = 0):
        self.bank = bank
        self.hardware_id = hardware_id
        self._api = None
        self._api_factory = self._make_api_factory()

    @abstractmethod
    def _make_api_factory(self) -> CpoApiFactory:
        raise NotImplementedError

    def refresh_api(self):
        self._api = self._api_factory.create_api()

    def get_api(self):
        if self._api is None:
            self.refresh_api()
        return self._api

    def remove_api(self):
        self._api = None


class CpoBase(device_base.DeviceBase):
    def __init__(self, hardware_id: CpoHardwareInfo, oe: "OeBase", elsfp: "ElsfpBase"):
        self.hardware_id = hardware_id
        self.oe = oe
        self.elsfp = elsfp

    def refresh_xcvr_api(self):
        self.oe.refresh_api()
        self.elsfp.refresh_api()

    def get_xcvr_api(self):
        # We always default to the OE API for CPO. If the ELSFP API is required,
        # then that can be accessed via self.elsfp.get_api() directly.
        return self.oe.get_api()

    def remove_xcvr_api(self):
        self.oe.remove_api()
        self.elsfp.remove_api()

    # Low-power mode and reset apply to the CPO virtual module as a whole, through
    # its module controller. By default that is the module API returned by
    # get_xcvr_api(), which xcvrd also uses to provision the module. Platforms
    # with a different controller model override these methods. A controller may
    # serve several ports, in which case every port it serves is affected.

    def get_lpmode(self):
        """
        Retrieves the low-power mode of the CPO virtual module

        Returns:
            A boolean, True if the module is in low-power mode, False if not,
            or None if it cannot be determined
        """
        api = self.get_xcvr_api()
        return api.get_lpmode() if api is not None else None

    def set_lpmode(self, lpmode):
        """
        Puts the CPO virtual module in low-power or full-power mode

        Args:
            lpmode: A boolean, True to enter low-power mode, False to leave it

        Returns:
            A boolean, True if successful, False if not
        """
        api = self.get_xcvr_api()
        return api.set_lpmode(lpmode) if api is not None else False

    def reset(self):
        """
        Resets the CPO virtual module, returning its settings to their defaults

        Returns:
            A boolean, True if successful, False if not
        """
        api = self.get_xcvr_api()
        return api.reset() if api is not None else False
