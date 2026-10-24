import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from itzli.adapters.cli_runner import CLIRunner

@pytest.mark.asyncio
async def test_deberia_manejar_output_vacio_correctamente_edge_case():
    runner = CLIRunner()
    
    # Aislar: Mockeamos create_subprocess_exec profundo de asyncio usando AsyncMock para compatibilidad con Py3.14
    mock_process = MagicMock()
    mock_process.returncode = 0
    # Simulamos un stdout que devuelve EOF (b'') inmediatamente
    mock_process.stdout.readline = AsyncMock(return_value=b'') 
    mock_process.wait = AsyncMock(return_value=0)

    with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
        lineas = []
        async for linea in runner.run_command(["comando_silencioso"]):
            lineas.append(linea)
            
        # Edge case: No debe crashear, simplemente devuelve una lista vacía
        assert len(lineas) == 0