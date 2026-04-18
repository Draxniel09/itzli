#!/bin/bash
# Script para instalar las reglas udev necesarias para OpenUnlock-Linux
# Esto permite que tu usuario acceda a los puertos seriales y dispositivos USB crudos de Samsung sin usar 'sudo'.

if [ "$EUID" -ne 0 ]; then
  echo "Por favor, ejecuta este script como root (sudo ./install_rules.sh)"
  exit
fi

echo "[*] Agregando tu usuario al grupo 'dialout' y 'plugdev'..."
usermod -aG dialout $SUDO_USER
usermod -aG plugdev $SUDO_USER || true

echo "[*] Creando reglas udev para dispositivos Samsung (Vendor ID: 04E8)..."
cat << 'EOF' > /etc/udev/rules.d/99-openunlock-samsung.rules
# Samsung Móviles
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666", GROUP="plugdev"
# Puertos CDC ACM (Módems)
KERNEL=="ttyACM*", MODE="0666", GROUP="dialout"
EOF

echo "[*] Recargando reglas udev..."
udevadm control --reload-rules
udevadm trigger

echo "[ÉXITO] Reglas instaladas. POR FAVOR REINICIA TU COMPUTADORA (o cierra sesión y vuelve a entrar) para que los permisos de grupo se apliquen correctamente."
