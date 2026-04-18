import asyncio
from typing import List, AsyncGenerator

class CLIRunner:
    def __init__(self):
        self.returncode = None
        self.process = None

    async def run_command(self, cmd_list: List[str]) -> AsyncGenerator[str, None]:
        """
        Ejecuta un comando en el sistema y devuelve la salida (stdout + stderr) 
        línea por línea de forma asíncrona, ideal para evitar congelar GUIs.
        """
        self.returncode = None
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd_list,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Leer línea por línea mientras el proceso siga vivo y haya salida
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                yield line.decode('utf-8', errors='replace')

            await self.process.wait()
            self.returncode = self.process.returncode
        except Exception as e:
            self.returncode = -1
            yield f"Error crítico ejecutando comando: {str(e)}"
