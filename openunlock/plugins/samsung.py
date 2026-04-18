import asyncio
from typing import List, Dict, Any, Tuple
from openunlock.core.interfaces import BaseDevicePlugin
from openunlock.adapters.serial_port import SerialPortAdapter

class SamsungPlugin(BaseDevicePlugin):
    """
    Plugin para operaciones específicas de dispositivos Samsung.
    Maneja el Bypass de FRP invocando comandos AT vía el módem serie.
    """
    
    def __init__(self):
        # Inyectamos el adaptador de puerto serie
        self.serial_adapter = SerialPortAdapter()
    
    @property
    def name(self) -> str:
        return "Samsung Factory Plugin"

    @property
    def supported_vid_pid(self) -> List[tuple[str, str]]:
        # VID de Samsung es 04E8, PID varía según el modo (MTP, ADB, Download)
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

    async def _enable_test_mode_adb(self) -> Dict[str, Any]:
        """
        Intenta enviar el comando AT para activar el modo de prueba (*#0*#) 
        que habilita el daemon ADB en el teléfono.
        """
        port = self.serial_adapter.find_samsung_modem_port()
        if not port:
            return {
                "status": "error", 
                "message": "No se encontró un puerto serie de Samsung conectado (ej. /dev/ttyACM0)."
            }
        
        loop = asyncio.get_running_loop()
        try:
            # Comando mágico AT para simular el tipeo en el dialer: *#0*#
            # AT+KSTRINGB invoca teclas (depende del firmware baseband, este es un ej. estándar)
            # En muchos Samsung se usa AT+SWTBIT=... o AT+SYSSCOPE
            command = "AT+KSTRINGB=0,3" 
            
            # pyserial es bloqueante (I/O). Lo mandamos al ThreadPoolExecutor
            # para no congelar el Event Loop ni la GUI.
            success, raw_response = await loop.run_in_executor(
                None, 
                self.serial_adapter.send_at_command, 
                port, 
                command
            )
            
            if success:
                return {
                    "status": "success", 
                    "message": "Comando enviado. Revisa la pantalla del celular para aceptar permisos ADB.", 
                    "raw": raw_response
                }
            else:
                return {
                    "status": "error", 
                    "message": "El celular no respondió con OK. Posible parche de seguridad reciente.", 
                    "raw": raw_response
                }
                
        except Exception as e:
            # Capturamos SerialException traducido en RuntimeError por el adaptador
            return {"status": "error", "message": f"Falla crítica: {str(e)}"}

    async def _read_info_at(self) -> Dict[str, Any]:
        """Lee información básica del dispositivo usando comandos AT estándar."""
        port = self.serial_adapter.find_samsung_modem_port()
        if not port:
            return {"status": "error", "message": "No se encontró el puerto serie de Samsung (/dev/ttyACM*)."}
            
        loop = asyncio.get_running_loop()
        try:
            # Pausa breve artificial para que el usuario pueda probar el botón "Abortar" en la GUI
            self.serial_adapter.logger.info("Esperando estabilización del puerto...")
            await asyncio.sleep(1.5)
            
            # AT+GMM pide el modelo del equipo
            s1, raw_model = await loop.run_in_executor(None, self.serial_adapter.send_at_command, port, "AT+GMM")
            # AT+GSN pide el IMEI del equipo
            s2, raw_imei = await loop.run_in_executor(None, self.serial_adapter.send_at_command, port, "AT+GSN")
            
            # Limpiamos las respuestas (quitando los 'OK' y saltos de línea)
            model = raw_model.replace("OK", "").strip() if s1 else "Desconocido"
            imei = raw_imei.replace("OK", "").strip() if s2 else "Desconocido"
            
            if s1 or s2:
                return {"status": "success", "message": f"INFO LEÍDA | Modelo: {model} | IMEI: {imei}"}
            else:
                return {"status": "error", "message": "El dispositivo no respondió a los comandos de lectura."}
        except Exception as e:
            return {"status": "error", "message": f"Falla crítica al leer info: {str(e)}"}

    async def _frp_bypass(self) -> Dict[str, Any]:
        return {"status": "error", "message": "FRP vía ADB requiere el CLIRunner. Todavía no implementado."}
