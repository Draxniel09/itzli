import pytest
from unittest.mock import MagicMock
from openunlock.adapters.udev_monitor import USBMonitor

def test_usb_monitor_detects_add_event():
    # Setup mock device
    mock_device = MagicMock()
    mock_device.action = 'add'
    mock_device.get.side_effect = lambda key: {
        'ID_VENDOR_ID': '04e8',
        'ID_MODEL_ID': '685d',
        'DEVNAME': '/dev/bus/usb/001/002'
    }.get(key)
    
    callbacks_received = []
    def on_event(action, vid, pid, devpath):
        callbacks_received.append((action, vid, pid, devpath))
        
    monitor = USBMonitor(callback=on_event)
    
    # Simulate processing one event directly
    monitor._process_event(mock_device)
    
    assert len(callbacks_received) == 1
    assert callbacks_received[0] == ('add', '04e8', '685d', '/dev/bus/usb/001/002')

def test_usb_monitor_detects_remove_event():
    mock_device = MagicMock()
    mock_device.action = 'remove'
    mock_device.get.side_effect = lambda key: {
        'ID_VENDOR_ID': '0FCE',
        'ID_MODEL_ID': 'D071',
        'DEVNAME': '/dev/bus/usb/002/003'
    }.get(key)
    
    callbacks_received = []
    monitor = USBMonitor(callback=lambda a,v,p,d: callbacks_received.append((a, v, p)))
    
    monitor._process_event(mock_device)
    
    assert len(callbacks_received) == 1
    assert callbacks_received[0] == ('remove', '0fce', 'd071')

def test_usb_monitor_ignores_non_usb_events():
    mock_device = MagicMock()
    mock_device.action = 'add'
    # Return None for VID/PID, simulating a generic USB hub event or incomplete data
    mock_device.get.return_value = None
    
    callbacks_received = []
    monitor = USBMonitor(callback=lambda a,v,p,d: callbacks_received.append(a))
    
    monitor._process_event(mock_device)
    
    # Should be ignored because VID and PID are missing
    assert len(callbacks_received) == 0
