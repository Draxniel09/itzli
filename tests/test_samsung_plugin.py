import pytest
from unittest.mock import patch, MagicMock
from itzli.plugins.samsung import SamsungPlugin

@pytest.mark.asyncio
async def test_samsung_plugin_enable_test_mode_success():
    plugin = SamsungPlugin()
    
    with patch.object(plugin.serial_adapter, 'find_samsung_modem_port', return_value="/dev/ttyACM0"):
        with patch.object(plugin, '_sync_at_command', return_value=(True, "OK")):
            result = await plugin.execute_action("ENABLE_TEST_MODE_ADB")
            
            assert result["status"] == "success"
            assert "raw" in result

@pytest.mark.asyncio
async def test_samsung_plugin_port_not_found():
    plugin = SamsungPlugin()
    
    with patch.object(plugin.serial_adapter, 'find_samsung_modem_port', return_value=None):
        # We mock usb_injector to simulate a failure to find the port after MTP injection attempt
        with patch.object(plugin.usb_injector, 'force_modem_configuration', side_effect=RuntimeError("MTP fallida")):
            result = await plugin.execute_action("ENABLE_TEST_MODE_ADB")
            
            assert result["status"] == "error"
            assert "MTP fallida" in result["message"]
