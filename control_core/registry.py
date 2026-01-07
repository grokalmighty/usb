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

def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _save_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def discover_scripts() -> Dict[str, Script]:
    scripts: Dict[str, Script] = {}

    for script_dir in SCRIPTS_DIR.iterdir():
        if not script_dir.is_dir():
            continue

        manifest = script_dir / "script.json"
        if not manifest.exists():
            continue

        data = _load_manifest(manifest)

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

def update_manifest(script_id: str, updater) -> None:
    """
    Updater: function that takes manifest dict and mutates it.
    """

    script_dir = SCRIPTS_DIR / script_id
    manifest_path = script_dir / "script.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"script.json not found for id={script_id}")
    
    data = _load_manifest(manifest_path)
    updater(data)
    _save_manifest(manifest_path, data)