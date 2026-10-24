import asyncio
import time
import re
import functools
from typing import List, Dict, Any, Tuple, Optional, Callable, AsyncGenerator
from itzli.core.interfaces import BaseDevicePlugin
from itzli.adapters.serial_port import SerialPortAdapter
from itzli.adapters.usb_injector import USBInjectorAdapter
from itzli.adapters.cli_runner import CLIRunner

def handle_usb_errors(func: Callable) -> Callable:
    """
    Decorador para estandarizar y centralizar el manejo de errores
    de hardware, permisos y cancelación del usuario en llamadas de plugins.
    """
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs) -> Dict[str, Any]:
        try:
            return await func(self, *args, **kwargs)
        except PermissionError as e:
            return {"status": "error", "message": f"Falta de permisos: {str(e)}"}
        except RuntimeError as e:
            return {"status": "error", "message": f"Error de Hardware: {str(e)}"}
        except asyncio.CancelledError:
            if hasattr(self, "serial_adapter") and hasattr(self.serial_adapter, "logger"):
                self.serial_adapter.logger.info("Operación cancelada por el usuario.")
            raise
        except Exception as e:
            return {"status": "error", "message": f"Falla inesperada en operación ({func.__name__}): {str(e)}"}
    return wrapper

class SamsungPlugin(BaseDevicePlugin):
    """
    Plugin para operaciones específicas de dispositivos Samsung.
    Replica el comportamiento de herramientas como SamFW Tool nativamente en Linux.
    """
    
    def __init__(self, serial_adapter=None, usb_injector=None, cli_runner=None):
        self.serial_adapter = serial_adapter or SerialPortAdapter()
        self.usb_injector = usb_injector or USBInjectorAdapter()
        self.cli_runner = cli_runner or CLIRunner()
    
    @property
    def name(self) -> str:
        return "Samsung Factory Plugin"

    @property
    def supported_vid_pid(self) -> List[tuple[str, str]]:
        return [("04e8", "685d"), ("04e8", "6860")]

    def get_supported_actions(self) -> List[str]:
        return [
            # Acciones Base
            "READ_INFO_AT", "HEIMDALL_DETECT",
            # Test Mode (*#0*#)
            "ENABLE_TEST_MODE_ADB", "TEST_MODE_REMOVE_FRP", "TEST_MODE_FACTORY_RESET", "TEST_MODE_DISABLE_KNOX",
            # MTP Mode
            "MTP_FACTORY_RESET", "MTP_ENABLE_VZW_SECRET_CODE", "MTP_REBOOT_DOWNLOAD_MODE",
            # Download Mode
            "DOWNLOAD_EXIT_MODE", "DOWNLOAD_SOFT_BRICK_FIX", "DOWNLOAD_FLASHER_HEIMDALL",
            # ADB Mode
            "ADB_CHANGE_CSC", "ADB_REMOVE_SAMSUNG_ACCOUNT", "ADB_REBOOT_DOWNLOAD_MODE"
        ]

    async def execute_action(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Enruta la acción solicitada a la función correspondiente."""
        dispatcher = {
            "READ_INFO_AT": self._read_info_at,
            "HEIMDALL_DETECT": self._heimdall_detect,
            "ENABLE_TEST_MODE_ADB": self._enable_test_mode_adb,
            "TEST_MODE_REMOVE_FRP": self._test_mode_remove_frp,
            "TEST_MODE_FACTORY_RESET": self._test_mode_factory_reset,
            "TEST_MODE_DISABLE_KNOX": self._test_mode_disable_knox,
            "MTP_FACTORY_RESET": self._mtp_factory_reset,
            "MTP_ENABLE_VZW_SECRET_CODE": self._mtp_enable_vzw_secret_code,
            "MTP_REBOOT_DOWNLOAD_MODE": self._mtp_reboot_download_mode,
            "DOWNLOAD_EXIT_MODE": self._download_exit_mode,
            "DOWNLOAD_SOFT_BRICK_FIX": self._download_soft_brick_fix,
            "DOWNLOAD_FLASHER_HEIMDALL": self._download_flasher_heimdall,
            "ADB_CHANGE_CSC": self._adb_change_csc,
            "ADB_REMOVE_SAMSUNG_ACCOUNT": self._adb_remove_samsung_account,
            "ADB_REBOOT_DOWNLOAD_MODE": self._adb_reboot_download_mode,
        }
        
        if action in dispatcher:
            return await dispatcher[action](**kwargs)
        else:
            raise ValueError(f"Acción no soportada: {action}")

    # ==========================================
    # UTILIDADES INTERNAS
    # ==========================================
    
    async def _ensure_modem_port(self) -> str:
        """Intenta encontrar el puerto serie normal. Si falla, inyecta configuración USB."""
        port = self.serial_adapter.find_samsung_modem_port()
        if port: return port
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.usb_injector.force_modem_configuration)
        port = self.serial_adapter.find_samsung_modem_port()
        if not port: raise RuntimeError("Inyección MTP fallida. No se detectó /dev/ttyACM0. ¿Lanzaste install_rules.sh?")
        return port

    async def _stream_multiple_commands(self, cmds: List[List[str]]) -> AsyncGenerator[str, None]:
        """Ejecuta una secuencia de comandos CLI y unifica el stream de logs."""
        for cmd in cmds:
            yield f"\n[⚙️] Ejecutando: {' '.join(cmd)}\n"
            async for line in self.cli_runner.run_command(cmd):
                # Interceptar errores comunes de ADB para dar contexto útil al usuario
                if "device unauthorized" in line:
                    yield "\n[🚨] BLOQUEO DE SEGURIDAD ADB DETECTADO [🚨]"
                    yield "[!] El celular rechazó la conexión porque no confía en esta computadora."
                    yield "[!] Solución: Desbloqueá la pantalla del teléfono, marcá 'Permitir siempre' y dale a OK."
                    yield "[!] Luego volvé a intentar la operación.\n"
                elif "no devices/emulators found" in line:
                    yield "\n[!] ERROR: No se detectó ningún dispositivo en modo ADB. ¿Está activada la Depuración USB?\n"
                    
                yield line
        yield "\n[✓] Secuencia completada.\n"

    def _sync_at_command(self, port: str, command: str) -> Tuple[bool, str]:
        with self.serial_adapter.session(port) as session:
            return session.send_at_command(command)

    def _sync_read_info(self, port: str) -> Dict[str, Tuple[bool, str]]:
        results = {}
        with self.serial_adapter.session(port) as session:
            # Comando vacío de inicialización para limpiar buffer/despertar
            session.send_at_command("AT")
            time.sleep(0.3) # Extra delay para que el módem despierte
            
            results["model"] = session.send_at_command("AT+GMM")
            results["imei"] = session.send_at_command("AT+GSN")
            results["sw_ver"] = session.send_at_command("AT+SWVER")
            results["cimi"] = session.send_at_command("AT+CIMI")
            results["dev_info"] = session.send_at_command("AT+DEVCONINFO")
            
            return results

    # ==========================================
    # ACCIONES BASE
    # ==========================================

    @handle_usb_errors
    async def _read_info_at(self) -> Dict[str, Any]:
        port = await self._ensure_modem_port()
        loop = asyncio.get_running_loop()
        await asyncio.sleep(1.0)
        
        results = await loop.run_in_executor(None, self._sync_read_info, port)
        
        def extract_val(res: Tuple[bool, str]) -> str:
            success, raw = res
            if not raw:
                return "No disponible"
            
            # Limpiamos OK y evitamos ocultar errores de diagnóstico (ej. +CME Error)
            val = raw.replace("OK\r", "").replace("OK\n", "").replace("\r", "").strip()
            return val if val else "No disponible"

        model = extract_val(results["model"])
        imei = extract_val(results["imei"])
        sw_ver = extract_val(results["sw_ver"])
        cimi = extract_val(results["cimi"])
        dev_info = extract_val(results["dev_info"])

        # ====== Limpieza y Parseo Avanzado (Fallbacks) ======
        # Limpiar los prefijos molestos y formatear errores
        sw_ver = re.sub(r'^\+SWVER:\s*', '', sw_ver)
        
        if "CME Error" in cimi or "ERROR" in cimi:
            cimi = "No disponible (Bloqueado por Knox/PACM)"
            # Intentar extraer datos de la red (MCC/MNC) como alternativa al IMSI
            if dev_info and "DEVCONINFO" in dev_info:
                m_mcc = re.search(r'MCC\(([^)]+)\)', dev_info)
                m_mnc = re.search(r'MNC\(([^)]+)\)', dev_info)
                if m_mcc and m_mnc:
                    mcc = m_mcc.group(1).split(',')[0]
                    mnc = m_mnc.group(1).split(',')[0]
                    if mcc and mcc.isdigit():
                        cimi += f" - Red: MCC {mcc} / MNC {mnc}"

        # Si el IMEI o Modelo fallaron en sus comandos directos, los extraemos de DEVCONINFO
        if dev_info and "DEVCONINFO" in dev_info:
            if "No disponible" in model or "NONE" in model.upper():
                m_model = re.search(r'MN\(([^)]+)\)', dev_info)
                if m_model:
                    model = m_model.group(1)
            
            if "No disponible" in imei or "NONE" in imei.upper():
                m_imei = re.search(r'IMEI\(([^)]+)\)', dev_info)
                if m_imei:
                    imei = m_imei.group(1)
        
        # Limpieza final
        model = model.replace("\n", "").replace("\r", "").strip()
        imei = imei.replace("\n", "").replace("\r", "").strip()
        
        # ====================================================

        # Si logramos leer alguno de los tres pilares (modelo, imei o sw_ver), éxito
        if model != "No disponible" or imei != "NONE" or results["sw_ver"][0]:
            msg = (
                f"=== INFORMACIÓN DEL DISPOSITIVO ===\n"
                f"📱 Modelo: {model}\n"
                f"🔑 IMEI: {imei}\n"
                f"💿 Software Ver: {sw_ver}\n"
                f"📡 IMSI (SIM): {cimi}\n"
                f"\n⚙️ Configuración (DevInfo):\n{dev_info}"
            )
            return {"status": "success", "message": msg}
            
        return {"status": "error", "message": "El dispositivo no respondió correctamente a la lectura AT."}

    async def _heimdall_detect(self) -> Dict[str, Any]:
        deps = self.cli_runner.check_dependencies()
        if not deps["heimdall"]: return {"status": "error", "message": "Heimdall no instalado (sudo dnf install heimdall)"}
        return {"status": "stream", "message": "Detectando Heimdall...", "generator": self.cli_runner.run_command(["heimdall", "detect"])}

    # ==========================================
    # TEST MODE (*#0*#)
    # ==========================================

    @handle_usb_errors
    async def _enable_test_mode_adb(self) -> Dict[str, Any]:
        port = await self._ensure_modem_port()
        loop = asyncio.get_running_loop()
        success, raw = await loop.run_in_executor(None, self._sync_at_command, port, "AT+KSTRINGB=0,3")
        if success: return {"status": "success", "message": "Inyectado vía MTP. Acepta permisos ADB en la pantalla.", "raw": raw}
        return {"status": "error", "message": "Fallo al habilitar Test Mode.", "raw": raw}

    async def _test_mode_remove_frp(self) -> Dict[str, Any]:
        if not self.cli_runner.check_dependencies()["adb"]: return {"status": "error", "message": "Falta ADB"}
        # Secuencia clásica de bypass FRP por ADB
        cmds = [
            ["adb", "shell", "am", "start", "-n", "com.google.android.gsf.login/"],
            ["adb", "shell", "am", "start", "-n", "com.google.android.setupwizard/.SetupWizardTestActivity"],
            ["adb", "shell", "content", "insert", "--uri", "content://settings/secure", "--bind", "name:s:user_setup_complete", "--bind", "value:s:1"]
        ]
        return {"status": "stream", "message": "Iniciando Bypass FRP...", "generator": self._stream_multiple_commands(cmds)}

    async def _test_mode_factory_reset(self) -> Dict[str, Any]:
        if not self.cli_runner.check_dependencies()["adb"]: return {"status": "error", "message": "Falta ADB"}
        cmds = [["adb", "shell", "am", "broadcast", "-a", "android.intent.action.MASTER_CLEAR"]]
        return {"status": "stream", "message": "Iniciando Factory Reset por ADB...", "generator": self._stream_multiple_commands(cmds)}

    async def _test_mode_disable_knox(self) -> Dict[str, Any]:
        if not self.cli_runner.check_dependencies()["adb"]: return {"status": "error", "message": "Falta ADB"}
        cmds = [
            ["adb", "shell", "pm", "uninstall", "-k", "--user", "0", "com.sec.enterprise.knox.attestation"],
            ["adb", "shell", "pm", "uninstall", "-k", "--user", "0", "com.samsung.klmsagent"]
        ]
        return {"status": "stream", "message": "Deshabilitando Knox...", "generator": self._stream_multiple_commands(cmds)}

    # ==========================================
    # MTP MODE
    # ==========================================

    @handle_usb_errors
    async def _mtp_factory_reset(self) -> Dict[str, Any]:
        port = await self._ensure_modem_port()
        loop = asyncio.get_running_loop()
        success, raw = await loop.run_in_executor(None, self._sync_at_command, port, "AT+FACTORYRESET")
        return {"status": "success" if success else "error", "message": f"Respuesta: {raw}"}

    @handle_usb_errors
    async def _mtp_enable_vzw_secret_code(self) -> Dict[str, Any]:
        port = await self._ensure_modem_port()
        loop = asyncio.get_running_loop()
        success, raw = await loop.run_in_executor(None, self._sync_at_command, port, "AT+SYSSCOPE=1,1")
        return {"status": "success" if success else "error", "message": f"Respuesta Verizon: {raw}"}

    @handle_usb_errors
    async def _mtp_reboot_download_mode(self) -> Dict[str, Any]:
        port = await self._ensure_modem_port()
        loop = asyncio.get_running_loop()
        # En Samsung, el comando AT+FUS? inicia la sesión Firmware Update (Download Mode)
        success, raw = await loop.run_in_executor(None, self._sync_at_command, port, "AT+FUS?")
        if success:
            return {"status": "success", "message": "Reiniciando a Download Mode (MTP/AT)...", "raw": raw}
        
        # Fallback 2: AT+KEYD
        success, raw = await loop.run_in_executor(None, self._sync_at_command, port, "AT+KEYD")
        return {"status": "success" if success else "error", "message": "Reiniciando a Download Mode (MTP/AT)...", "raw": raw}

    # ==========================================
    # DOWNLOAD MODE (ODIN)
    # ==========================================

    async def _download_exit_mode(self) -> Dict[str, Any]:
        if not self.cli_runner.check_dependencies()["heimdall"]: return {"status": "error", "message": "Falta Heimdall"}
        return {"status": "stream", "message": "Forzando reinicio...", "generator": self.cli_runner.run_command(["heimdall", "print-pit"])}

    async def _download_soft_brick_fix(self) -> Dict[str, Any]:
        if not self.cli_runner.check_dependencies()["heimdall"]: return {"status": "error", "message": "Falta Heimdall"}
        return {"status": "stream", "message": "Limpiando buffers...", "generator": self.cli_runner.run_command(["heimdall", "close-pc-screen"])}

    async def _download_flasher_heimdall(self, **kwargs) -> Dict[str, Any]:
        if not self.cli_runner.check_dependencies()["heimdall"]: 
            return {"status": "error", "message": "Falta Heimdall. Instálalo con: sudo dnf install heimdall"}
            
        firmware_dir = kwargs.get("firmware_dir")
        if not firmware_dir:
            return {"status": "request_dir", "title": "Selecciona la carpeta con el Firmware (Archivos AP, BL, CP, CSC en .tar.md5 o extraídos)"}
            
        import os
        import random
        import tarfile
        import tempfile
        import shutil

        async def flasher_real_process() -> AsyncGenerator[Tuple[str, int], None]:
            yield ("[+] Iniciando proceso Real de Flasheo Heimdall...", 2)
            
            # 1. Identificar archivos provistos
            files_in_dir = os.listdir(firmware_dir)
            tar_files = [f for f in files_in_dir if f.upper().startswith(('AP_', 'BL_', 'CP_', 'CSC_')) and (f.endswith('.tar') or f.endswith('.md5'))]
            
            # Crear directorio temporal para extracción si hay archivos empaquetados
            temp_dir = tempfile.mkdtemp(prefix="itzli_fw_")
            try:
                if tar_files:
                    yield (f"[+] Detectados {len(tar_files)} archivos empaquetados. Extrayendo componentes...", 5)
                    progress_step = 20 / len(tar_files)
                    current_prog = 5
                    
                    for t_file in tar_files:
                        yield (f"[i] Descomprimiendo: {t_file}", int(current_prog))
                        tar_path = os.path.join(firmware_dir, t_file)
                        
                        # Ejecutar extracción bloqueante en un hilo de forma segura (previniendo Tar Slip)
                        loop = asyncio.get_running_loop()
                        def extract():
                            with tarfile.open(tar_path, 'r') as tar:
                                for member in tar.getmembers():
                                    # Prevención de ataques de inyección de ruta (Tar/Zip Slip)
                                    if member.name.startswith('/') or '..' in member.name:
                                        continue
                                    tar.extract(member, path=temp_dir, set_attrs=False)
                        await loop.run_in_executor(None, extract)
                        
                        current_prog += progress_step
                else:
                    # Si ya venían extraídos, solo usamos la carpeta seleccionada
                    yield ("[+] No se detectaron .tar.md5, asumiendo firmware ya extraído.", 20)
                    temp_dir = firmware_dir

                # 2. Mapear archivos extraídos a particiones de Heimdall
                # Mapa de (archivo_esperado) -> (Particion_Heimdall)
                partition_map = {
                    "boot.img": "BOOT", "boot.img.lz4": "BOOT",
                    "recovery.img": "RECOVERY", "recovery.img.lz4": "RECOVERY",
                    "system.img": "SYSTEM", "system.img.ext4": "SYSTEM", "system.img.lz4": "SYSTEM",
                    "vendor.img": "VENDOR", "vendor.img.ext4": "VENDOR", "vendor.img.lz4": "VENDOR",
                    "modem.bin": "RADIO", "modem.bin.lz4": "RADIO",
                    "cache.img": "CACHE", "cache.img.ext4": "CACHE", "cache.img.lz4": "CACHE",
                    "userdata.img": "USERDATA", "userdata.img.ext4": "USERDATA", "userdata.img.lz4": "USERDATA",
                    "sboot.bin": "BOOTLOADER", "sboot.bin.lz4": "BOOTLOADER",
                    "param.bin": "PARAM", "param.bin.lz4": "PARAM",
                    "cm.bin": "CM", "cm.bin.lz4": "CM"
                }
                
                cmd_args = ["heimdall", "flash"]
                files_to_flash = os.listdir(temp_dir)
                found_partitions = 0
                
                yield ("[⚙️] Mapeando archivos a particiones Heimdall...", 25)
                
                for f in files_to_flash:
                    for key, partition in partition_map.items():
                        if f.lower() == key.lower():
                            file_path = os.path.join(temp_dir, f)
                            cmd_args.extend([f"--{partition}", file_path])
                            found_partitions += 1
                            yield (f"  -> Asignado {f} a --{partition}", 25 + found_partitions)
                            break
                            
                if found_partitions == 0:
                    raise RuntimeError("No se encontraron archivos .img o .bin válidos para flashear.")
                    
                # 3. Empujar comando Real a Heimdall
                yield (f"\n[⚡] Iniciando comando Heimdall con {found_partitions} particiones...", 35)
                
                # Ejecuta heimdall (si no hay dispositivo colgará/fallará, pero es el comando real)
                async for line in self.cli_runner.run_command(cmd_args):
                    clean_line = line.strip()
                    if not clean_line:
                        continue
                        
                    # Parsear el progreso de Heimdall para la GUI (Ej: "Uploading BOOT... 100%")
                    if "Uploading" in clean_line and "%" in clean_line:
                        # Extraer un porcentaje visual un poco burdo y trasladarlo a 35-95%
                        yield (clean_line, 65)
                    else:
                        yield (clean_line, 50)
                        
                yield ("\n[🎉 ÉXITO] ¡Flasheo Heimdall Completado Seguro y Satisfactoriamente!", 100)
                
            except Exception as e:
                yield (f"\n[🚨 ERROR] Falló el proceso real: {str(e)}", -1)
                yield ("[!] OPERACIÓN ABORTADA.", -1)
                raise e
            finally:
                # Limpiar siempre el temporal
                if temp_dir != firmware_dir and os.path.exists(temp_dir):
                    yield ("[i] Limpiando archivos temporales de extracción...", -1) # No alterar barra
                    shutil.rmtree(temp_dir)

        return {
            "status": "stream",
            "message": "Iniciando proceso Real Heimdall Flasher",
            "generator": flasher_real_process()
        }

    # ==========================================
    # ADB MODE
    # ==========================================

    async def _adb_change_csc(self) -> Dict[str, Any]:
        if not self.cli_runner.check_dependencies()["adb"]: return {"status": "error", "message": "Falta ADB"}
        cmds = [["adb", "shell", "am", "start", "-n", "com.samsung.android.app.omcagent/.network.app.PreconfigActivity"]]
        return {"status": "stream", "message": "Abriendo menú CSC en el dispositivo...", "generator": self._stream_multiple_commands(cmds)}

    async def _adb_remove_samsung_account(self) -> Dict[str, Any]:
        if not self.cli_runner.check_dependencies()["adb"]: return {"status": "error", "message": "Falta ADB"}
        cmds = [["adb", "shell", "pm", "uninstall", "-k", "--user", "0", "com.osp.app.signin"]]
        return {"status": "stream", "message": "Removiendo Samsung Account...", "generator": self._stream_multiple_commands(cmds)}

    async def _adb_reboot_download_mode(self) -> Dict[str, Any]:
        if not self.cli_runner.check_dependencies()["adb"]: return {"status": "error", "message": "Falta ADB"}
        cmds = [["adb", "reboot", "download"]]
        return {"status": "stream", "message": "Reiniciando a Download Mode (ADB)...", "generator": self._stream_multiple_commands(cmds)}
