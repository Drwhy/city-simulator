from __future__ import annotations
import json
from pathlib import Path
from typing import Any
SAVE_VERSION = 14

def validate_save_version(state: dict[str, Any]) -> None:
    if int(state.get("version",0)) != SAVE_VERSION: raise ValueError("Version de sauvegarde non prise en charge.")

def write_snapshot(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    temporary.replace(path)
    return path

def read_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists(): raise FileNotFoundError("Aucune sauvegarde n'est disponible.")
    payload=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload,dict): raise TypeError("La sauvegarde doit être un objet JSON.")
    return payload
