import json
from pathlib import Path

def validate_script_folder(folder: str) -> tuple[bool, list[str]]:
    errs: list[str] = []
    src = Path(folder).expanduser().resolve()

    if not src.exists() or not src.is_dir():
        return False, [f"Folder not found: {src}"]
    
    manifest = src / "script.json"
    if not manifest.exists():
        return False, [f"Missing script.json in {src}"]
    
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"Invalid JSON in script.json: {e}"]
    

    # Required fields
    for k in ["id", "entrypoint"]:
        if k not in data or not str(data[k]).strip():
            errs.append(f"Missing required field: {k}")

    script_id = data.get("id")
    if script_id and src.name != script_id:
        errs.append(f"Folder name '{src.name}' should match id 'script_id' (recommended)")

    entry = data.get("entrypoint", "")
    if ":" not in entry:
        errs.append("entrypoint must look like 'module.path:func'")

    # Schedule validation
    sched = data.get("schedule", {})
    if sched:
        stype = sched.get("type")
        if stype not in ("interval", "time", "event", "file_watch", "on_failure"):
            errs.append(f"Unknown schedule type: {stype}")

    # Recommended files
    if not (src / "__init__.py").exists():
        errs.append("Missing __init__.py (recommended; required for import-style entrypoints)")

    # Entrypoint module sanity
    # If entrypoint references control_core.scripts.<id>..., require main.py exists
    if script_id and f"control_core.scripts.{script_id}." in entry:
        if not (src / "main.py").exists():
            errs.append("Missing main.py")
    
    return (len(errs) == 0), errs

def validate_times(t: str) -> bool:
    if ":" not in t:
        return False
    a = t.split(":")
    if len(a) != 2:
        return False
    try:
        hh = int(a[0]); mm = int(a[1])
        return 0 <= hh <= 23 and 0 <= mm <= 59
    except Exception:
        return False

def validate_dom(dom: int, m: int) -> bool:
    try:
        day = int(dom)
        month = int(m)
        if not (1 <= month <= 12):
            return False
        if month in (1, 3, 5, 7, 8, 10, 12):
            return 1 <= day <= 31
        elif month in (4, 6, 9, 11):
            return 1 <= day <= 30
        elif month == 2:
            return 1 <= day <= 29
        return False
    except Exception:
        return False