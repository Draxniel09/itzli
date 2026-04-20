import serial
import serial.tools.list_ports
import time
from typing import Optional, List, Tuple
import logging

class SerialSession:
    """
    Maneja la conexión activa al puerto serie durante una sesión, 
    evitando abrir y cerrar el puerto por cada comando.
    """
    def __init__(self, port: str, timeout: float):
        self.port = port
        self.timeout = timeout
        self.ser = None

    def __enter__(self):
        try:
            self.ser = serial.Serial(self.port, baudrate=115200, timeout=self.timeout)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            return self
        except serial.SerialException as e:
            raise RuntimeError(f"Error abriendo el puerto {self.port}: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send_at_command(self, command: str, expected_responses: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Envía un comando AT al puerto abierto, esperando la respuesta línea a línea
        para evitar problemas de timming con sleep() estáticos.
        Limpia buffers residuales antes de emitir un nuevo comando.
        """
        if expected_responses is None:
            expected_responses = ['OK']
            
        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            
            # Limpiar cualquier basura residual (USB CDC in-flight packets)
            self.ser.timeout = 0.05
            while self.ser.read(1024):
                pass
            self.ser.timeout = self.timeout
            
            encoded_cmd = f"{command}\r\n".encode('ascii')
            self.ser.write(encoded_cmd)
            self.ser.flush()
            
            start_time = time.time()
            response_lines = []
            success = False
            
            while (time.time() - start_time) < self.timeout:
                line = self.ser.readline().decode('ascii', errors='ignore').strip()
                if line:
                    # Ignorar el echo exacto del comando o ecos parciales del módem Samsung
                    if command in line:
                        continue
                    
                    if any(expected in line for expected in expected_responses):
                        success = True
                        break
                    
                    if "ERROR" in line:
                        response_lines.append(line)
                        break
                        
                    response_lines.append(line)
            
            # Crucial: Pequeño delay de 150ms para que el módem procese el comando previo
            time.sleep(0.15)
            
            response_str = "\n".join(response_lines).strip()
            return success, response_str
        except serial.SerialException as e:
            raise RuntimeError(f"Error de comunicación en puerto {self.port}: {e}")

class SerialPortAdapter:
    """
    Adaptador para aislar la lógica de pyserial, cumpliendo con el
    principio de responsabilidad única.
    """
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        self.logger = logging.getLogger("SerialPortAdapter")
        
    def find_samsung_modem_port(self) -> Optional[str]:
        """Busca el puerto serie que corresponde a un módem Samsung."""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # 0x04e8 es el Vendor ID oficial de Samsung
            if port.vid == 0x04e8:
                return port.device
        return None

    def session(self, port: str) -> SerialSession:
        """Retorna un context manager para mantener el puerto abierto durante una sesión de comandos."""
        return SerialSession(port, self.timeout)
