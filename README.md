# Itzli ⚡

> **A Modular, Clean-Architecture Linux Platform for Mobile Device Repair and Diagnostics**

[English](README.md) | [Español](README.es.md)

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20(Universal)-orange.svg)](https://kernel.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-green.svg)](https://www.qt.io/)
[![Architecture](https://img.shields.io/badge/Architecture-Micro--kernel%20%7C%20Hexagonal-purple.svg)]()
[![Tests](https://img.shields.io/badge/tests-26%2F26%20passing-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-GNU%20GPLv3-blue.svg)](LICENSE)

---

## 📌 Overview

**Itzli** is an open-source, native Linux desktop application engineered to diagnose, flash, and repair mobile devices (Samsung, MediaTek, generic Android ADB/Fastboot, etc.) without relying on proprietary hardware dongles, questionable Windows cracked binaries, or paid SaaS subscriptions.

In an industry historically plagued by closed-source tools, ad-supported wrappers, and security risks, **Itzli** brings modern software engineering standards to mobile forensics and repair: **Clean Architecture, asynchronous non-blocking I/O, micro-kernel extensibility, and 100% mocked automated testing.**

> ⚠️ **Project Status**: **Active Development (Alpha / MVP)**. Core architecture, plugin system, hardware monitoring, and Samsung AT diagnostic engines are fully operational and covered by automated test suites.

---

## 🏛️ Architectural Highlights & Design Decisions

Itzli was designed with strict architectural principles to guarantee scalability, maintainability, and rock-solid stability when interfacing with low-level Linux kernel interfaces.

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                     │
│               PySide6 (Qt6) Modern Dark GUI                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
               Thread-Safe Event Bridge (Queue + QTimer)
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                      Core Domain Engine                     │
│    DeviceManager (Orchestrator) ── PluginManager (Loader)   │
│             ▲                                               │
│             │ implements                                    │
│    ┌────────┴───────────────────────────┐                   │
│    │ BaseDevicePlugin Interface         │                   │
└────┼────────────────────────────────────┼───────────────────┘
     │                                    │
┌────┴────────────────────────┐ ┌─────────┴───────────────────┐
│     Adapters / I/O Layer    │ │       Plugin Ecosystem      │
│  - USBMonitor (pyudev)      │ │  - SamsungPlugin (AT/Modem) │
│  - SerialPortAdapter        │ │  - UniversalPlugin (ADB)    │
│  - CLIRunner (async stream) │ │  - [Future] MediaTek BROM   │
│  - USBInjector (pyusb MTP)  │ │  - [Future] Qualcomm EDL    │
└─────────────────────────────┘ └─────────────────────────────┘
```

### 1. Micro-Kernel Plugin System (Extensibility)
The core application knows **nothing** about specific phone brands. It exposes a formal contract ([`BaseDevicePlugin`](itzli/core/interfaces.py)) requiring plugins to declare:
- Supported `(VID, PID)` USB tuples.
- Available actions (e.g., `READ_INFO_AT`, `ENABLE_TEST_MODE_ADB`, `HEIMDALL_DETECT`).
- Asynchronous execution routines.

Adding support for a new OEM (Xiaomi, Motorola, Spreadtrum) simply requires dropping a new `.py` file into [`itzli/plugins/`](itzli/plugins/) without touching the core orchestration engine.

### 2. Thread-Safe Event Bridge (Overcoming Python/C++ ABI Segfaults)
* **The Problem:** `pyudev` listens to netlink kernel events on a dedicated native Linux background thread. Directly calling Qt GUI signals (`.emit()`) across thread boundaries with complex Python objects causes random segmentation faults (`SIGSEGV`) in the PySide6/Qt C++ bridge.
* **The Solution:** A decoupled event bus using a thread-safe [`queue.Queue`](main.py) combined with a high-frequency `QTimer` poller running on Qt's main event loop. The kernel thread only appends tuples to the queue; the GUI thread processes and dispatches events cleanly.

### 3. Non-Blocking Streaming CLI Runner
Flashing and repair tasks (like `heimdall flash` or `adb logcat`) produce continuous terminal output. Instead of blocking the UI or buffering entire logs in memory, [`CLIRunner`](itzli/adapters/cli_runner.py) leverages `asyncio.subprocess` and Python asynchronous generators (`yield line`) to stream logs directly to the user interface in real time.

### 4. Reverse-Engineered Modem Diagnostic Fallback
Samsung devices often reject standard AT queries (`AT+DEVCONINFO`) depending on the firmware Knox state (`PACM/AP NOT_ALLOWED`). Itzli implements an intelligent fallback parser that analyzes raw modem descriptors to accurately retrieve IMEI, Serial Number, CSC, and Model even when security mitigations are tripped.

---

## ✨ Current Capabilities (MVP)

- [x] **Zero-Polling USB Hotplug Detection:** Instant device plug/unplug tracking via native Linux `udev` netlink sockets.
- [x] **Samsung Modem & AT Engine:**
  - Automatic detection of Samsung diagnostic serial interfaces (`/dev/ttyACM*`, `/dev/ttyUSB*`).
  - MTP-to-Modem USB configuration switching via `pyusb`.
  - Comprehensive device identification: Model, IMEI, Baseband, Software Version, Network Lock, CSC.
- [x] **Universal Android ADB Pipeline:**
  - Live asynchronous stream of `adb devices` and shell actions.
  - Dependency pre-flight validation (checks if `adb`, `heimdall`, etc. are installed).
- [x] **Safe Background Abort:** Cancellation of running asynchronous tasks and sub-processes without leaving orphaned zombies.
- [x] **SamFW-Inspired Hacker Dark UI:** Responsive layout with dynamic action button generation tailored to the detected connected device.

---

## 🗺️ Roadmap & Upcoming Milestones

- [ ] **Heimdall Flashing Suite:** Visual partition manager, PIT file parser, and ROM flashing engine.
- [ ] **MediaTek (MTK) BROM Engine:** Deep integration with `mtkclient` for handshake bypass and partition dumping.
- [ ] **Qualcomm Emergency Download (EDL):** Sahara / Firehose protocol integration.
- [ ] **Universal Packaging:** Official AppImage, Flatpak, and Arch Linux AUR distribution builds.

---

## 🚀 Getting Started

### System Requirements & External Dependencies
- Modern Linux distribution (Fedora, Debian, Ubuntu, Arch, openSUSE).
- **Python >= 3.10**
- **Poetry** (package and dependency manager)
- Hardware utilities: `adb` (Android Debug Bridge), `heimdall` (Samsung Flasher), `libusb`, and `udev` development libraries.

#### Install System Packages:

```bash
# Fedora / RHEL
sudo dnf install android-tools heimdall systemd-devel libusb1-devel python3-devel

# Ubuntu / Debian
sudo apt install adb heimdall-flash libudev-dev libusb-1.0-0-dev python3-dev

# Arch Linux
sudo pacman -S android-tools heimdall libusb python-poetry
```

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Draxniel09/itzli.git
cd itzli

# 2. Install Python dependencies in virtualenv via Poetry
poetry install

# 3. Configure udev rules (Mandatory for non-root USB access)
sudo ./install_rules.sh
```

> 🔒 **Security First — Why `install_rules.sh` is required:**
> Communicating with raw USB hardware and modem serial ports on Linux normally requires root permissions. However, **you should NEVER run desktop GUI applications with `sudo`**, as doing so risks corrupting your desktop environment's display sockets (Wayland/X11) and creating root-owned configuration files in your home directory.
> Running `sudo ./install_rules.sh` **once** installs kernel `udev` rules and grants your user membership to the `dialout` and `plugdev` groups, enabling Itzli to run seamlessly with standard, unprivileged user permissions. *(Note: Log out and back in after running this script for group memberships to take effect).*

### Launching the Application (Never use `sudo` here)

```bash
poetry run python main.py
```

---

## 🧪 Testing & Quality Assurance

Itzli adheres to strict test-driven development practices. Hardware interfaces (serial ports, USB endpoints, udev monitoring, and system binaries) are fully decoupled and mocked to ensure deterministic, fast CI/CD execution without requiring physical devices attached.

Run the test suite:
```bash
# Run tests in offscreen mode (ideal for headless servers / CI)
QT_QPA_PLATFORM=offscreen poetry run pytest -v
```

### Test Coverage Highlights:
- **`test_device_manager.py`**: State machine validation on device insertion, removal, and unrecognized hardware.
- **`test_samsung_plugin.py` & `extended`**: AT command timeout handling, modem fallback parsing, and missing binary detection.
- **`test_udev_monitor.py`**: Filter logic validating that non-USB udev events are cleanly discarded.
- **`test_gui.py`**: Qt signal integrity, typewriter log queue, and animation lifecycle synchronization via `pytest-qt` (`qtbot`).

---

## 🤝 Contributing

Contributions from the open-source community are warmly welcomed!

### 💡 Good First Issues & Contribution Opportunities
Looking to make your first contribution? Here are great starting points:
- **New Device Plugins**: Implement a subclass of [`BaseDevicePlugin`](itzli/core/interfaces.py) in `itzli/plugins/` for other brands (e.g., Motorola Fastboot, MediaTek BROM handshake, or Xiaomi Fastboot).
- **Extended Samsung AT Commands**: Add diagnostic queries for battery health cycles, Knox warranty bit, or CSC country list in [`SamsungPlugin`](itzli/plugins/samsung.py).
- **Mock Test Coverage**: Expand unit tests under `tests/` for exotic serial modem responses and error conditions.
- **UI Themes & Localization**: Add support for language catalogs (i18n) or custom color schemes in PySide6.

### 🛠️ Development Workflow

1. **Fork & Branch**:
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. **Environment & Testing**:
   Make sure all tests pass before making changes:
   ```bash
   QT_QPA_PLATFORM=offscreen poetry run pytest -v
   ```
3. **Coding Standards**:
   - Follow clean architecture boundaries (Adapters vs. Core vs. GUI).
   - Never block the GUI thread — all I/O must be asynchronous or offloaded.
   - Mock all hardware interactions in new test cases.
4. **Commit Guidelines**:
   Use **Conventional Commits** format (e.g., `feat(plugin): add motorola fastboot support` or `fix(udev): handle unplug edge case`).
   > *Note: Please do not include AI co-authoring metadata ("Co-Authored-By") in commit messages.*
5. **Submit a Pull Request**: Describe your change, architectural motivation, and verification steps.

---

## 👨‍💻 Author & Lead Maintainer

**Daniel Mata Ruiz** ([@Draxniel09](https://github.com/Draxniel09))
- System Architecture, Core Engine & Lead Maintainer

---

## 🙏 Acknowledgements & Credits

Itzli stands on the shoulders of giants in the open-source hardware, reverse-engineering, and mobile forensics communities:

- **[Benjamin Dobell](https://github.com/Benjamin-Dobell) & Glass Echidna** — Creators of **[Heimdall](https://github.com/Benjamin-Dobell/Heimdall)**, the pioneering cross-platform suite for flashing firmware onto Samsung Galaxy devices via the Odin protocol without Windows.
- **[Android Open Source Project (AOSP)](https://source.android.com/) & Google** — For the **Android Debug Bridge (ADB)** and core platform toolkits.
- **The XDA Developers & SamFW Community** — For documenting Samsung AT modem commands, test mode interfaces (`*#0*#`), and hardware troubleshooting methodologies.
- **[libusb](https://libusb.info/) & [pyusb](https://github.com/pyusb/pyusb)** — For providing low-level, cross-platform USB device communication interfaces.
- **[The Qt Company](https://www.qt.io/) & PySide6** — For delivering a robust, performant C++ GUI framework with native Python bindings.

---

## ⚖️ License

Distributed under the **GNU General Public License v3.0 (GPLv3)**. See `LICENSE` for more information.

---

## ⚠️ Disclaimer

> **IMPORTANT TECHNICAL AND LEGAL NOTICE:**
> 
> 1. **Educational Purpose & Right to Repair:** Itzli was created strictly for technical research, diagnostics, software engineering education, and in support of users' legitimate right to repair their own hardware.
> 2. **Firmware Modification Inherent Risks:** Interacting directly with device bootloaders, serial modems, and flash partitions (NAND/UFS) carries inherent risks. Incorrect commands, corrupted images, or interrupted connections may cause severe hardware malfunction, permanent bricking, bootloops, or unrecoverable data loss.
> 3. **No Warranty (AS IS):** This software is provided under the terms of the GNU GPLv3 on an "AS IS" basis, **WITHOUT WARRANTY OF ANY KIND**, express or implied. The author, contributors, and maintainers assume no liability for damaged hardware, lost personal data, financial losses, or voided OEM warranties.
> 4. **Lawful and Authorized Use Only:** It is strictly prohibited to utilize this software for unauthorized or unlawful purposes, including but not limited to unlocking devices of illicit origin, circumventing enterprise/carrier theft protection illegally, or altering hardware identifiers (IMEI/MEID) where prohibited by local or international law. The user assumes full responsibility for ensuring they possess explicit authorization from the legal device owner before executing any operation.
