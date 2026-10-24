import pytest
from unittest.mock import patch
from itzli.plugins.universal import UniversalPlugin

@pytest.mark.asyncio
async def test_deberia_ejecutar_adb_devices_correctamente_happy_path():
    plugin = UniversalPlugin()
    
    # Aislar: Simulamos que ADB está instalado
    with patch.object(plugin.cli_runner, 'check_dependencies', return_value={"adb": True}):
        # Simulamos que el CLI runner devuelve un stream asíncrono
        async def mock_generator():
            yield "List of devices attached"
            yield "123456789abc\tdevice"
            
        with patch.object(plugin.cli_runner, 'run_command', return_value=mock_generator()) as mock_run:
            resultado = await plugin.execute_action("ADB_DEVICES")
            
            assert resultado["status"] == "stream"
            assert "Listando" in resultado["message"]
            mock_run.assert_called_once_with(["adb", "devices"])

@pytest.mark.asyncio
async def test_deberia_retornar_error_si_adb_no_esta_instalado():
    plugin = UniversalPlugin()
    
    # Manejo de Errores: Simulamos que ADB no existe en el sistema
    with patch.object(plugin.cli_runner, 'check_dependencies', return_value={"adb": False}):
        resultado = await plugin.execute_action("ADB_DEVICES")
        
        assert resultado["status"] == "error"
        assert "no está instalado" in resultado["message"]