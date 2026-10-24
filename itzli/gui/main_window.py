from collections import deque
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPlainTextEdit, QLabel, QPushButton, 
    QTabWidget, QGroupBox, QGridLayout, QMessageBox, QFileDialog,
    QProgressBar, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QAbstractAnimation
from PySide6.QtGui import QTextCursor
from itzli.gui.bridge import DeviceEventBridge
from itzli.core.interfaces import BaseDevicePlugin
import asyncio
import threading

class MainWindow(QMainWindow):
    def __init__(self, bridge: DeviceEventBridge):
        super().__init__()
        self.bridge = bridge
        self.setWindowTitle("Itzli (Dark Blue Edition)")
        self.resize(1100, 750)
        self.active_plugin = None
        self.running_tasks = 0
        
        # Cola adaptativa y timer para efecto máquina de escribir en terminal
        self._typewriter_queue = deque()
        self._typewriter_timer = QTimer(self)
        self._typewriter_timer.setInterval(12)
        self._typewriter_timer.timeout.connect(self._process_typewriter)
        self._console_anim = None
        
        # Tema Oscuro Premium con tonalidades Azules (Midnight Blue)
        self.setStyleSheet("""
            QMainWindow { background-color: #0F172A; }
            QLabel { color: #E2E8F0; font-weight: bold; font-family: 'Segoe UI', 'Inter', sans-serif;}
            
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid #1E293B; 
                border-radius: 8px; 
                margin-top: 15px; 
                padding: 15px;
                background-color: #0B1120;
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 12px; 
                padding: 0 8px; 
                color: #38BDF8;
                background-color: #0F172A;
                font-size: 13px;
            }
            
            QListWidget { 
                background-color: #020617; 
                color: #F8FAFC; 
                border: 1px solid #1E293B; 
                border-radius: 6px; 
                font-size: 13px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
            }
            QListWidget::item:selected { 
                background-color: #1D4ED8; 
                color: #FFFFFF;
            }
            
            QPlainTextEdit { 
                background-color: #020617; 
                color: #38BDF8; 
                font-family: 'Fira Code', 'Consolas', 'Courier New', monospace; 
                border: 1px solid #1E293B; 
                border-radius: 6px; 
                padding: 10px;
                font-size: 13px;
            }
            
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                color: #F8FAFC; 
                border: 1px solid #334155; 
                border-bottom: 3px solid #2563EB;
                padding: 12px 16px; 
                border-radius: 6px; 
                font-weight: bold; 
                font-size: 13px;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563EB, stop:1 #1D4ED8);
                border-color: #60A5FA;
                border-bottom: 3px solid #1E40AF;
                color: #FFFFFF;
            }
            QPushButton:pressed { 
                background-color: #1E3A8A;
                border-bottom: 1px solid #1E40AF;
                padding-top: 13px;
            }
            QPushButton:disabled { 
                background-color: #0F172A; 
                border: 1px solid #1E293B;
                border-bottom: 2px solid #1E293B;
                color: #475569; 
            }
            
            QTabWidget::pane { 
                border: 1px solid #1E293B; 
                background-color: #0B1120; 
                border-radius: 6px;
            }
            QTabBar::tab { 
                background-color: #0F172A; 
                color: #94A3B8; 
                padding: 10px 22px; 
                font-weight: bold; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px;
                border: 1px solid #1E293B;
                border-bottom: none;
                margin-right: 4px;
            }
            QTabBar::tab:selected { 
                background-color: #0B1120; 
                color: #38BDF8; 
                border-top: 2px solid #38BDF8;
            }
            QTabBar::tab:hover:!selected {
                background-color: #1E293B;
                color: #F1F5F9;
            }
        """)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # -- Panel Izquierdo (Dispositivos Info y Logs) --
        left_panel = QVBoxLayout()
        
        info_group = QGroupBox("Hardware Detectado")
        info_layout = QVBoxLayout()
        self.device_list = QListWidget()
        self.device_list.setMaximumHeight(150)
        info_layout.addWidget(self.device_list)
        
        self.lbl_status = QLabel("Estado: Esperando conexión USB...")
        self.lbl_status.setStyleSheet("color: #F59E0B; font-size: 14px;") # Ámbar cuando espera
        info_layout.addWidget(self.lbl_status)
        
        info_group.setLayout(info_layout)
        left_panel.addWidget(info_group)
        
        # Consola de Logs
        log_group = QGroupBox("Terminal de Operaciones")
        log_layout = QVBoxLayout()
        
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console_opacity_effect = QGraphicsOpacityEffect(self.console)
        self.console.setGraphicsEffect(self.console_opacity_effect)
        
        # Header con botón para limpiar la consola
        log_header = QHBoxLayout()
        log_header.addStretch()
        self.btn_clear_log = QPushButton("🧹 Limpiar Consola")
        self.btn_clear_log.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_log.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: normal;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
                border-color: #475569;
            }
        """)
        self.btn_clear_log.clicked.connect(self._fade_clear_console)
        log_header.addWidget(self.btn_clear_log)
        log_layout.addLayout(log_header)
        log_layout.addWidget(self.console)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #1E293B; border-radius: 5px; text-align: center; color: #E2E8F0; }
            QProgressBar::chunk { background-color: #10B981; width: 10px; }
        """)
        self.progress_bar.hide() # Se mostrará solo cuando una operación lo necesite
        log_layout.addWidget(self.progress_bar)

        log_group.setLayout(log_layout)
        left_panel.addWidget(log_group)
        
        layout.addLayout(left_panel, 1) # Toma el 40% del ancho
        
        # -- Área Principal (Tabs y Botones Mágicos) --
        right_panel = QVBoxLayout()
        
        self.lbl_actions = QLabel(
            "⚡ Esperando dispositivo USB...\n\n"
            "Conecta un teléfono móvil (Samsung, etc.) por USB\n"
            "para descubrir automáticamente las acciones disponibles."
        )
        self.lbl_actions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_actions.setStyleSheet("""
            QLabel {
                font-size: 14px; 
                color: #94A3B8; 
                padding: 40px 25px; 
                background-color: #0B1120; 
                border: 2px dashed #1E293B; 
                border-radius: 10px;
                margin: 25px;
                line-height: 1.6;
            }
        """)
        self.actions_opacity_effect = QGraphicsOpacityEffect(self.lbl_actions)
        self.lbl_actions.setGraphicsEffect(self.actions_opacity_effect)
        self._setup_breathing_animation()
        right_panel.addWidget(self.lbl_actions)
        
        self.tabs = QTabWidget()
        
        # Tab Principal
        self.tab_actions = QWidget()
        self.tab_actions.setStyleSheet("background-color: #0F172A;")
        self.tab_actions_layout = QVBoxLayout(self.tab_actions)
        
        # Grid para meter los botones principales dinámicamente
        self.dynamic_buttons_widget = QWidget()
        self.dynamic_buttons_layout = QGridLayout(self.dynamic_buttons_widget)
        self.dynamic_buttons_layout.setSpacing(15)
        self.tab_actions_layout.addWidget(self.dynamic_buttons_widget)
        self.tab_actions_layout.addStretch()
        
        self.tabs.addTab(self.tab_actions, "Acciones Principales")
        
        # Tab MTP / ADB Tools
        self.tab_mtp_adb = QWidget()
        self.tab_mtp_adb.setStyleSheet("background-color: #0F172A;")
        self.tab_mtp_adb_layout = QVBoxLayout(self.tab_mtp_adb)
        
        # Grid para botones MTP y ADB
        self.mtp_adb_buttons_widget = QWidget()
        self.mtp_adb_buttons_layout = QGridLayout(self.mtp_adb_buttons_widget)
        self.mtp_adb_buttons_layout.setSpacing(15)
        self.tab_mtp_adb_layout.addWidget(self.mtp_adb_buttons_widget)
        self.tab_mtp_adb_layout.addStretch()
        
        self.tabs.addTab(self.tab_mtp_adb, "MTP / ADB Tools")
        
        right_panel.addWidget(self.tabs)
        self.tabs.hide() # Oculto hasta que se conecte el equipo
        
        # Botón de Abortar (oculto por defecto)
        self.btn_abort = QPushButton("🛑 ABORTAR OPERACIÓN")
        self.btn_abort.setStyleSheet("""
            QPushButton { background-color: #DC2626; color: white; border: none; padding: 15px; font-size: 14px; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background-color: #B91C1C; }
            QPushButton:pressed { background-color: #991B1B; }
        """)
        self.btn_abort.hide()
        self.btn_abort.clicked.connect(self._abort_operation)
        right_panel.addWidget(self.btn_abort)
        
        layout.addLayout(right_panel, 2) # Toma el 60% del ancho

    def _connect_signals(self):
        self.bridge.device_added.connect(self._on_device_added)
        self.bridge.device_removed.connect(self._on_device_removed)
        self.bridge.log_message.connect(self.log)
        self.bridge.operation_finished.connect(self._on_operation_finished)
        self.bridge.file_requested.connect(self._on_file_requested)
        self.bridge.dir_requested.connect(self._on_dir_requested)
        self.bridge.progress_update.connect(self._on_progress_update)

    def _on_progress_update(self, value: int):
        self.progress_bar.setValue(value)
        if value > 0 and value < 100:
            self.progress_bar.show()
        elif value == 100 or value < 0:
            # -1 can be used to hide it or hide it on finish
            pass # We leave 100 for a second to show completion OR handled below

    def _on_dir_requested(self, action_name: str, title: str):
        """Abre un diálogo de selección de carpeta."""
        dir_path = QFileDialog.getExistingDirectory(self, title, "")
        if dir_path:
            self.log(f"[+] Carpeta Firmware seleccionada: {dir_path}")
            self._execute_plugin_action(action_name, firmware_dir=dir_path)
        else:
            self.log("[!] Operación cancelada: No se seleccionó carpeta.")
            self._on_operation_finished()

    def _on_file_requested(self, action_name: str, title: str, file_filter: str):
        """Abre un diálogo de selección de archivos en el hilo de la GUI."""
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", file_filter)
        if file_path:
            self.log(f"[+] Archivo seleccionado: {file_path}")
            self._execute_plugin_action(action_name, file_path=file_path)
        else:
            self.log("[!] Operación cancelada: No se seleccionó ningún archivo.")
            self._on_operation_finished()

    def _setup_breathing_animation(self):
        """Configura y arranca el efecto de respiración para el cartel de espera."""
        self._breathing_group = QSequentialAnimationGroup(self)
        
        fade_down = QPropertyAnimation(self.actions_opacity_effect, b"opacity")
        fade_down.setDuration(1300)
        fade_down.setStartValue(1.0)
        fade_down.setEndValue(0.35)
        fade_down.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        fade_up = QPropertyAnimation(self.actions_opacity_effect, b"opacity")
        fade_up.setDuration(1300)
        fade_up.setStartValue(0.35)
        fade_up.setEndValue(1.0)
        fade_up.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self._breathing_group.addAnimation(fade_down)
        self._breathing_group.addAnimation(fade_up)
        self._breathing_group.setLoopCount(-1) # Infinito
        self._breathing_group.start()

    def _fade_clear_console(self):
        """Desvanece suavemente el texto de la consola antes de limpiarla."""
        if hasattr(self, '_typewriter_timer') and self._typewriter_timer.isActive():
            self._typewriter_timer.stop()
        self._typewriter_queue.clear()
        
        if not self.console.toPlainText().strip():
            self.console.clear()
            return
            
        self._console_anim = QPropertyAnimation(self.console_opacity_effect, b"opacity")
        self._console_anim.setDuration(220)
        self._console_anim.setStartValue(1.0)
        self._console_anim.setEndValue(0.0)
        self._console_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        def on_cleared():
            self.console.clear()
            self.console_opacity_effect.setOpacity(1.0)
            
        self._console_anim.finished.connect(on_cleared)
        self._console_anim.start()

    def _process_typewriter(self):
        """Escribe caracteres de la cola de forma adaptativa simulando una máquina de escribir."""
        q_len = len(self._typewriter_queue)
        if q_len == 0:
            self._typewriter_timer.stop()
            return
            
        # Velocidad adaptativa: si la cola se acumula por streams intensos (ej. Heimdall o ADB),
        # escribimos chunks más grandes para evitar retraso visual acumulado.
        if q_len > 1200:
            chunk_size = q_len
        elif q_len > 300:
            chunk_size = 35
        elif q_len > 80:
            chunk_size = 12
        elif q_len > 25:
            chunk_size = 4
        else:
            chunk_size = 1
            
        chunk_chars = []
        for _ in range(min(chunk_size, len(self._typewriter_queue))):
            chunk_chars.append(self._typewriter_queue.popleft())
        chunk = "".join(chunk_chars)
        
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.console.setTextCursor(cursor)
        self.console.ensureCursorVisible()
        
        if len(self._typewriter_queue) == 0:
            self._typewriter_timer.stop()

    def log(self, message: str):
        """Agrega texto a la cola de la terminal con efecto máquina de escribir."""
        formatted = f"> {message}\n"
        self._typewriter_queue.extend(formatted)
        if hasattr(self, '_typewriter_timer') and not self._typewriter_timer.isActive():
            self._typewriter_timer.start()

    def _on_device_added(self, devpath: str, plugin: BaseDevicePlugin):
        self.active_plugin = plugin
        self.lbl_status.setText(f"Estado: CONECTADO - {plugin.name}")
        self.lbl_status.setStyleSheet("color: #10B981; font-size: 14px;") # Emerald Green
        
        item_text = f"{plugin.name} [{devpath}]"
        self.device_list.addItem(item_text)
        self.log(f"[+] Hardware enlazado: {plugin.name}")
        
        self._build_dynamic_buttons(plugin)

    def _on_device_removed(self, devpath: str, plugin: BaseDevicePlugin):
        # Limpiar de la lista buscando por ruta o nombre de plugin
        for i in reversed(range(self.device_list.count())):
            item = self.device_list.item(i)
            if devpath in item.text() or plugin.name in item.text():
                self.device_list.takeItem(i)
            
        if self.device_list.count() == 0:
            self.lbl_status.setText("Estado: Esperando conexión USB...")
            self.lbl_status.setStyleSheet("color: #F59E0B; font-size: 14px;")
            self.active_plugin = None
            self._clear_dynamic_buttons()
            
        self.log(f"[-] Hardware desconectado: {plugin.name}")

    def _clear_dynamic_buttons(self):
        self.lbl_actions.show()
        if hasattr(self, '_breathing_group'):
            if self._breathing_group.state() != QAbstractAnimation.State.Running:
                self._breathing_group.start()
        self.tabs.hide()
        for layout in [self.dynamic_buttons_layout, self.mtp_adb_buttons_layout]:
            for i in reversed(range(layout.count())): 
                widget = layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

    def _build_dynamic_buttons(self, plugin: BaseDevicePlugin):
        self._clear_dynamic_buttons()
        if hasattr(self, '_breathing_group'):
            self._breathing_group.pause()
            self.actions_opacity_effect.setOpacity(1.0)
        self.lbl_actions.hide()
        self.tabs.show()
        
        actions = plugin.get_supported_actions()
        row_main, col_main = 0, 0
        row_mtp, col_mtp = 0, 0
        
        action_display_map = {
            # Diagnóstico y lectura
            "READ_INFO_AT": "📱 Leer Info Completa (AT)",
            "HEIMDALL_DETECT": "🔍 Detectar Modo Download",
            
            # Operaciones Menú de Emergencia (*#0*#) - acciones reales
            "ENABLE_TEST_MODE_ADB": "⚡ Habilitar Depuración ADB (*#0*#)",
            "TEST_MODE_REMOVE_FRP": "🔓 Eliminar Cuenta Google (FRP)",
            "TEST_MODE_FACTORY_RESET": "♻️ Restablecimiento de Fábrica",
            "TEST_MODE_DISABLE_KNOX": "🛡️ Deshabilitar Knox Guard",
            
            # Modo MTP
            "MTP_FACTORY_RESET": "⚠️ Factory Reset (MTP)",
            "MTP_REBOOT_DOWNLOAD_MODE": "⬇️ Reiniciar a Modo Download",
            "MTP_ENABLE_VZW_SECRET_CODE": "📟 Código Diagnóstico Módem",
            
            # Modo Download (Odin)
            "DOWNLOAD_FLASHER_HEIMDALL": "🔥 Flashear Firmware (Heimdall)",
            "DOWNLOAD_EXIT_MODE": "🚪 Salir de Modo Download",
            "DOWNLOAD_SOFT_BRICK_FIX": "🩹 Reparar Pantalla Emergencia",
            
            # Modo ADB
            "ADB_DEVICES": "🔌 Listar Dispositivos ADB",
            "ADB_GET_MODEL": "📋 Obtener Modelo por ADB",
            "ADB_CHANGE_CSC": "🌐 Cambiar Región / CSC",
            "ADB_REMOVE_SAMSUNG_ACCOUNT": "👤 Quitar Cuenta Samsung",
            "ADB_REBOOT_DOWNLOAD_MODE": "⬇️ Reiniciar a Download (ADB)",
            "FRP_BYPASS": "🔓 Bypass FRP Universal",
        }
        
        for action in actions:
            human_name = action_display_map.get(action, f"⚙️  {action.replace('_', ' ').title()}")
            btn = QPushButton(human_name)
            btn.setMinimumHeight(55)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, a=action: self._execute_plugin_action(a))
            
            if action.startswith("MTP_") or action.startswith("ADB_"):
                self.mtp_adb_buttons_layout.addWidget(btn, row_mtp, col_mtp)
                col_mtp += 1
                if col_mtp > 1: 
                    col_mtp = 0
                    row_mtp += 1
            else:
                self.dynamic_buttons_layout.addWidget(btn, row_main, col_main)
                col_main += 1
                if col_main > 1: 
                    col_main = 0
                    row_main += 1

    def _on_operation_finished(self):
        self.btn_abort.hide()
        self.dynamic_buttons_widget.setEnabled(True)
        self.mtp_adb_buttons_widget.setEnabled(True)
        # Ocultar barra de progreso tras 1.5s
        QTimer.singleShot(1500, self.progress_bar.hide)

    def _abort_operation(self):
        if hasattr(self, 'active_action_loop') and self.active_action_loop:
            if hasattr(self, 'active_action_task') and self.active_action_task:
                self.log("[!] Solicitando interrupción del proceso (SIGTERM)...")
                self.btn_abort.setEnabled(False)
                # Programar la cancelación de forma segura dentro del event loop
                self.active_action_loop.call_soon_threadsafe(self.active_action_task.cancel)

    def _execute_plugin_action(self, action_name: str, **kwargs):
        if not self.active_plugin: return
        self.log(f"[*] Lanzando acción: {action_name}...")
        
        self.dynamic_buttons_widget.setEnabled(False)
        self.mtp_adb_buttons_widget.setEnabled(False)
        self.btn_abort.setEnabled(True)
        self.btn_abort.show()
        
        def run_async():
            self.running_tasks += 1
            # Creamos un event loop propio para este hilo
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.active_action_loop = loop
            
            try:
                # Envolvemos la corrutina en una Task para poder cancelarla
                task = loop.create_task(self.active_plugin.execute_action(action_name, **kwargs))
                self.active_action_task = task
                
                result = loop.run_until_complete(task)
                
                # Handle requests for file picking (returns back to GUI Thread via signal)
                if result.get("status") == "request_file":
                    self.bridge.file_requested.emit(
                        action_name, 
                        result.get("title", "Selecciona un archivo"), 
                        result.get("filter", "*.*")
                    )
                    return # Exit this background thread, QFileDialog will restart the cycle
                    
                # Handle requests for directory picking
                elif result.get("status") == "request_dir":
                    self.bridge.dir_requested.emit(
                        action_name,
                        result.get("title", "Selecciona la carpeta del firmware")
                    )
                    return

                # Handle streams from CLIRunner (like ADB or Heimdall)
                elif result.get("status") == "stream":
                    generator = result.get("generator")
                    self.bridge.log_message.emit(f"[*] {result.get('message')}")
                    
                    async def consume_stream():
                        try:
                            async for item in generator:
                                if isinstance(item, tuple):
                                    # Formato: (mensaje, progreso_int)
                                    msg, progress = item
                                    self.bridge.log_message.emit(msg)
                                    self.bridge.progress_update.emit(progress)
                                else:
                                    self.bridge.log_message.emit(item.strip())
                        except asyncio.CancelledError:
                            self.bridge.log_message.emit("[ABORTADO] Stream interrumpido.")
                            self.bridge.progress_update.emit(0)
                            
                    loop.run_until_complete(consume_stream())
                elif result.get("status") == "success":
                    self.bridge.log_message.emit(f"[ÉXITO] {result.get('message')}")
                else:
                    self.bridge.log_message.emit(f"[ERROR] {result.get('message')}")
            except asyncio.CancelledError:
                self.bridge.log_message.emit("[ABORTADO] La operación fue cancelada por el usuario.")
            except Exception as e:
                self.bridge.log_message.emit(f"[FALLA CRÍTICA] {str(e)}")
            finally:
                self.active_action_task = None
                self.active_action_loop = None
                self.running_tasks -= 1
                loop.close()
                self.bridge.operation_finished.emit()

        threading.Thread(target=run_async, daemon=True).start()

    def closeEvent(self, event):
        """Intercepta el cierre de la ventana para evitar corromper procesos."""
        if self.running_tasks > 0:
            reply = QMessageBox.warning(
                self, '¡Advertencia de Seguridad!', 
                "Hay acciones en ejecución en segundo plano (ej. ADB o Puerto Serie).\n\n"
                "Si cerrás la aplicación ahora, podrías interrumpir un proceso de flasheo, "
                "dejar el teléfono inestable, o dejar el puerto USB bloqueado en Linux.\n\n"
                "¿Estás absolutamente seguro de forzar el cierre?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        event.accept()
