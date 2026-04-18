import pytest
from unittest.mock import patch
from openunlock.plugins.samsung import SamsungPlugin

@pytest.mark.asyncio
async def test_samsung_plugin_enable_test_mode_success():
    plugin = SamsungPlugin()
    
    with patch.object(plugin.serial_adapter, 'find_samsung_modem_port', return_value="/dev/ttyACM0"):
        with patch.object(plugin.serial_adapter, 'send_at_command', return_value=(True, "OK")):
            result = await plugin.execute_action("ENABLE_TEST_MODE_ADB")
            
            assert result["status"] == "success"
            assert "raw" in result

@pytest.mark.asyncio
async def test_samsung_plugin_port_not_found():
    plugin = SamsungPlugin()
    
    with patch.object(plugin.serial_adapter, 'find_samsung_modem_port', return_value=None):
        result = await plugin.execute_action("ENABLE_TEST_MODE_ADB")
        
        assert result["status"] == "error"
        assert "No se encontró" in result["message"]
