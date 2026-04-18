import usb.core
import usb.util
import time
from typing import Optional

class USBInjectorAdapter:
    """
    Adaptador de muy bajo nivel usando libusb/pyusb para interactuar directamente 
    con los Endpoints de los dispositivos, saltándose las limitaciones de los drivers del SO.
    """
    def __init__(self):
        self.vendor_id = 0x04e8 # Samsung

    def force_modem_configuration(self) -> bool:
        """
        Busca un dispositivo Samsung conectado y fuerza un cambio en su 
        Configuración USB activa. Por defecto están en Config 1 (MTP). 
        Al cambiarlo a Config 2, el celular expone el módem (/dev/ttyACM0) 
        sin que el usuario tenga que marcar *#0808#.
        """
        dev = usb.core.find(idVendor=self.vendor_id)
        if dev is None:
            return False
            
        try:
            # Obtenemos la configuración activa actual
            current_cfg = dev.get_active_configuration()
            
            # Si ya está en la configuración 2 o superior, probablemente ya tiene el módem expuesto
            if current_cfg.bConfigurationValue >= 2:
                return True
                
            # Desconectamos el driver de Linux MTP que puede estar usando el dispositivo
            for intf in current_cfg:
                if dev.is_kernel_driver_active(intf.bInterfaceNumber):
                    try:
                        dev.detach_kernel_driver(intf.bInterfaceNumber)
                    except usb.core.USBError:
                        pass
            
            # MAGIA: Forzamos el cambio de configuración a la 2 (Suele ser CDC ACM / ADB)
            dev.set_configuration(2)
            
            # Damos tiempo a que el kernel de Linux lea el cambio y cree /dev/ttyACM0
            time.sleep(2)
            return True
            
        except usb.core.USBError as e:
            if e.errno == 13 or "Access denied" in str(e):
                raise PermissionError("Permisos USB insuficientes. Debes correr './install_rules.sh' y reiniciar, o ejecutar como root.")
            elif "Entity not found" in str(e):
                # A veces al cambiar de configuración, el dispositivo se "desconecta" lógicamente y se reconecta
                time.sleep(2)
                return True
            else:
                raise RuntimeError(f"Falla de inyección USB: {e}")
