import pyudev
from typing import Callable, Optional

class USBMonitor:
    def __init__(self, callback: Callable[[str, str, str, str], None]):
        """
        Inicializa el monitor USB nativo de Linux.
        :param callback: Función a llamar cuando ocurre un evento.
                         Firma: callback(action, vid, pid, devpath)
        """
        self.callback = callback
        self._context = pyudev.Context()
        self._monitor = pyudev.Monitor.from_netlink(self._context)
        self._monitor.filter_by(subsystem='usb')
        self._observer: Optional[pyudev.MonitorObserver] = None

    def _process_event(self, device: pyudev.Device) -> None:
        """Procesa el evento crudo de pyudev y lo filtra."""
        action = device.action
        vid = device.get('ID_VENDOR_ID')
        pid = device.get('ID_MODEL_ID')
        devpath = device.get('DEVNAME') or getattr(device, 'device_node', None)
        
        if action == 'add':
            # En add requerimos VID y PID para mapear al plugin correspondiente
            if vid and pid and devpath:
                self.callback('add', vid.lower(), pid.lower(), devpath)
        elif action == 'remove':
            # En remove, en Linux real el hardware ya no existe en sysfs y VID/PID son None.
            # Notificamos con devpath para que DeviceManager desvincule el hardware.
            vid_str = vid.lower() if vid else ''
            pid_str = pid.lower() if pid else ''
            if devpath:
                self.callback('remove', vid_str, pid_str, devpath)

    def start(self) -> None:
        """Inicia el monitoreo en un hilo en segundo plano (nativamente provisto por pyudev)."""
        if self._observer is None:
            self._observer = pyudev.MonitorObserver(self._monitor, callback=self._process_event)
            self._observer.start()

    def stop(self) -> None:
        """Detiene el monitoreo."""
        if self._observer is not None:
            self._observer.stop()
            self._observer = None
