import pytest
from unittest.mock import patch
from openunlock.plugins.samsung import SamsungPlugin

@pytest.mark.asyncio
async def test_deberia_leer_info_con_puerto_serie_alternativo_edge_case():
    plugin = SamsungPlugin()
    
    # Edge Case: ¿Qué pasa si el puerto no es ttyACM0 sino ttyUSB0?
    puerto_raro = "/dev/ttyUSB0"
    
    with patch.object(plugin.serial_adapter, 'find_samsung_modem_port', return_value=puerto_raro):
        # Simulamos la lectura síncrona dentro del hilo
        mock_results = {
            "model": (True, "OK SM-G998B"),
            "imei": (True, "OK 351234567890123"),
            "sw_ver": (True, "OK G998BXXU4CVA9"),
            "cimi": (True, "OK 123456789012345"),
            "dev_info": (True, "OK PDA: ...")
        }
        with patch.object(plugin, '_sync_read_info', return_value=mock_results):
            resultado = await plugin.execute_action("READ_INFO_AT")
        
        assert resultado["status"] == "success"
        assert "SM-G998B" in resultado["message"]
        assert "351234567890123" in resultado["message"]

@pytest.mark.asyncio
async def test_deberia_retornar_error_si_heimdall_no_esta_instalado():
    plugin = SamsungPlugin()
    
    # Manejo de errores: Heimdall missing
    with patch.object(plugin.cli_runner, 'check_dependencies', return_value={"heimdall": False}):
        resultado = await plugin.execute_action("HEIMDALL_DETECT")
        
        assert resultado["status"] == "error"
        assert "Heimdall no instalado" in resultado["message"]