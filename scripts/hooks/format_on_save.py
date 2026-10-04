#!/usr/bin/env python3
"""Hook PostFileSave: formatea y linta el archivo Python recién guardado.

Lee el evento del hook por stdin (JSON), extrae la ruta del archivo y aplica
``black`` y ``ruff check --fix`` solo sobre ese archivo. Nunca interrumpe al
agente: cualquier fallo se ignora en silencio.
"""

from __future__ import annotations

import json
import subprocess
import sys


def file_path_from_event() -> str | None:
    """Extrae la ruta del archivo desde el evento JSON recibido por stdin."""
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError):
        return None
    for key in ("file_path", "filePath", "path"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def main() -> int:
    """Aplica black y ruff --fix al archivo guardado, si es un .py."""
    path = file_path_from_event()
    if not path or not path.endswith(".py"):
        return 0
    for cmd in (["black", path], ["ruff", "check", "--fix", path]):
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            # Si falta la herramienta, no interrumpimos el guardado.
            continue
    return 0


if __name__ == "__main__":
    sys.exit(main())
