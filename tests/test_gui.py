import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from openunlock.gui.bridge import DeviceEventBridge
from openunlock.gui.main_window import MainWindow

def test_bridge_signals(qtbot):
    bridge = DeviceEventBridge()
    with qtbot.waitSignal(bridge.device_added, timeout=1000) as blocker:
        bridge.device_added.emit("/dev/ttyACM0", None)
    assert blocker.args == ["/dev/ttyACM0", None]

def test_main_window_device_add_remove(qtbot):
    bridge = DeviceEventBridge()
    window = MainWindow(bridge)
    qtbot.addWidget(window)
    
    fake_plugin = MagicMock()
    fake_plugin.name = "Samsung Fake"
    
    # Simular Agregar
    bridge.device_added.emit("/dev/USB0", fake_plugin)
    assert window.device_list.count() == 1
    assert "Samsung Fake" in window.device_list.item(0).text()
    
    # Simular Remover
    bridge.device_removed.emit("/dev/USB0", fake_plugin)
    assert window.device_list.count() == 0
