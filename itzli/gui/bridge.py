from PySide6.QtCore import QObject, Signal

class DeviceEventBridge(QObject):
    """
    Puente de señales (Signals & Slots) para comunicar el hilo en 
    segundo plano de pyudev con el hilo principal de la GUI (PySide6).
    Evita crasheos por actualización de interfaz desde otro thread.
    """
    # Emite: devpath, plugin_instance
    device_added = Signal(str, object)
    
    # Emite: devpath, plugin_instance
    device_removed = Signal(str, object)
    
    # Emite: mensaje de texto
    log_message = Signal(str)
    
    # Emite: cuando una operación asíncrona de plugin termina o se aborta
    operation_finished = Signal()

    # Emite: action_name, title, file_filter
    file_requested = Signal(str, str, str)

    # Emite: action_name, title
    dir_requested = Signal(str, str)

    # Emite: progreso actual (0-100)
    progress_update = Signal(int)
