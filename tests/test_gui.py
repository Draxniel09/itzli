import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from itzli.gui.bridge import DeviceEventBridge
from itzli.gui.main_window import MainWindow

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

def test_main_window_typewriter_and_fade_clear(qtbot):
    bridge = DeviceEventBridge()
    window = MainWindow(bridge)
    qtbot.addWidget(window)
    
    # 1. Typewriter logging
    window.log("Probando efecto typewriter")
    assert len(window._typewriter_queue) > 0
    assert window._typewriter_timer.isActive()
    
    # Procesar hasta vaciar la cola
    while len(window._typewriter_queue) > 0:
        window._process_typewriter()
        
    assert "Probando efecto typewriter" in window.console.toPlainText()
    assert not window._typewriter_timer.isActive()
    
    # 2. Fade clear console
    window._fade_clear_console()
    assert len(window._typewriter_queue) == 0
    assert window._console_anim is not None

def test_main_window_breathing_animation(qtbot):
    bridge = DeviceEventBridge()
    window = MainWindow(bridge)
    qtbot.addWidget(window)
    
    assert hasattr(window, "_breathing_group")
    assert window._breathing_group.loopCount() == -1
    
    fake_plugin = MagicMock()
    fake_plugin.name = "Samsung Test"
    fake_plugin.get_supported_actions.return_value = ["READ_INFO_AT"]
    
    # Cuando se conecta un dispositivo, se pausa la respiración
    window._build_dynamic_buttons(fake_plugin)
    assert window._breathing_group.state() != window._breathing_group.State.Running
    assert window.lbl_actions.isHidden()
    
    # Cuando se desconecta el dispositivo, se reanuda
    window._clear_dynamic_buttons()
    assert not window.lbl_actions.isHidden()
    assert window._breathing_group.state() == window._breathing_group.State.Running

