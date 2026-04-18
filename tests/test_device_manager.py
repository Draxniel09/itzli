import pytest
from unittest.mock import MagicMock
from openunlock.core.device_manager import DeviceManager

def test_device_manager_add_supported_device():
    mock_monitor = MagicMock()
    mock_plugin_loader = MagicMock()
    
    fake_plugin = MagicMock()
    fake_plugin.name = "Test Plugin"
    mock_plugin_loader.get_plugin_for_device.return_value = fake_plugin
    
    callbacks_received = []
    def on_device_change(action, devpath, plugin):
        callbacks_received.append((action, devpath, plugin))
        
    manager = DeviceManager(
        usb_monitor=mock_monitor, 
        plugin_loader=mock_plugin_loader,
        on_device_change=on_device_change
    )
    
    # Simulamos evento de add
    manager._on_usb_event('add', '04e8', '685d', '/dev/bus/usb/001/001')
    
    mock_plugin_loader.get_plugin_for_device.assert_called_with('04e8', '685d')
    assert len(manager.active_devices) == 1
    assert '/dev/bus/usb/001/001' in manager.active_devices
    assert len(callbacks_received) == 1
    assert callbacks_received[0] == ('add', '/dev/bus/usb/001/001', fake_plugin)

def test_device_manager_add_unsupported_device():
    mock_monitor = MagicMock()
    mock_plugin_loader = MagicMock()
    mock_plugin_loader.get_plugin_for_device.return_value = None
    
    callbacks_received = []
    manager = DeviceManager(
        usb_monitor=mock_monitor, 
        plugin_loader=mock_plugin_loader,
        on_device_change=lambda a, d, p: callbacks_received.append(a)
    )
    
    manager._on_usb_event('add', '1234', '5678', '/dev/bus/usb/001/002')
    
    assert len(manager.active_devices) == 0
    assert len(callbacks_received) == 0

def test_device_manager_remove_device():
    mock_monitor = MagicMock()
    mock_plugin_loader = MagicMock()
    fake_plugin = MagicMock()
    
    manager = DeviceManager(
        usb_monitor=mock_monitor, 
        plugin_loader=mock_plugin_loader,
        on_device_change=MagicMock()
    )
    
    # Pre-poblamos un dispositivo activo
    manager.active_devices['/dev/bus/usb/001/001'] = fake_plugin
    
    manager._on_usb_event('remove', '04e8', '685d', '/dev/bus/usb/001/001')
    
    assert len(manager.active_devices) == 0
    manager.on_device_change.assert_called_with('remove', '/dev/bus/usb/001/001', fake_plugin)
