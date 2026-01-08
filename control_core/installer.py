import json
import shutil
from pathlib import Path

from .registry import SCRIPTS_DIR
from .validator import validate_script_folder

def install_script_from_folder(source_folder: str, force: bool = False) -> str:
    src = Path(source_folder).resolve()
    if not src.exists() or not src.is_dir():
        raise FileNotFoundError(f"Source folder not found: {src}")
    
    ok, errs = validate_script_folder(str(src))
    if not ok:
        msg = "Script folder failed validation:\n" + "\n".join(f" - {e}" for e in errs)
        raise ValueError(msg)
    
    manifest = src / "script.json"
    if not manifest.exists():
        raise FileNotFoundError(f"Missing script.json in: {src}")
    
    data = json.loads(manifest.read_text(encoding="utf-8"))
    script_id = data["id"]

    dest = (SCRIPTS_DIR / script_id).resolve()
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        if not force:
            raise FileExistsError(f"Script '{script_id}' already exists. Use --force to overwrite.")
        shutil.rmtree(dest)

    shutil.copytree(src, dest)
    return script_id