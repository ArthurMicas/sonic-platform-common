from mock import MagicMock

from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoBase, CpoHardwareInfo, OeId
from sonic_platform_base.sonic_xcvr.cpo.oe import OeBase
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpBase

# These tests don't depend on the specific ids (the factory's create methods
# are mocked); any valid id will do.
SOME_OE_ID = OeId.BROADCOM_DAVISSON
SOME_ELSFP_ID = None


class TestOeBase(object):
    def test_get_api_refreshes_when_none(self):
        oe = OeBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        oe._api_factory.create_api = MagicMock(return_value=fake_api)

        result = oe.get_api()

        oe._api_factory.create_api.assert_called_once_with()
        assert result is fake_api

    def test_get_api_cached(self):
        oe = OeBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        oe._api_factory.create_api = MagicMock(return_value=fake_api)

        # First call populates the cache, second call should reuse it.
        first = oe.get_api()
        second = oe.get_api()

        oe._api_factory.create_api.assert_called_once_with()
        assert first is second is fake_api


class TestElsfpBase(object):
    def test_get_api_refreshes_when_none(self):
        elsfp = ElsfpBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        elsfp._api_factory.create_api = MagicMock(return_value=fake_api)

        result = elsfp.get_api()

        elsfp._api_factory.create_api.assert_called_once_with()
        assert result is fake_api

    def test_get_api_cached(self):
        elsfp = ElsfpBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        elsfp._api_factory.create_api = MagicMock(return_value=fake_api)

        first = elsfp.get_api()
        second = elsfp.get_api()

        elsfp._api_factory.create_api.assert_called_once_with()
        assert first is second is fake_api


class TestCpoBase(object):
    def test_init(self):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        oe = OeBase(hardware_id)
        elsfp = ElsfpBase(hardware_id)

        cpo = CpoBase(hardware_id, oe, elsfp)

        assert cpo.hardware_id is hardware_id
        assert cpo.oe is oe
        assert cpo.elsfp is elsfp

    def test_get_xcvr_api_returns_oe_api(self):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        oe = OeBase(hardware_id)
        elsfp = ElsfpBase(hardware_id)
        oe_api = MagicMock()
        oe.get_api = MagicMock(return_value=oe_api)

        cpo = CpoBase(hardware_id, oe, elsfp)

        assert cpo.get_xcvr_api() is oe_api
        oe.get_api.assert_called_with()

    def _cpo_with_oe_api(self, oe_api):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        oe = OeBase(hardware_id)
        elsfp = ElsfpBase(hardware_id)
        oe.get_api = MagicMock(return_value=oe_api)
        elsfp.get_api = MagicMock()
        return CpoBase(hardware_id, oe, elsfp)

    def test_vmodule_controls_use_the_module_api(self):
        oe_api = MagicMock()
        oe_api.get_lpmode.return_value = True
        oe_api.set_lpmode.return_value = True
        oe_api.reset.return_value = True
        cpo = self._cpo_with_oe_api(oe_api)

        assert cpo.get_lpmode() is True
        assert cpo.set_lpmode(False) is True
        assert cpo.reset() is True
        oe_api.get_lpmode.assert_called_once_with()
        oe_api.set_lpmode.assert_called_once_with(False)
        oe_api.reset.assert_called_once_with()
        # The ELS endpoint is not used for vmodule controls.
        cpo.elsfp.get_api.assert_not_called()

    def test_vmodule_controls_without_module_api(self):
        cpo = self._cpo_with_oe_api(None)

        assert cpo.get_lpmode() is None
        assert cpo.set_lpmode(True) is False
        assert cpo.reset() is False

    def test_vmodule_controls_can_be_overridden(self):
        class ControllerCpo(CpoBase):
            def set_lpmode(self, lpmode):
                return "controller"

        oe_api = MagicMock()
        cpo = ControllerCpo(None, MagicMock(get_api=MagicMock(return_value=oe_api)), MagicMock())

        assert cpo.set_lpmode(True) == "controller"
        oe_api.set_lpmode.assert_not_called()
