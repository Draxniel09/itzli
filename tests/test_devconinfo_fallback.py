import pytest
from unittest.mock import patch, AsyncMock
from openunlock.plugins.samsung import SamsungPlugin

@pytest.mark.asyncio
async def test_fallback_devconinfo():
    plugin = SamsungPlugin()
    
    mock_results = {
        "model": (False, "No disponible"),
        "imei": (True, "OK\r\nNONE"),
        "sw_ver": (True, "+SWVER: A525FXXU4CVJB/A525FOXM4CVJB/A525FXXU4CVJB/A525FXXU4CVJB"),
        "cimi": (True, "+CME Error:PACM(AP),NOT_ALLOWED_CRO"),
        "dev_info": (True, "+DEVCONINFO: MN(SM-A525F);BASE(UNKNOWN);VER(A525FXXU4CVJB);MNC(140,140);MCC(334,334);SN(R58RC3AL3CR);IMEI(354704171609828);UN(2C102123);PN(,+52);CON(AT,MTP);LOCK(NONE)")
    }
    
    with patch.object(plugin, '_ensure_modem_port', return_value="/dev/ttyFAKE"):
        with patch.object(plugin, '_sync_read_info', return_value=mock_results):
            # No esperamos por sleep
            with patch('asyncio.sleep', new_callable=AsyncMock):
                res = await plugin.execute_action("READ_INFO_AT")
                
                assert res["status"] == "success"
                # Verificamos que el fallback extrajo Modelo e IMEI correctamente de DEVCONINFO
                assert "📱 Modelo: SM-A525F" in res["message"]
                assert "🔑 IMEI: 354704171609828" in res["message"]
                # Verificamos limpieza
                assert "💿 Software Ver: A525FXXU4CVJB" in res["message"]
                assert "Bloqueado por Knox/PACM" in res["message"]
                assert "Red: MCC 334 / MNC 140" in res["message"]

