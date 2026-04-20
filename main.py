import sys
import faulthandler
import queue
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from openunlock.core.plugin_loader import PluginManager
from openunlock.core.device_manager import DeviceManager
from openunlock.adapters.udev_monitor import USBMonitor
from openunlock.gui.bridge import DeviceEventBridge
from openunlock.gui.main_window import MainWindow

# Habilitar diagnóstico de segfaults en stderr (si vuelve a pasar, veremos dónde)
faulthandler.enable()

def main():
    # Inicialización estándar de PySide6
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Base sólida para nuestro dark mode
    
    # 1. Crear el puente para comunicar threads de forma segura
    bridge = DeviceEventBridge()
    
    # 2. Cola thread-safe para desacoplar el hilo de pyudev del hilo de Qt.
    #    ¿Por qué? Porque pyudev dispara callbacks desde un hilo nativo de Linux.
    #    Si hacemos .emit() de una Signal de Qt desde ese hilo, PySide6 puede
    #    hacer SEGFAULT al cruzar la barrera de hilos con objetos Python.
    #    La solución es: pyudev solo escribe en la cola (operación thread-safe pura),
    #    y un QTimer en el hilo principal de Qt lee y emite las señales de forma segura.
    event_queue = queue.Queue()
    
    def on_device_change(action, devpath, plugin):
        """Callback ejecutado en el hilo de pyudev. Solo toca la cola."""
        event_queue.put((action, devpath, plugin))
    
    def process_usb_events():
        """Procesador ejecutado en el hilo principal de Qt vía QTimer."""
        while not event_queue.empty():
            action, devpath, plugin = event_queue.get_nowait()
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
    
    # 5. QTimer que procesa la cola de eventos USB cada 150ms desde el hilo de Qt
    usb_timer = QTimer()
    usb_timer.timeout.connect(process_usb_events)
    usb_timer.start(150)
    
    # 6. Iniciar monitor USB (Background)
    device_manager.start()
    
    # 7. Event Loop (Bloqueante) y limpieza ("Sin cabos sueltos")
    exit_code = app.exec()
    usb_timer.stop()
    device_manager.stop() # Mata el hilo de pyudev limpiamente
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
