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
        if stype not in ("interval", "file_watch", "on_failure"):
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