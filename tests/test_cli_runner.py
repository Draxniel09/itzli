import pytest
import asyncio
from openunlock.adapters.cli_runner import CLIRunner

@pytest.mark.asyncio
async def test_cli_runner_success():
    runner = CLIRunner()
    lines = []
    
    # Corremos un echo básico
    async for line in runner.run_command(['echo', 'hello world']):
        lines.append(line.strip())
        
    assert runner.returncode == 0
    assert "hello world" in lines

@pytest.mark.asyncio
async def test_cli_runner_failure():
    runner = CLIRunner()
    
    # Corremos un comando que sabemos que falla
    async for _ in runner.run_command(['ls', '/non_existent_folder_xyz_123']):
        pass
        
    assert runner.returncode != 0
