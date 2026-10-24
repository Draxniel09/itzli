import pytest
import asyncio
from itzli.adapters.cli_runner import CLIRunner

@pytest.mark.asyncio
async def test_cli_runner_success():
    runner = CLIRunner()
    lines = []
    
    # Corremos un echo básico
    async for line in runner.run_command(['echo', 'hello world']):
        lines.append(line.strip())
        
    assert "hello world" in lines

@pytest.mark.asyncio
async def test_cli_runner_failure():
    runner = CLIRunner()
    lines = []
    
    # Corremos un comando que sabemos que falla
    async for line in runner.run_command(['ls', '/non_existent_folder_xyz_123']):
        lines.append(line)
        
    # Verificamos que el comando emitió texto en stderr
    assert any("No such file" in line or "No existe" in line or "No such directory" in line for line in lines)
