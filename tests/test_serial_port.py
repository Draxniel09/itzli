import pytest
from unittest.mock import patch, MagicMock
from openunlock.adapters.serial_port import SerialPortAdapter

def test_find_samsung_modem():
    adapter = SerialPortAdapter()
    
    mock_port = MagicMock()
    mock_port.vid = 0x04e8
    mock_port.device = "/dev/ttyACM0"
    
    with patch('serial.tools.list_ports.comports', return_value=[mock_port]):
        port = adapter.find_samsung_modem_port()
        assert port == "/dev/ttyACM0"

def test_send_at_command_success():
    adapter = SerialPortAdapter()
    
    mock_serial_instance = MagicMock()
    mock_serial_instance.read_all.return_value = b"\r\nOK\r\n"
    
    with patch('serial.Serial') as mock_serial:
        mock_serial.return_value.__enter__.return_value = mock_serial_instance
        success, response = adapter.send_at_command("/dev/ttyACM0", "AT")
        
        assert success is True
        assert "OK" in response
        mock_serial_instance.write.assert_called_with(b"AT\r\n")

def test_send_at_command_failure():
    adapter = SerialPortAdapter()
    
    mock_serial_instance = MagicMock()
    mock_serial_instance.read_all.return_value = b"\r\nERROR\r\n"
    
    with patch('serial.Serial') as mock_serial:
        mock_serial.return_value.__enter__.return_value = mock_serial_instance
        success, response = adapter.send_at_command("/dev/ttyACM0", "AT")
        
        assert success is False
        assert "ERROR" in response
