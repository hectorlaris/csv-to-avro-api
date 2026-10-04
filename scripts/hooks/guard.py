#!/usr/bin/env python3
"""Hook PreToolUse: barrera de gobernanza para el proyecto.

Lee el evento del hook por stdin (JSON) y bloquea (exit 2) dos clases de acción:

1. Comandos de shell destructivos o peligrosos (force push, push a main, deploys
   manuales, borrados recursivos, ``curl | sh``, etc.).
2. Escrituras de archivos sensibles (``.env``, llaves privadas) o con contenido
   que parezca una credencial.

Para cualquier otra invocación, termina con exit 0 y no interfiere. El mensaje de
bloqueo se envía por stderr, como espera un hook PreToolUse.
"""

from __future__ import annotations

import json
import re
import sys

# --- Comandos de shell bloqueados -------------------------------------------

DANGEROUS_COMMAND_PATTERNS: list[tuple[str, str]] = [
    (r"git\s+push\s+.*--force", "git push --force está bloqueado."),
    (
        r"git\s+push\s+.*\bforce-with-lease",
        "git push --force-with-lease está bloqueado.",
    ),
    (
        r"git\s+push\s+\S+\s+(main|master)\b",
        "No se permite push directo a main/master.",
    ),
    (r"git\s+reset\s+--hard", "git reset --hard está bloqueado."),
    (r"git\s+clean\s+-\w*f", "git clean -f está bloqueado."),
    (r"git\s+branch\s+-D", "Borrado forzado de ramas (git branch -D) bloqueado."),
    (r"\brm\s+-\w*r\w*f|\brm\s+-\w*f\w*r", "rm -rf está bloqueado."),
    (
        r"Remove-Item\s+.*-Recurse.*-Force",
        "Remove-Item -Recurse -Force está bloqueado.",
    ),
    (
        r"\bsam\s+deploy\b",
        "El deploy manual (sam deploy) debe hacerse por el pipeline.",
    ),
    (
        r"\baws\s+cloudformation\s+(delete|deploy)",
        "Operaciones manuales de CloudFormation bloqueadas.",
    ),
    (
        r"curl\s+.*\|\s*(sh|bash|pwsh|python)",
        "Patrón 'curl | shell' bloqueado (ejecución remota).",
    ),
    (
        r"Invoke-WebRequest\s+.*\|\s*(iex|Invoke-Expression)",
        "Patrón 'IWR | iex' bloqueado (ejecución remota).",
    ),
]

# --- Archivos y contenido sensibles -----------------------------------------

SENSITIVE_PATH_PATTERNS: list[str] = [
    r"(^|/|\\)\.env($|\.|/)",
    r"\.pem$",
    r"\.key$",
    r"(^|/|\\)id_rsa($|\.)",
    r"(^|/|\\)credentials($|\.)",
    r"\.pfx$",
    r"\.p12$",
]

SECRET_CONTENT_PATTERNS: list[str] = [
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"AKIA[0-9A-Z]{16}",  # AWS access key id
    r"aws_secret_access_key\s*=",
    r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*['\"][^'\"]{6,}",
    r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S{6,}",
]

SHELL_TOOL_HINTS = ("shell", "bash", "pwsh", "command", "process")
WRITE_TOOL_HINTS = ("write", "append", "replace", "edit")


def deny(reason: str) -> int:
    """Escribe el motivo en stderr y devuelve el código de bloqueo (2)."""
    sys.stderr.write(f"[governance-guards] {reason}")
    return 2


def extract_command(tool_input: dict) -> str:
    """Reúne los campos del input que puedan contener un comando de shell."""
    parts: list[str] = []
    for key in ("command", "cmd", "script", "args"):
        value = tool_input.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
    return " ".join(parts)


def check_shell(tool_input: dict) -> int:
    """Bloquea comandos de shell peligrosos."""
    command = extract_command(tool_input)
    for pattern, reason in DANGEROUS_COMMAND_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return deny(reason)
    return 0


def check_write(tool_input: dict) -> int:
    """Bloquea escrituras a rutas sensibles o con contenido que parezca secreto."""
    path = ""
    for key in ("path", "file_path", "filePath", "targetFile"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            path = value
            break
    for pattern in SENSITIVE_PATH_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return deny(f"Escritura bloqueada en archivo sensible: {path}")

    content = ""
    for key in ("text", "content", "newStr", "new_str"):
        value = tool_input.get(key)
        if isinstance(value, str):
            content += value
    for pattern in SECRET_CONTENT_PATTERNS:
        if re.search(pattern, content):
            return deny("El contenido parece incluir una credencial o llave privada.")
    return 0


def main() -> int:
    """Enruta el evento al chequeo correcto según el tipo de herramienta."""
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError):
        return 0  # Ante un evento ilegible, no interrumpimos al agente.

    tool_name = str(event.get("tool_name", "")).lower()
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    if any(hint in tool_name for hint in SHELL_TOOL_HINTS):
        return check_shell(tool_input)
    if any(hint in tool_name for hint in WRITE_TOOL_HINTS):
        return check_write(tool_input)
    return 0


if __name__ == "__main__":
    sys.exit(main())
