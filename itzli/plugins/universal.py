import asyncio
from typing import List, Dict, Any, Optional
from itzli.core.interfaces import BaseDevicePlugin
from itzli.adapters.cli_runner import CLIRunner

class UniversalPlugin(BaseDevicePlugin):
    """
    Módulo Universal para operaciones genéricas de Android.
    Interactúa con ADB y MTKClient utilizando llamadas a sistema.
    """
    
    def __init__(self, cli_runner=None):
        self.cli_runner = cli_runner or CLIRunner()
        
    @property
    def name(self) -> str:
        return "Universal Android Plugin"
        
    @property
    def supported_vid_pid(self) -> List[tuple[str, str]]:
        # Universal puede aplicar a cualquier dispositivo conectado por ADB
        return [] 
        
    def get_supported_actions(self) -> List[str]:
        return ["ADB_DEVICES", "ADB_GET_MODEL"]
        
    async def execute_action(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Enruta la acción solicitada a la función correspondiente."""
        if action == "ADB_DEVICES":
            return await self._adb_devices()
        elif action == "ADB_GET_MODEL":
            return await self._adb_get_model()
        else:
            raise ValueError(f"Acción no soportada: {action}")

    async def _check_adb(self) -> Optional[Dict[str, Any]]:
        deps = self.cli_runner.check_dependencies()
        if not deps["adb"]:
            return {
                "status": "error", 
                "message": "ADB no está instalado. En Fedora instálalo con: sudo dnf install android-tools"
            }
        return None

    async def _adb_devices(self) -> Dict[str, Any]:
        """Ejecuta adb devices en tiempo real."""
        error = await self._check_adb()
        if error: return error
            
        cmd = ["adb", "devices"]
        return {
            "status": "stream",
            "message": "Listando dispositivos ADB...",
            "generator": self.cli_runner.run_command(cmd)
        }

    async def _adb_get_model(self) -> Dict[str, Any]:
        """Ejecuta adb shell getprop ro.product.model en tiempo real."""
        error = await self._check_adb()
        if error: return error
            
        # Evitamos shell=True. Pasamos los argumentos exactamente como lista.
        cmd = ["adb", "shell", "getprop", "ro.product.model"]
        return {
            "status": "stream",
            "message": "Obteniendo modelo por ADB...",
            "generator": self.cli_runner.run_command(cmd)
        }