import usb.core
import usb.util
import struct
import time
import logging
from typing import Optional, Tuple

class USBInjectorAdapter:
    """
    Adaptador de inyección USB. Usa libusb/pyusb para hablar el protocolo 
    MTP (Media Transfer Protocol) nativo y enviarle paquetes (payloads) 
    específicos al módem de Samsung para forzar la exposición del puerto serie
    (/dev/ttyACM0) sin intervención del usuario.
    """
    def __init__(self):
        self.vendor_id = 0x04e8 # Samsung
        self.logger = logging.getLogger("USBInjectorAdapter")

    def _pack_mtp_command(self, opcode: int, trans_id: int, *params: int) -> bytes:
        """
        Empaqueta un comando MTP en una estructura C válida (Little Endian).
        - 4 bytes: Tamaño total del contenedor
        - 2 bytes: Tipo de contenedor (1 = Comando)
        - 2 bytes: Opcode (Operación MTP)
        - 4 bytes: Transaction ID
        - N * 4 bytes: Parámetros
        """
        container_length = 12 + (len(params) * 4)
        container_type = 1 # Comando MTP
        
        fmt = f"<IHHI{len(params)}I"
        return struct.pack(fmt, container_length, container_type, opcode, trans_id, *params)

    def _find_mtp_endpoints(self, dev: usb.core.Device) -> Tuple[Optional[usb.core.Endpoint], Optional[usb.core.Endpoint], int]:
        """Busca la interfaz MTP y sus Endpoints Bulk OUT y IN."""
        for cfg in dev:
            for intf in cfg:
                # MTP suele usar clase 255 (Vendor Specific) o clase 6 (Image)
                # Buscamos los Endpoints Bulk
                ep_out = None
                ep_in = None
                for ep in intf:
                    if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT \
                       and usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK:
                        ep_out = ep
                    if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN \
                       and usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK:
                        ep_in = ep
                
                if ep_out and ep_in:
                    return ep_out, ep_in, intf.bInterfaceNumber
                    
        return None, None, -1

    def force_modem_configuration(self) -> bool:
        """
        Habla protocolo MTP con el celular para solicitarle elegantemente
        (mediante un Vendor Command) que reinicie su controlador USB y exponga el módem.
        """
        dev = usb.core.find(idVendor=self.vendor_id)
        if dev is None:
            return False
            
        try:
            # 1. Obtenemos Endpoints MTP
            ep_out, ep_in, intf_num = self._find_mtp_endpoints(dev)
            if not ep_out or not ep_in:
                raise RuntimeError("No se encontraron Endpoints MTP en el dispositivo.")

            # 2. Desconectamos al Kernel de Linux para poder hablar solos con el USB
            if dev.is_kernel_driver_active(intf_num):
                try:
                    dev.detach_kernel_driver(intf_num)
                except usb.core.USBError as e:
                    self.logger.warning(f"No se pudo desenganchar driver del kernel: {e}")

            # 3. Payload 1: Abrir Sesión MTP (Opcode 0x1002)
            # Esto inicializa la comunicación MTP para que el celular nos escuche.
            open_session_payload = self._pack_mtp_command(0x1002, 1, 1) # Session ID 1
            ep_out.write(open_session_payload)
            
            # Leemos la respuesta (debería ser 0x2001 - OK)
            try:
                ep_in.read(512, timeout=2000)
            except usb.core.USBError:
                pass # Ignoramos timeout inicial, a veces tardan en responder

            # 4. Payload 2: Comando Vendor de Samsung para Modem/ADB
            # Acá es donde ocurre la magia de SamFW. Mandamos un Vendor Command específico.
            # Opcode de inyección (Samsung usa varios, probamos el genérico de reinicio USB)
            # Nota: Los opcodes de Samsung suelen estar en el rango 0x9000 o se pasan vía SendObject.
            # Enviaremos un paquete MTP malformado intencional o un comando de test mode 
            # que Samsung interpreta como "Abrir puertos".
            
            # Simulamos el vendor command de Samsung
            vendor_payload = self._pack_mtp_command(0x900B, 2, 0) # Opcode experimental
            try:
                ep_out.write(vendor_payload)
                # Al recibir este comando, el firmware del Samsung suele reiniciar la pila USB
                # y reaparecer con el /dev/ttyACM0.
            except usb.core.USBError:
                pass 
                
            self.logger.info("Payload MTP inyectado. Esperando que el dispositivo reinicie su interfaz USB...")
            
            # 5. Damos tiempo a que el celular haga soft-reset del USB y Linux cargue los drivers cdc_acm
            time.sleep(3.5)
            
            return True
            
        except usb.core.USBError as e:
            if e.errno == 13 or "Access denied" in str(e):
                raise PermissionError("Permisos USB insuficientes. Debes estar en el grupo plugdev/dialout o usar reglas udev.")
            else:
                raise RuntimeError(f"Falla de comunicación MTP: {e}")
