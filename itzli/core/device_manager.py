import os
from typing import Callable, Dict, Optional, Any
from itzli.core.interfaces import BaseDevicePlugin
from itzli.core.plugin_loader import PluginManager

class DeviceManager:
    """
    Orquestador Central de Dispositivos:
    Actúa como el cerebro que conecta los eventos de hardware (conexión/desconexión USB)
    con los plugins disponibles en Itzli.
    """
    def __init__(self, usb_monitor: Any, plugin_loader: PluginManager, on_device_change: Optional[Callable[[str, str, BaseDevicePlugin], None]] = None):
        """
        Inicializa el orquestador.
        :param usb_monitor: Instancia de USBMonitor (observa los puertos USB).
        :param plugin_loader: Instancia de PluginManager ya inicializada y descubierta.
        :param on_device_change: Callback opcional -> on_device_change(action, devpath, plugin_instance)
        """
        self.usb_monitor = usb_monitor
        self.plugin_loader = plugin_loader
        self.on_device_change = on_device_change
        
        # Diccionario de { devpath: plugin_instance }
        self.active_devices: Dict[str, BaseDevicePlugin] = {}
        
        # Inyectar nuestro manejador al monitor
        self.usb_monitor.callback = self._on_usb_event

    def start(self) -> None:
        """Inicia la detección de dispositivos."""
        self.usb_monitor.start()

    def stop(self) -> None:
        """Detiene la detección."""
        self.usb_monitor.stop()

    def _on_usb_event(self, action: str, vid: str, pid: str, devpath: str) -> None:
        """Callback interno que se dispara con eventos udev."""
        if action == 'add':
            plugin = self.plugin_loader.get_plugin_for_device(vid, pid)
            if plugin:
                self.active_devices[devpath] = plugin
                if self.on_device_change:
                    self.on_device_change('add', devpath, plugin)
        elif action == 'remove':
            # 1. Coincidencia directa por devpath
            plugin = self.active_devices.pop(devpath, None)
            if plugin and self.on_device_change:
                self.on_device_change('remove', devpath, plugin)
            elif self.active_devices and self.on_device_change:
                # 2. Resiliencia: verificar si los dispositivos registrados ya no existen físicamente en /dev
                for p in list(self.active_devices.keys()):
                    if not os.path.exists(p):
                        plug = self.active_devices.pop(p)
                        self.on_device_change('remove', p, plug)
