#!/usr/bin/env python3
"""Hook PostToolUse: bitácora local de cada herramienta que usa el agente.

Escribe una línea JSON por invocación en ``.kiro-audit/tool-calls.jsonl``. La
auditoría nunca debe interrumpir al agente, así que cualquier error se ignora.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    """Agrega una entrada de auditoría con marca de tiempo, sesión y herramienta."""
    try:
        event = json.loads(sys.stdin.read() or "{}")
        audit_dir = Path(".kiro-audit")
        audit_dir.mkdir(exist_ok=True)
        entry = {
            "at": datetime.now(timezone.utc).isoformat(),
            "session": event.get("session_id"),
            "tool": event.get("tool_name"),
            "input": event.get("tool_input"),
        }
        with (audit_dir / "tool-calls.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(f"{json.dumps(entry, ensure_ascii=False)}\n")
    except Exception:  # noqa: BLE001 - la auditoría nunca interrumpe al agente.
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
