import sys
import logging
from PySide6.QtWidgets import QApplication
from openunlock.core.plugin_loader import PluginManager
from openunlock.core.device_manager import DeviceManager
from openunlock.adapters.udev_monitor import USBMonitor
from openunlock.gui.bridge import DeviceEventBridge
from openunlock.gui.main_window import MainWindow

def main():
    # Inicialización estándar de PySide6
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Base sólida para nuestro dark mode
    
    # 1. Crear el puente para comunicar threads de forma segura
    bridge = DeviceEventBridge()
    
    # 2. Callback que será disparado por el monitor USB (en un thread secundario)
    def on_device_change(action, devpath, plugin):
        if action == 'add':
            bridge.device_added.emit(devpath, plugin)
        elif action == 'remove':
            bridge.device_removed.emit(devpath, plugin)
            
    # 3. Inicializar Infraestructura (Core y Adapters)
    usb_monitor = USBMonitor(callback=lambda a,v,p,d: None)
    plugin_loader = PluginManager(plugin_package="openunlock.plugins")
    plugin_loader.discover_plugins()
    
    device_manager = DeviceManager(
        usb_monitor=usb_monitor,
        plugin_loader=plugin_loader,
        on_device_change=on_device_change
    )
    
    # 4. Inicializar y mostrar Ventana Principal
    window = MainWindow(bridge)
    window.show()
    
    bridge.log_message.emit("=== OpenUnlock-Linux Iniciado ===")
    bridge.log_message.emit(f"Plugins activos: {len(plugin_loader.get_all_plugins())}")
    bridge.log_message.emit("A la espera de dispositivos USB...")
    
    # 5. Iniciar monitor USB (Background)
    device_manager.start()
    
    # 6. Event Loop (Bloqueante) y limpieza ("Sin cabos sueltos")
    exit_code = app.exec()
    device_manager.stop() # Mata el hilo de pyudev limpiamente
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
