#!/usr/bin/env python3
"""Comprueba que docs/requirements-audit.md cubre todos los IDs de REQUIREMENTS.md.

Uso:
  python scripts/check_requirements.py            # modo auditoría: todo ID con estado + evidencia
  python scripts/check_requirements.py --strict   # modo corrección: además, ningún obligatorio en NO_CUMPLE/PARCIAL
Sale con código 0 si todo está bien.
"""
import re
import sys
from pathlib import Path

REQ = Path("REQUIREMENTS.md")
AUDIT = Path("docs/requirements-audit.md")
ID_RE = re.compile(r"^\|\s*([A-Z]+-\d{2})\s*\|")
VALID = {"CUMPLE", "PARCIAL", "NO_CUMPLE", "MANUAL", "NO_APLICA"}


def ids_in(path):
    return [m.group(1) for line in path.read_text(encoding="utf-8").splitlines()
            if (m := ID_RE.match(line))]


def main():
    strict = "--strict" in sys.argv
    if not AUDIT.exists():
        print(f"FALTA {AUDIT}")
        return 1
    required = ids_in(REQ)
    rows = {}
    for line in AUDIT.read_text(encoding="utf-8").splitlines():
        if m := ID_RE.match(line):
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            rows[m.group(1)] = cols

    problems = []
    for rid in required:
        cols = rows.get(rid)
        if not cols or len(cols) < 3:
            problems.append(f"{rid}: sin fila en la auditoría")
            continue
        status, evidence = cols[1], cols[2]
        if status not in VALID:
            problems.append(f"{rid}: estado inválido '{status}'")
        if status != "NO_APLICA" and len(evidence) < 5:
            problems.append(f"{rid}: sin evidencia")
        if status == "NO_APLICA" and not rid.startswith("OPT-"):
            problems.append(f"{rid}: NO_APLICA solo se permite en opcionales")
        if strict and not rid.startswith("OPT-") and status in {"NO_CUMPLE", "PARCIAL"}:
            problems.append(f"{rid}: {status}")

    counts = {s: sum(1 for r in required if rows.get(r, [None, None])[1] == s) for s in sorted(VALID)}
    print(f"Requisitos: {len(required)} | " + " | ".join(f"{k}: {v}" for k, v in counts.items()))
    for p in problems:
        print("  -", p)
    print("OK" if not problems else f"{len(problems)} problemas")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
