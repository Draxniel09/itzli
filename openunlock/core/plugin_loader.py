import importlib
import pkgutil
import inspect
from typing import List, Optional
from openunlock.core.interfaces import BaseDevicePlugin

class PluginManager:
    def __init__(self, plugin_package: str = "openunlock.plugins"):
        self.plugin_package = plugin_package
        self._plugins: List[BaseDevicePlugin] = []

    def discover_plugins(self) -> None:
        """Descubre y carga automáticamente las clases que heredan de BaseDevicePlugin."""
        self._plugins = []
        
        try:
            package = importlib.import_module(self.plugin_package)
        except ImportError:
            return

        # Si el paquete no tiene __path__, es solo un archivo (módulo simple)
        if not hasattr(package, '__path__'):
            self._load_from_module(package)
            return

        # Iterar sobre todos los sub-módulos del paquete
        for _, name, _ in pkgutil.iter_modules(package.__path__):
            full_module_name = f"{self.plugin_package}.{name}"
            try:
                module = importlib.import_module(full_module_name)
                self._load_from_module(module)
            except ImportError:
                continue

    def _load_from_module(self, module) -> None:
        """Busca clases dentro de un módulo que implementen BaseDevicePlugin."""
        for _, item in inspect.getmembers(module):
            if inspect.isclass(item) and issubclass(item, BaseDevicePlugin) and item is not BaseDevicePlugin:
                try:
                    plugin_instance = item()
                    self._plugins.append(plugin_instance)
                except Exception:
                    # Ignore instantiation errors for now (e.g. abstract methods not implemented)
                    continue

    def get_all_plugins(self) -> List[BaseDevicePlugin]:
        """Retorna todos los plugins cargados."""
        return self._plugins

    def get_plugin_for_device(self, vid: str, pid: str) -> Optional[BaseDevicePlugin]:
        """Busca el primer plugin que soporte el VID:PID dado (case-insensitive)."""
        target_vid = vid.lower()
        target_pid = pid.lower()
        
        for plugin in self._plugins:
            supported = [(v.lower(), p.lower()) for v, p in plugin.supported_vid_pid]
            if (target_vid, target_pid) in supported:
                return plugin
        return None
