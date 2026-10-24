"""
Utilidades para categorizar, extraer y mapear archivos de firmware Samsung.
Los firmware de Samsung vienen como .tar.md5 con prefijos estándar:
BL_ (Bootloader), AP_ (Android Platform), CP_ (Modem), CSC_ / HOME_CSC_.
"""
import os
import re
import tarfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ============================================================
# Modelo de datos
# ============================================================

@dataclass
class FirmwareSlot:
    """Representa una partición de firmware Samsung (BL, AP, CP, CSC)."""
    slot_name: str       # BL, AP, CP, CSC, HOME_CSC
    file_path: str       # Ruta al archivo .tar.md5 o .img
    display_name: str    # Nombre legible
    inner_files: List[str] = field(default_factory=list)  # Archivos extraídos


# ============================================================
# Constantes de mapeo
# ============================================================

# Orden importa: HOME_CSC antes de CSC para evitar match parcial
SLOT_PATTERNS = [
    ("HOME_CSC", re.compile(r'^HOME_CSC_', re.IGNORECASE), "CSC (Preserva datos)"),
    ("BL",       re.compile(r'^BL_',       re.IGNORECASE), "Bootloader"),
    ("AP",       re.compile(r'^AP_',       re.IGNORECASE), "Android Platform (System)"),
    ("CP",       re.compile(r'^CP_',       re.IGNORECASE), "Communication Processor (Modem)"),
    ("CSC",      re.compile(r'^CSC_',      re.IGNORECASE), "Consumer Software Customization"),
    ("USERDATA", re.compile(r'^USERDATA_', re.IGNORECASE), "User Data"),
]

# Mapeo de archivos extraídos → nombre de partición para Heimdall
FILE_TO_PARTITION: Dict[str, str] = {
    "sboot.bin":       "BOOTLOADER",
    "boot.img":        "BOOT",
    "boot.img.lz4":    "BOOT",
    "recovery.img":    "RECOVERY",
    "recovery.img.lz4":"RECOVERY",
    "system.img":      "SYSTEM",
    "system.img.lz4":  "SYSTEM",
    "system.img.ext4": "SYSTEM",
    "vendor.img":      "VENDOR",
    "vendor.img.lz4":  "VENDOR",
    "modem.bin":       "RADIO",
    "cache.img":       "CACHE",
    "cache.img.lz4":   "CACHE",
    "cache.img.ext4":  "CACHE",
    "param.bin":       "PARAM",
    "dtbo.img":        "DTBO",
    "dtbo.img.lz4":    "DTBO",
    "vbmeta.img":      "VBMETA",
    "vbmeta.img.lz4":  "VBMETA",
    "super.img":       "SUPER",
    "super.img.lz4":   "SUPER",
    "optics.img":      "OPTICS",
    "optics.img.lz4":  "OPTICS",
    "prism.img":       "PRISM",
    "prism.img.lz4":   "PRISM",
    "omr.img":         "OMR",
    "omr.img.lz4":     "OMR",
    "userdata.img":    "USERDATA",
    "userdata.img.ext4":"USERDATA",
}


# ============================================================
# Funciones principales
# ============================================================

def categorize_firmware_file(file_path: str) -> Optional[FirmwareSlot]:
    """Auto-detecta la partición de un archivo Samsung por su nombre."""
    basename = os.path.basename(file_path)
    for slot_name, pattern, display in SLOT_PATTERNS:
        if pattern.match(basename):
            return FirmwareSlot(
                slot_name=slot_name,
                file_path=file_path,
                display_name=display,
            )
    return None


def categorize_firmware_files(file_paths: List[str]) -> Dict[str, FirmwareSlot]:
    """Categoriza múltiples archivos de firmware en sus slots."""
    result: Dict[str, FirmwareSlot] = {}
    for path in file_paths:
        slot = categorize_firmware_file(path)
        if slot:
            result[slot.slot_name] = slot
    return result


def extract_tar_md5(tar_path: str, dest_dir: str) -> List[str]:
    """
    Extrae un .tar.md5 (o .tar) a dest_dir.
    Los .tar.md5 de Samsung son archivos TAR con un hash MD5 al final del archivo.
    tarfile los abre sin problema porque ignora el trailing data.
    """
    try:
        with tarfile.open(tar_path, 'r') as tar:
            # Seguridad: filtrar paths con traversal (../)
            safe_members = [
                m for m in tar.getmembers()
                if not m.name.startswith('/') and '..' not in m.name
            ]
            tar.extractall(path=dest_dir, members=safe_members)
            return [
                os.path.join(dest_dir, m.name) 
                for m in safe_members if m.isfile()
            ]
    except (tarfile.TarError, OSError) as e:
        raise RuntimeError(f"No se pudo extraer '{os.path.basename(tar_path)}': {e}")


def map_extracted_to_partitions(file_paths: List[str]) -> Dict[str, str]:
    """Mapea archivos extraídos a nombres de partición de Heimdall."""
    result: Dict[str, str] = {}
    for path in file_paths:
        basename = os.path.basename(path).lower()
        for filename, partition in FILE_TO_PARTITION.items():
            if basename == filename.lower():
                result[partition] = path
                break
    return result


def build_heimdall_command(partition_map: Dict[str, str], no_reboot: bool = False) -> List[str]:
    """Construye el comando heimdall flash desde un mapa de particiones."""
    if not partition_map:
        raise ValueError("No hay particiones para flashear.")
    cmd = ["heimdall", "flash"]
    for partition, file_path in sorted(partition_map.items()):
        cmd.extend([f"--{partition}", file_path])
    if no_reboot:
        cmd.append("--no-reboot")
    return cmd
