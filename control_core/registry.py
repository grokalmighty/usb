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
            seconds = float(sched.get("seconds", 0))
        except Exception:
            seconds = 0
        if seconds <= 0:
            return {}
        return {"type": "interval", "seconds": seconds}

    if stype == "time":
        at = sched.get("at")
        
        if isinstance(at, str):
            times = [at]
        
        elif isinstance(at, list):
            times = [x for x in at if isinstance(x, str)]
        
        else:
            return {}
        
        norm_times: list[str] = []
        for t in times:
            if _valid_hhmm(t):
                hh, mm = t.strip().split(":")
                norm_times.append(f"{int(hh):02d}:{int(mm):02d}")

        if not norm_times:
            return {}
        
        tz = sched.get("tz") or "America/New_York"

        # Days of the week
        days = sched.get("days")
        if isinstance(days, list) and days:
            try:
                days = [int(d) for d in days]
                days = [d for d in days if 1 <= d <= 7]
            except Exception:
                days = None
        else:
            days = None
        
        # Month
        months = sched.get("months")
        if isinstance(months, list) and months:
            try:
                months = [int(m) for m in months]
                months = [m for m in months if 1 <= m <= 12]
            except Exception:
                months = None
        else:
            months = None

        # Days of the month
        dom = sched.get("dom")
        if (isinstance(dom, list) and dom) and months:
            try:
                dom = [int(d) for d in dom]
                dom = [d for d in dom if 1 <= d <= 31]
            except Exception:
                dom = None
        else:
            dom = None

        out = {"type": "time", "at": norm_times if len(norm_times) > 1 else norm_times[0], "tz": tz}
        if days:
            out["days"] = days
        if months:
            out["months"] = months
        if dom:
            out["dom"] = dom
        return out 
    
    if stype == "event":
        raw_events = sched.get("events")

        if isinstance(raw_events, list):
            events = [e.strip() for e in raw_events if isinstance(e, str) and e.strip()]
        else:
            one = sched.get("event")
            events = [one.strip()] if isinstance(one, str) and one.strip() else []

        allowed = {"idle", "app_open", "app_close", "network_up", "network_down"}
        events = [e for e in events if e in allowed]
        events = sorted(set(events))
        if not events:
            return {}
        
        out = {"type": "event", "events": events}

        # Idle seconds
        if "idle" in events:
            try:
                seconds = float(sched.get("seconds", 0))
            except Exception:
                seconds = 0
            if seconds <= 0:
                return {}
            out["seconds"] = seconds 

        # Apps list
        if any(e in ("app_open", "app_close") for e in events):
            apps = sched.get("apps")
            if isinstance(apps, str):
                apps_list = [a.strip() for a in apps.split(",") if a.strip()]
            elif isinstance(apps, list):
                apps_list = [a.strip() for a in apps if isinstance(a, str) and a.strip()]
            else:
                apps_list = []
            if apps_list:
                out["apps"] = apps_list
        
        return out
    
    if stype == "file_watch":
        p = sched.get("path")
        if not p:
            return {}
        try:
            poll_seconds = float(sched.get("poll_seconds", 1.0) or 1.0)
        except Exception:
            poll_seconds = 1.0
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
            schedule=_normalize_schedule(data.get("schedule", {})),
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