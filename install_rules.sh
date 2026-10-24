#!/bin/bash
# Script para instalar las reglas udev necesarias para Itzli
# Esto permite que tu usuario acceda a los puertos seriales y dispositivos USB crudos de Samsung sin usar 'sudo'.

if [ "$EUID" -ne 0 ]; then
  echo "Por favor, ejecuta este script como root (sudo ./install_rules.sh)"
  exit
fi

echo "[*] Agregando tu usuario al grupo 'dialout' y 'plugdev'..."
usermod -aG dialout $SUDO_USER
usermod -aG plugdev $SUDO_USER 2>/dev/null || true

# Limpieza de reglas legacy si existen
if [ -f /etc/udev/rules.d/99-openunlock-samsung.rules ]; then
  echo "[*] Removiendo archivo de reglas obsoleto (99-openunlock-samsung.rules)..."
  rm -f /etc/udev/rules.d/99-openunlock-samsung.rules
fi

echo "[*] Creando reglas udev para dispositivos Samsung (Vendor ID: 04E8)..."
cat << 'EOF' > /etc/udev/rules.d/99-itzli-samsung.rules
# Samsung Móviles (Acceso directo a USB)
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666", GROUP="plugdev"
# Puertos CDC ACM / Módems serie
KERNEL=="ttyACM*", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB*", MODE="0666", GROUP="dialout"
EOF

echo "[*] Recargando reglas udev en el kernel..."
udevadm control --reload-rules
udevadm trigger

echo "[ÉXITO] Reglas instaladas. POR FAVOR REINICIA TU COMPUTADORA (o cierra sesión y vuelve a entrar) para que los permisos de grupo se apliquen correctamente."
