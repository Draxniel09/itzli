from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseDevicePlugin(ABC):
    """Contrato estricto para cualquier módulo de la comunidad."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Ej: 'Samsung Odin/Heimdall Flasher'"""
        pass

    @property
    @abstractmethod
    def supported_vid_pid(self) -> List[tuple[str, str]]:
        """Ej: [('04e8', '685d')] para identificar el celular al vuelo."""
        pass

    @abstractmethod
    def get_supported_actions(self) -> List[str]:
        """Ej: ['FRP_BYPASS', 'READ_INFO', 'FLASH_FIRMWARE']"""
        pass

    @abstractmethod
    async def execute_action(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """El core llama a esto. El plugin interactúa con adapters/cli_runner.py acá."""
        pass
