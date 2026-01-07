import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"

@dataclass(frozen=True)
class Script:
    id: str
    name: str
    enabled: bool
    entrypoint: str
    schedule: dict
    path: Path

def discover_scripts() -> Dict[str, Script]:
    scripts: Dict[str, Script] = {}

    for script_dir in SCRIPTS_DIR.iterdir():
        if not script_dir.is_dir():
            continue

        manifest = script_dir / "script.json"
        if not manifest.exists():
            continue

        data = json.loads(manifest.read_text())

        s = Script(
            id=data["id"],
            name=data.get("name", data["id"]),
            enabled=bool(data.get("enabled", False)),
            entrypoint=data["entrypoint"],
            schedule=data.get("schedule", {}),
            path=script_dir,
        )
        scripts[s.id] = s
    
    return scripts

def list_scripts() -> List[Script]:
    return list(discover_scripts().values())