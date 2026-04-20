import asyncio
import shutil
from typing import List, AsyncGenerator, Dict

class CLIRunner:
    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """
        Verifica si los binarios requeridos están instalados en el sistema (en el PATH).
        Esto evita crasheos cuando una herramienta (adb, heimdall, mtk) no existe.
        """
        return {
            "adb": shutil.which("adb") is not None,
            "heimdall": shutil.which("heimdall") is not None,
            "mtk": shutil.which("mtk") is not None
        }

    async def run_command(self, cmd_list: List[str]) -> AsyncGenerator[str, None]:
        """
        Ejecuta un comando en el sistema y devuelve la salida (stdout + stderr) 
        línea por línea de forma asíncrona.
        No usa shell=True por seguridad contra inyección de comandos.
        """
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd_list,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Leer línea por línea mientras el proceso siga vivo y haya salida
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode('utf-8', errors='replace')

            await process.wait()
        except asyncio.CancelledError:
            if process and process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    process.kill()
            raise
        except Exception as e:
            yield f"Error crítico ejecutando comando: {str(e)}"
