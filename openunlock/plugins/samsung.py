import asyncio
from typing import List, Dict, Any, Tuple, Optional
from openunlock.core.interfaces import BaseDevicePlugin
from openunlock.adapters.serial_port import SerialPortAdapter
from openunlock.adapters.usb_injector import USBInjectorAdapter

class SamsungPlugin(BaseDevicePlugin):
    """
    Plugin para operaciones específicas de dispositivos Samsung.
    Maneja el Bypass de FRP invocando comandos AT vía el módem serie.
    """
    
    def __init__(self):
        self.serial_adapter = SerialPortAdapter()
        self.usb_injector = USBInjectorAdapter()
    
    @property
    def name(self) -> str:
        return "Samsung Factory Plugin"

    @property
    def supported_vid_pid(self) -> List[tuple[str, str]]:
        return [("04e8", "685d"), ("04e8", "6860")]

    def get_supported_actions(self) -> List[str]:
        return ["READ_INFO_AT", "ENABLE_TEST_MODE_ADB", "FRP_BYPASS"]

    async def execute_action(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Enruta la acción solicitada a la función correspondiente."""
        if action == "READ_INFO_AT":
            return await self._read_info_at()
        elif action == "ENABLE_TEST_MODE_ADB":
            return await self._enable_test_mode_adb()
        elif action == "FRP_BYPASS":
            return await self._frp_bypass()
        else:
            raise ValueError(f"Acción no soportada: {action}")

    async def _ensure_modem_port(self) -> str:
        """Intenta encontrar el puerto serie normal. Si falla, inyecta configuración USB."""
        port = self.serial_adapter.find_samsung_modem_port()
        if port:
            return port
            
        # Si no lo encuentra, forzamos el modo módem usando pyusb
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.usb_injector.force_modem_configuration)
        
        # Volvemos a buscar el puerto después de inyectar
        port = self.serial_adapter.find_samsung_modem_port()
        if not port:
            raise RuntimeError("Inyección MTP fallida. No se detectó /dev/ttyACM0. ¿Lanzaste install_rules.sh?")
        return port

    async def _enable_test_mode_adb(self) -> Dict[str, Any]:
        """Envía el comando AT para activar el modo de prueba (*#0*#)."""
        try:
            port = await self._ensure_modem_port()
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
        loop = asyncio.get_running_loop()
        try:
            command = "AT+KSTRINGB=0,3" 
            success, raw_response = await loop.run_in_executor(
                None, self.serial_adapter.send_at_command, port, command
            )
            
            if success:
                return {
                    "status": "success", 
                    "message": "Comando inyectado vía MTP. Revisa la pantalla del celular para aceptar permisos ADB.", 
                    "raw": raw_response
                }
            else:
                return {"status": "error", "message": "El celular no respondió con OK al comando AT.", "raw": raw_response}
        except Exception as e:
            return {"status": "error", "message": f"Falla de comunicación serial: {str(e)}"}

    async def _read_info_at(self) -> Dict[str, Any]:
        """Lee información básica del dispositivo usando comandos AT estándar."""
        try:
            port = await self._ensure_modem_port()
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
        loop = asyncio.get_running_loop()
        try:
            self.serial_adapter.logger.info("Esperando estabilización del puerto...")
            await asyncio.sleep(1.5)
            
            s1, raw_model = await loop.run_in_executor(None, self.serial_adapter.send_at_command, port, "AT+GMM")
            s2, raw_imei = await loop.run_in_executor(None, self.serial_adapter.send_at_command, port, "AT+GSN")
            
            model = raw_model.replace("OK", "").strip() if s1 else "Desconocido"
            imei = raw_imei.replace("OK", "").strip() if s2 else "Desconocido"
            
            if s1 or s2:
                return {"status": "success", "message": f"INFO LEÍDA | Modelo: {model} | IMEI: {imei}"}
            else:
                return {"status": "error", "message": "El dispositivo no respondió a los comandos de lectura AT."}
        except Exception as e:
            return {"status": "error", "message": f"Falla al leer info por puerto: {str(e)}"}

    async def _frp_bypass(self) -> Dict[str, Any]:
        return {"status": "error", "message": "FRP vía ADB requiere el CLIRunner. Todavía no implementado."}
