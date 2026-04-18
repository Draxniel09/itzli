from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPlainTextEdit, QLabel
)
from PySide6.QtCore import Qt
from openunlock.gui.bridge import DeviceEventBridge
from openunlock.core.interfaces import BaseDevicePlugin

class MainWindow(QMainWindow):
    def __init__(self, bridge: DeviceEventBridge):
        super().__init__()
        self.bridge = bridge
        self.setWindowTitle("OpenUnlock-Linux")
        self.resize(1000, 700)
        
        # Diseño Estético Premium (Dark Mode nativo modificado)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: #ffffff; font-weight: bold; font-family: 'Inter', 'Segoe UI', sans-serif;}
            QListWidget { background-color: #252526; color: #d4d4d4; border: 1px solid #333; border-radius: 5px; padding: 5px; font-size: 14px;}
            QListWidget::item:selected { background-color: #094771; }
            QPlainTextEdit { background-color: #0d0d0d; color: #4af626; font-family: 'Fira Code', 'Monospace'; border: 1px solid #333; border-radius: 5px; padding: 10px;}
            QPushButton { background-color: #0e639c; color: white; border: none; padding: 10px; border-radius: 4px; font-weight: bold; font-size: 14px;}
            QPushButton:hover { background-color: #1177bb; }
            QPushButton:disabled { background-color: #4d4d4d; color: #888888; }
        """)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # -- Panel lateral --
        sidebar = QVBoxLayout()
        lbl_sidebar = QLabel("Dispositivos Conectados")
        lbl_sidebar.setStyleSheet("font-size: 16px; margin-bottom: 5px;")
        sidebar.addWidget(lbl_sidebar)
        
        self.device_list = QListWidget()
        sidebar.addWidget(self.device_list)
        layout.addLayout(sidebar, 1)
        
        # -- Área Principal --
        main_area = QVBoxLayout()
        main_area.setSpacing(10)
        
        self.title_label = QLabel("Esperando dispositivo...")
        self.title_label.setStyleSheet("font-size: 22px; color: #569cd6; margin-bottom: 15px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_area.addWidget(self.title_label)
        
        # Layout para inyectar botones dinámicos según el plugin
        self.actions_layout = QHBoxLayout()
        main_area.addLayout(self.actions_layout)
        
        main_area.addStretch()
        
        lbl_console = QLabel("Consola de Sistema")
        lbl_console.setStyleSheet("font-size: 14px;")
        main_area.addWidget(lbl_console)
        
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        main_area.addWidget(self.console, 2)
        
        layout.addLayout(main_area, 3)

    def _connect_signals(self):
        # Conectamos las señales del puente a nuestras funciones de UI
        self.bridge.device_added.connect(self._on_device_added)
        self.bridge.device_removed.connect(self._on_device_removed)
        self.bridge.log_message.connect(self.log)

    def log(self, message: str):
        self.console.appendPlainText(f"> {message}")

    def _on_device_added(self, devpath: str, plugin: BaseDevicePlugin):
        item_text = f"{plugin.name} [{devpath}]"
        self.device_list.addItem(item_text)
        self.log(f"[+] Hardware detectado e interceptado: {plugin.name}")

    def _on_device_removed(self, devpath: str, plugin: BaseDevicePlugin):
        item_text = f"{plugin.name} [{devpath}]"
        items = self.device_list.findItems(item_text, Qt.MatchFlag.MatchExactly)
        for item in items:
            self.device_list.takeItem(self.device_list.row(item))
        self.log(f"[-] Hardware desconectado: {plugin.name}")
