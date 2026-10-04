#!/usr/bin/env python3
"""Hook Stop: quality gate del stack Python.

Cuando el agente termina su turno y hubo cambios en ``src/`` o ``tests/``, corre
el linter, el chequeo de formato y las pruebas. Si algo falla, emite una
"block decision" por stdout para que el agente siga corrigiendo en vez de
terminar con el código roto.
"""

from __future__ import annotations

import json
import subprocess
import sys


def changed() -> bool:
    """Indica si hay cambios sin commitear en ``src/`` o ``tests/``."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", "src", "tests"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return bool(result.stdout.strip())


def run_step(cmd: list[str]) -> tuple[int, str]:
    """Ejecuta un paso del gate y devuelve (código de salida, salida combinada)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 127, f"No se encontró el ejecutable: {cmd[0]}"
    combined = f"{result.stdout or ''}{result.stderr or ''}".strip()
    tail = "\n".join(combined.splitlines()[-25:])
    return result.returncode, tail


def block(cmd: list[str], output: str) -> None:
    """Imprime la decisión de bloqueo en el formato que espera el hook Stop."""
    reason = (
        f'Quality gate del equipo falló en "{" ".join(cmd)}". '
        "Corrige el problema antes de terminar (no desactives las pruebas ni el hook):\n"
        f"{output}"
    )
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))


def main() -> int:
    """Corre ruff, black --check y pytest si hubo cambios relevantes."""
    if not changed():
        return 0
    steps = [
        ["ruff", "check", "."],
        ["black", "--check", "."],
        ["pytest", "-q"],
    ]
    for cmd in steps:
        code, output = run_step(cmd)
        if code != 0:
            block(cmd, output)
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
