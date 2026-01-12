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

    # Locking
    lock_group: str | None = None
    lock_mode: str = "skip"
    lock_timeout_seconds: float = 0.0

def _valid_hhmm(s: str) -> bool:
    try:
        parts = s.strip().split(":")
        if len(parts) != 2:
            return False
        hh = int(parts[0]); mm = int(parts[1])
        return 0 <= hh <= 23 and 0 <= mm <= 59
    except Exception:
        return False
    
def _normalize_schedule(sched: dict) -> dict:
    if not isinstance(sched, dict):
        return {}
    
    stype = sched.get("type")
    if stype is None:
        return {}
    
    if stype == "interval":
        try:
            aeconds = float(sched.get("seconds", 0))
        except Exception:
            seconds = 0
        if seconds <= 0:
            return {}
        return {"type": "interval", "seconds": seconds}

    if stype == "time":
        at = sched.get("at")
        if not isinstance(at, str) or not _valid_hhmm(at):
            return {}
        tz = sched.get("tz") or "America/New_York"
        return {"type": "time", "at": at, "tz": tz}
    
    if stype == "file_watch":
        p = sched.get("path")
        if not p:
            return {}
        poll_seconds = float(sched.get("poll_seconds", 1.0) or 1.0)
        return {"type": "file_watch", "path": p, "poll_seconds": poll_seconds}
    
    if stype == "on_failure":
        target = sched.get("target", "*")
        return {"type": "on_failure", "target": target}

    return {}

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

        # Backward compatible
        lock_group = data.get("lock_group", data.get("lock"))
        lock_mode = data.get("lock_mode", "skip")
        if lock_mode not in ("skip", "wait"):
            lock_mode = "skip"
        lock_timeout_seconds = float(data.get("lock_timeout_seconds", 0.0) or 0.0)
        if lock_timeout_seconds < 0:
            lock_timeout_seconds = 0.0

        s = Script(
            id=data["id"],
            name=data.get("name", data["id"]),
            enabled=bool(data.get("enabled", False)),
            entrypoint=data["entrypoint"],
            schedule=data.get("schedule", {}),
            path=script_dir,
            lock_group=lock_group,
            lock_mode=lock_mode,
            lock_timeout_seconds=lock_timeout_seconds,
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