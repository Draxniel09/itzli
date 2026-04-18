from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPlainTextEdit, QLabel, QPushButton, 
    QTabWidget, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt
from openunlock.gui.bridge import DeviceEventBridge
from openunlock.core.interfaces import BaseDevicePlugin
import asyncio
import threading

class MainWindow(QMainWindow):
    def __init__(self, bridge: DeviceEventBridge):
        super().__init__()
        self.bridge = bridge
        self.setWindowTitle("OpenUnlock-Linux (Premium UI)")
        self.resize(1100, 750)
        self.active_plugin = None
        
        # Diseño Estético Premium (Estilo SamFw / Herramientas Profesionales)
        self.setStyleSheet("""
            QMainWindow { background-color: #f3f3f3; }
            QLabel { color: #333333; font-weight: bold; font-family: 'Segoe UI', sans-serif;}
            QGroupBox { font-weight: bold; border: 1px solid #cccccc; border-radius: 5px; margin-top: 10px; padding-top: 15px;}
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; color: #005A9E;}
            QListWidget { background-color: #ffffff; color: #333; border: 1px solid #ccc; border-radius: 5px; font-size: 14px;}
            QListWidget::item:selected { background-color: #cce8ff; color: #000;}
            QPlainTextEdit { background-color: #1e1e1e; color: #4af626; font-family: 'Consolas', 'Monospace'; border: none; border-radius: 5px; padding: 10px;}
            QPushButton { background-color: #0078D7; color: white; border: none; padding: 12px; border-radius: 4px; font-weight: bold; font-size: 13px;}
            QPushButton:hover { background-color: #005A9E; }
            QPushButton:disabled { background-color: #cccccc; color: #888888; }
            QTabWidget::pane { border: 1px solid #cccccc; background: #ffffff; border-radius: 4px;}
            QTabBar::tab { background: #e1e1e1; color: #333; padding: 10px 20px; font-weight: bold; border-top-left-radius: 4px; border-top-right-radius: 4px;}
            QTabBar::tab:selected { background: #ffffff; color: #0078D7; border-bottom: 2px solid #0078D7;}
        """)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # -- Panel Izquierdo (Dispositivos Info y Logs) --
        left_panel = QVBoxLayout()
        
        info_group = QGroupBox("Información del Dispositivo")
        info_layout = QVBoxLayout()
        self.device_list = QListWidget()
        self.device_list.setMaximumHeight(150)
        info_layout.addWidget(self.device_list)
        
        self.lbl_status = QLabel("Estado: Esperando conexión USB...")
        self.lbl_status.setStyleSheet("color: #d83b01; font-size: 14px;") # Naranja cuando espera
        info_layout.addWidget(self.lbl_status)
        
        info_group.setLayout(info_layout)
        left_panel.addWidget(info_group)
        
        # Consola de Logs
        log_group = QGroupBox("Registro de Operaciones (Consola)")
        log_layout = QVBoxLayout()
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        log_layout.addWidget(self.console)
        log_group.setLayout(log_layout)
        left_panel.addWidget(log_group)
        
        layout.addLayout(left_panel, 1) # Toma el 40% del ancho
        
        # -- Área Principal (Tabs y Botones Mágicos) --
        right_panel = QVBoxLayout()
        self.tabs = QTabWidget()
        
        # Tab Principal
        self.tab_actions = QWidget()
        self.tab_actions_layout = QVBoxLayout(self.tab_actions)
        
        self.lbl_actions = QLabel("Conecta un dispositivo para descubrir las acciones disponibles.")
        self.lbl_actions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_actions.setStyleSheet("font-size: 16px; color: #666; margin: 20px;")
        self.tab_actions_layout.addWidget(self.lbl_actions)
        
        # Grid para meter los botones dinámicamente
        self.dynamic_buttons_widget = QWidget()
        self.dynamic_buttons_layout = QGridLayout(self.dynamic_buttons_widget)
        self.tab_actions_layout.addWidget(self.dynamic_buttons_widget)
        self.tab_actions_layout.addStretch()
        
        self.tabs.addTab(self.tab_actions, "Acciones Soportadas")
        self.tabs.addTab(QWidget(), "MTP / ADB Tools") # Espacio para el futuro
        
        right_panel.addWidget(self.tabs)
        layout.addLayout(right_panel, 2) # Toma el 60% del ancho

    def _connect_signals(self):
        self.bridge.device_added.connect(self._on_device_added)
        self.bridge.device_removed.connect(self._on_device_removed)
        self.bridge.log_message.connect(self.log)

    def log(self, message: str):
        self.console.appendPlainText(f"> {message}")

    def _on_device_added(self, devpath: str, plugin: BaseDevicePlugin):
        self.active_plugin = plugin
        self.lbl_status.setText(f"Estado: CONECTADO - {plugin.name}")
        self.lbl_status.setStyleSheet("color: #107c10; font-size: 14px;") # Verde
        
        item_text = f"{plugin.name} [{devpath}]"
        self.device_list.addItem(item_text)
        self.log(f"[+] Hardware enlazado: {plugin.name}")
        
        self._build_dynamic_buttons(plugin)

    def _on_device_removed(self, devpath: str, plugin: BaseDevicePlugin):
        item_text = f"{plugin.name} [{devpath}]"
        items = self.device_list.findItems(item_text, Qt.MatchFlag.MatchExactly)
        for item in items:
            self.device_list.takeItem(self.device_list.row(item))
            
        if self.device_list.count() == 0:
            self.lbl_status.setText("Estado: Esperando conexión USB...")
            self.lbl_status.setStyleSheet("color: #d83b01; font-size: 14px;")
            self.active_plugin = None
            self._clear_dynamic_buttons()
            
        self.log(f"[-] Hardware desenlazado: {plugin.name}")

    def _clear_dynamic_buttons(self):
        self.lbl_actions.show()
        # Elimina los botones viejos del grid
        for i in reversed(range(self.dynamic_buttons_layout.count())): 
            widget = self.dynamic_buttons_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

    def _build_dynamic_buttons(self, plugin: BaseDevicePlugin):
        self._clear_dynamic_buttons()
        self.lbl_actions.hide()
        
        actions = plugin.get_supported_actions()
        row, col = 0, 0
        for action in actions:
            # Formateamos ej: ENABLE_TEST_MODE_ADB -> Enable Test Mode Adb
            human_name = action.replace("_", " ").title()
            btn = QPushButton(human_name)
            btn.setMinimumHeight(60) # Botones grandes y fáciles de clickear
            
            # Usamos un closure (lambda con argumento default) para atar la acción al botón
            btn.clicked.connect(lambda checked=False, a=action: self._execute_plugin_action(a))
            
            self.dynamic_buttons_layout.addWidget(btn, row, col)
            col += 1
            if col > 1: # Dos columnas de botones
                col = 0
                row += 1

    def _execute_plugin_action(self, action_name: str):
        if not self.active_plugin: return
        self.log(f"[*] Lanzando acción: {action_name}...")
        
        # Como los plugins usan `async` y PySide6 se bloquea, lo mandamos a un hilo común de Python
        def run_async():
            try:
                # Corremos el Event Loop aislado para esta acción
                result = asyncio.run(self.active_plugin.execute_action(action_name))
                if result.get("status") == "success":
                    self.bridge.log_message.emit(f"[ÉXITO] {result.get('message')}")
                else:
                    self.bridge.log_message.emit(f"[ERROR] {result.get('message')}")
            except Exception as e:
                self.bridge.log_message.emit(f"[FALLA CRÍTICA] {str(e)}")

        threading.Thread(target=run_async, daemon=True).start()
