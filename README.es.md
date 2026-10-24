# Itzli ⚡

> **Plataforma Modular y de Arquitectura Limpia en Linux para Diagnóstico y Reparación de Dispositivos Móviles**

[English](README.md) | [Español](README.es.md)

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20(Universal)-orange.svg)](https://kernel.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-green.svg)](https://www.qt.io/)
[![Architecture](https://img.shields.io/badge/Architecture-Micro--kernel%20%7C%20Hexagonal-purple.svg)]()
[![Tests](https://img.shields.io/badge/tests-26%2F26%20passing-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-GNU%20GPLv3-blue.svg)](LICENSE)

---

## 📌 Visión General

**Itzli** es una aplicación de escritorio nativa para Linux diseñada para diagnosticar, flashear y reparar dispositivos móviles (Samsung, MediaTek, Android genérico mediante ADB/Fastboot, etc.) sin depender de cajas de hardware ("dongles") privativas, binarios crakeados dudosos para Windows o suscripciones mensuales opacas.

En una industria históricamente dominada por herramientas de código cerrado, bloatware y riesgos de seguridad, **Itzli** introduce estándares rigurosos de ingeniería de software a la reparación móvil y forense: **Arquitectura Limpia, I/O asíncrono no bloqueante, extensibilidad mediante micro-kernel y una suite de pruebas automatizadas al 100% con hardware mockeado.**

> ⚠️ **Estado del Proyecto**: **Desarrollo Activo (Alpha / MVP)**. El núcleo arquitectónico, el cargador dinámico de plugins, la monitorización de hardware udev y el motor de diagnóstico AT de Samsung se encuentran 100% operativos y validados mediante tests unitarios.

---

## 🏛️ Decisiones de Arquitectura y Diseño

Itzli fue concebido bajo principios estrictos de arquitectura de software para garantizar estabilidad y desacople frente a las interfaces de bajo nivel del kernel de Linux.

```
┌─────────────────────────────────────────────────────────────┐
│                      Capa de Presentación                   │
│               PySide6 (Qt6) GUI Modo Oscuro Moderno         │
└──────────────────────────────┬──────────────────────────────┘
                               │
               Puente Thread-Safe (Cola + Sondeo QTimer)
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    Motor del Dominio (Core)                 │
│    DeviceManager (Orquestador) ── PluginManager (Loader)    │
│             ▲                                               │
│             │ implementa                                    │
│    ┌────────┴───────────────────────────┐                   │
│    │ Interfaz BaseDevicePlugin          │                   │
└────┼────────────────────────────────────┼───────────────────┘
     │                                    │
┌────┴────────────────────────┐ ┌─────────┴───────────────────┐
│     Capa de Infraestructura │ │      Ecosistema de Plugins  │
│  - USBMonitor (pyudev)      │ │  - SamsungPlugin (AT/Modem) │
│  - SerialPortAdapter        │ │  - UniversalPlugin (ADB)    │
│  - CLIRunner (async stream) │ │  - [Futuro] MediaTek BROM   │
│  - USBInjector (pyusb MTP)  │ │  - [Futuro] Qualcomm EDL    │
└─────────────────────────────┘ └─────────────────────────────┘
```

### 1. Sistema Micro-Kernel Basado en Plugins
El núcleo de la aplicación desconoce deliberadamente las particularidades de marcas o modelos concretos. Expone un contrato formal (`BaseDevicePlugin`) que obliga a cada plugin a definir:
- Tuplas de identificación USB `(VID, PID)` soportadas.
- Catálogo de acciones disponibles (ej. `READ_INFO_AT`, `ENABLE_TEST_MODE_ADB`, `HEIMDALL_DETECT`).
- Rutinas de ejecución asíncronas no bloqueantes.

Agregar compatibilidad con un nuevo fabricante (Xiaomi, Motorola, Spreadtrum) se reduce a crear un archivo en `itzli/plugins/` sin necesidad de tocar ni alterar el orquestador principal.

### 2. Puente de Eventos Thread-Safe (Blindaje ante Segfaults de C++/Python)
* **El Problema:** `pyudev` procesa los eventos netlink del kernel en un hilo nativo de Linux (C). Invocar directamente señales de Qt (`.emit()`) desde dicho hilo hacia la GUI provoca fallos de segmentación aleatorios (`SIGSEGV`) en la frontera de la ABI C++/Python de PySide6.
* **La Solución:** Un bus desacoplado donde el hilo de hardware únicamente deposita tuplas en una cola `queue.Queue` (operación puramente atómica y thread-safe en Python), mientras que un `QTimer` de alta frecuencia en el hilo principal de Qt extrae los eventos y emite las señales de forma segura en el bucle de eventos.

### 3. Ejecución de Comandos con Streaming Asíncrono
Operaciones pesadas (como flashear particiones o monitorear logs en vivo) emiten texto continuo. En vez de bloquear la interfaz o acumular buffers gigantescos en memoria, `CLIRunner` utiliza `asyncio.subprocess` y generadores asíncronos (`yield line`) para volcar la salida a la consola de la UI en tiempo real.

### 4. Analizador de Respaldo para Módems Samsung
Muchos terminales Samsung restringen las respuestas AT directas ante protecciones Knox (`PACM/AP NOT_ALLOWED`). Itzli cuenta con un parser inteligente que analiza tramas de bajo nivel (`+DEVCONINFO`) para extraer de forma certera Modelo, IMEI, Versión de Software, CSC y estado de bloqueo de red.

---

## ✨ Capacidades Actuales (MVP)

- [x] **Detección USB Hotplug con Cero Sondeo:** Monitoreo instantáneo de inserción/remoción mediante sockets netlink de `udev`.
- [x] **Motor AT y Módem para Samsung:**
  - Detección automática de interfaces serie (`/dev/ttyACM*`, `/dev/ttyUSB*`).
  - Conmutación de configuración USB de MTP a Módem mediante inyección de descriptores con `pyusb`.
  - Extracción completa de información técnica: Modelo, IMEI, Versión de Baseband, Software y Estado de Bloqueo.
- [x] **Canal Universal ADB para Android:**
  - Streaming asíncrono en vivo de salida de `adb devices` y comandos shell.
  - Validación previa del entorno (verificación de presencia de binarios del sistema).
- [x] **Cancelación Segura en Segundo Plano:** Interrupción ordenada de tareas asíncronas y subprocesos sin dejar procesos huérfanos ("zombies").
- [x] **Interfaz Gráfica Dark Mode (Inspirada en herramientas profesionales):** Generación dinámica de botones y acciones según el hardware detectado.

---

## 🗺️ Hoja de Ruta (Roadmap)

- [ ] **Suite de Flasheo con Heimdall:** Gestor visual de particiones, analizador de archivos PIT y flasheo de imágenes ROM.
- [ ] **Motor MediaTek (MTK) BROM:** Integración con `mtkclient` para bypass de autenticación y volcado de particiones.
- [ ] **Qualcomm Emergency Download (EDL):** Implementación de protocolos Sahara y Firehose.
- [ ] **Empaquetado Universal:** Distribución en AppImage, Flatpak y paquete AUR para Arch Linux.

---

## 🚀 Puesta en Marcha

### Requisitos del Sistema y Dependencias Externas
- Cualquier distribución moderna de Linux (Fedora, Debian, Ubuntu, Arch, openSUSE).
- **Python >= 3.10**
- **Poetry** (gestor de entornos y dependencias)
- Utilidades de hardware del sistema: `adb` (Android Debug Bridge), `heimdall` (Flasheador Samsung), `libusb` y librerías de desarrollo de `udev`.

#### Instalar Paquetes del Sistema:

```bash
# Fedora / RHEL
sudo dnf install android-tools heimdall systemd-devel libusb1-devel python3-devel

# Ubuntu / Debian
sudo apt install adb heimdall-flash libudev-dev libusb-1.0-0-dev python3-dev

# Arch Linux
sudo pacman -S android-tools heimdall libusb python-poetry
```

### Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/Draxniel09/itzli.git
cd itzli

# 2. Instalar dependencias en el entorno virtual mediante Poetry
poetry install

# 3. Instalar reglas udev (Imprescindible para acceso USB sin privilegios de root)
sudo ./install_rules.sh
```

> 🔒 **Seguridad Primero — ¿Por qué es fundamental `install_rules.sh`?**
> La comunicación con hardware USB y módems serie en Linux habitualmente exige privilegios de superusuario. Sin embargo, **NUNCA debes ejecutar una aplicación gráfica con `sudo`**, ya que corres el riesgo de corromper los sockets del servidor de pantalla (Wayland/X11) y crear archivos propiedad de root en tu carpeta de usuario.
> Ejecutar `sudo ./install_rules.sh` **una única vez** instala las reglas de `udev` necesarias en el kernel y añade a tu usuario a los grupos `dialout` y `plugdev`. Esto permite que Itzli funcione con tu usuario estándar, sin elevar privilegios innecesariamente. *(Nota: Recuerda cerrar sesión y volver a entrar tras ejecutar el script para que los grupos se actualicen en tu sesión).*

### Ejecutar la Aplicación (Nunca usar `sudo` aquí)

```bash
poetry run python main.py
```

---

## 🧪 Pruebas y Aseguramiento de Calidad

Itzli se desarrolla bajo prácticas estrictas de TDD. Todas las interfaces de hardware (puertos serie, descriptores USB, eventos udev y binarios del sistema) están completamente desacopladas y mockeadas. Esto permite ejecutar pruebas de integración continua rápidas y determinísticas sin requerir teléfonos físicos conectados.

Ejecutar la suite completa:
```bash
# Ejecución en modo offscreen (ideal para servidores headless o CI/CD)
QT_QPA_PLATFORM=offscreen poetry run pytest -v
```

### Cobertura de Pruebas:
- **`test_device_manager.py`**: Máquina de estados ante conexión, desconexión y dispositivos no reconocidos.
- **`test_samsung_plugin.py` y `extended`**: Tiempos de espera AT, recuperación ante fallos de módem y detección de binarios ausentes.
- **`test_udev_monitor.py`**: Filtros de eventos de hardware descartando eventos no USB o sin VID/PID.
- **`test_gui.py`**: Integridad de señales de Qt, cola de terminal typewriter y ciclo de vida de animaciones mediante `pytest-qt` (`qtbot`).

---

## 🤝 Cómo Colaborar

¡Las contribuciones de la comunidad de código abierto son bienvenidas!

### 💡 Buenas Primeras Tareas (Good First Issues)
¿Querés hacer tu primer aporte al proyecto? Acá tenés excelentes puntos de partida:
- **Nuevos Plugins de Fabricantes**: Implementá una subclase de [`BaseDevicePlugin`](itzli/core/interfaces.py) en `itzli/plugins/` para otras marcas (ej. Motorola Fastboot, MediaTek BROM handshake o Xiaomi Fastboot).
- **Comandos AT Adicionales para Samsung**: Agregá lecturas de salud de batería, ciclo de carga, estado del flag Knox (Warranty Void) o lista de CSC en [`SamsungPlugin`](itzli/plugins/samsung.py).
- **Cobertura de Pruebas Unitarias**: Sumá tests en `tests/` testeando respuestas atípicas del módem serie o desconexiones forzadas.
- **Internacionalización y Temas**: Agregar catálogo de idiomas o soporte para selector de temas en la UI de PySide6.

### 🛠️ Flujo de Trabajo para Desarrolladores

1. **Fork y Rama de Trabajo**:
   ```bash
   git checkout -b feat/mi-nueva-caracteristica
   ```
2. **Entorno y Pruebas**:
   Asegurate de que todos los tests pasen antes y después de hacer cambios:
   ```bash
   QT_QPA_PLATFORM=offscreen poetry run pytest -v
   ```
3. **Estándares de Código**:
   - Respeta la separación de capas limpias (Adaptadores vs. Core vs. GUI).
   - Nunca bloquees el hilo principal de la GUI — todo I/O debe ser asíncrono o ejecutarse en segundo plano.
   - Todo nuevo código de hardware debe tener su respectivo test mockeado.
4. **Convención de Commits**:
   Utiliza el formato de **Conventional Commits** (ej. `feat(plugin): add motorola fastboot support` o `fix(udev): handle unplug edge case`).
   > *Nota: Por favor, no agregues firmas ni atribución de autoría por IA ("Co-Authored-By") en los commits.*
5. **Abre tu Pull Request**: Describe claramente el cambio realizado, la justificación arquitectónica y cómo verificarlo.

---

## 👨‍💻 Autor y Desarrollador Principal

**Daniel Mata Ruiz** ([@Draxniel09](https://github.com/Draxniel09))
- Arquitectura del Sistema, Motor Principal y Dirección del Proyecto

---

## 🙏 Agradecimientos y Créditos

Itzli se apoya en el trabajo fundamental de pioneros del software libre, la ingeniería inversa y la comunidad de reparación móvil:

- **[Benjamin Dobell](https://github.com/Benjamin-Dobell) y Glass Echidna** — Creadores de **[Heimdall](https://github.com/Benjamin-Dobell/Heimdall)**, la suite abierta que hizo posible flashear dispositivos Samsung Galaxy en Linux y macOS mediante el protocolo Odin sin depender de Windows.
- **[Android Open Source Project (AOSP)](https://source.android.com/) y Google** — Por el desarrollo de **ADB (Android Debug Bridge)** y las herramientas base de la plataforma Android.
- **La comunidad de XDA Developers y SamFW** — Por documentar a lo largo de los años secuencias AT de diagnóstico, modos de servicio (`*#0*#`) y métodos de recuperación de hardware.
- **[libusb](https://libusb.info/) y [pyusb](https://github.com/pyusb/pyusb)** — Por proveer librerías sólidas de acceso y manipulación de interfaces USB en Linux.
- **[The Qt Company](https://www.qt.io/) y PySide6** — Por un framework gráfico moderno, reactivo y de alto rendimiento.

---

## ⚖️ Licencia

Distribuido bajo la licencia **GNU General Public License v3.0 (GPLv3)**. Consulta el archivo `LICENSE` para conocer todos los detalles.

---

## ⚠️ Descargo de Responsabilidad (Disclaimer)

> **AVISO TÉCNICO Y LEGAL IMPORTANTE:**
> 
> 1. **Propósito Educativo y Derecho a Reparar:** Itzli ha sido desarrollado exclusivamente con fines de investigación, diagnóstico técnico, educación y en defensa del derecho legítimo de los usuarios a reparar sus propios dispositivos electrónicos.
> 2. **Riesgo de Modificación de Firmware:** La interacción con interfaces de bajo nivel, bootloaders y memorias flash (NAND/UFS) conlleva riesgos inherentes. El uso indebido de comandos, archivos de firmware corruptos o interrupciones en la transferencia de datos pueden provocar que un dispositivo quede inservible ("brickeado"), entre en bucle de reinicio ("bootloop") o sufra pérdida irrecuperable de información.
> 3. **Ausencia de Garantía:** El software se distribuye bajo la licencia GPLv3 "TAL CUAL" ("AS IS"), **SIN GARANTÍA DE NINGÚN TIPO**, expresa o implícita. Los autores, mantenedores y colaboradores de este proyecto no se hacen responsables de ningún daño directo, indirecto, incidental o consecuente a equipos físicos, datos personales o pérdida de garantías de fabricante.
> 4. **Uso Legal y Ético:** Queda terminantemente prohibido utilizar este software para actividades no autorizadas, tales como el desbloqueo o manipulación de dispositivos de origen ilícito, elusión ilegal de bloqueos patronales o alteración de identificadores de hardware (IMEI/MEID) en jurisdicciones donde dicha práctica esté penada por la ley. Es responsabilidad exclusiva del usuario asegurarse de que cualquier acción ejecutada sobre un equipo cuente con el consentimiento expreso de su propietario legal y respete la legislación vigente en su país.
