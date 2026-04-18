import serial
import serial.tools.list_ports
import time
from typing import Optional, List, Tuple
import logging

class SerialPortAdapter:
    """
    Adaptador para aislar la lógica de pyserial, cumpliendo con el
    principio de responsabilidad única.
    """
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        
    def find_samsung_modem_port(self) -> Optional[str]:
        """Busca el puerto serie que corresponde a un módem Samsung."""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # 0x04e8 es el Vendor ID oficial de Samsung
            if port.vid == 0x04e8:
                return port.device
        return None

    def send_at_command(self, port: str, command: str, expected_responses: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Envía un comando AT al puerto especificado y lee la respuesta.
        Retorna una tupla (exito: bool, respuesta_cruda: str)
        """
        if expected_responses is None:
            expected_responses = ['OK']
            
        try:
            with serial.Serial(port, baudrate=115200, timeout=self.timeout) as ser:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Enviamos el comando con retorno de carro (CRLF)
                encoded_cmd = f"{command}\r\n".encode('ascii')
                ser.write(encoded_cmd)
                
                # Los módems celulares pueden ser lentos en responder
                time.sleep(0.5)
                
                # Intentamos decodificar ignorando caracteres inválidos
                response = ser.read_all().decode('ascii', errors='ignore')
                
                for expected in expected_responses:
                    if expected in response:
                        return True, response
                return False, response
        except serial.SerialException as e:
            raise RuntimeError(f"Error de comunicación en puerto {port}. Posible puerto ocupado o desconectado: {e}")
