"""Pruebas de arquitectura (RNF-ARQ-04): ejecuta los contratos de .importlinter."""

import os
import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]


def test_import_contracts_hold() -> None:
    env = {**os.environ, "PYTHONPATH": str(API_DIR / "src")}
    lint = Path(sys.executable).with_name("lint-imports")
    result = subprocess.run(
        [str(lint)], cwd=API_DIR, env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
