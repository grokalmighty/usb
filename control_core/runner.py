import json
import subprocess
import sys
import time
import traceback
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from .registry import Script

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"

def log_event(event: Dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def run_script(script: Script, timeout_seconds: Optional[float] = 30.0, payload: Optional[dict] = None) -> Tuple[bool, str]:
    """
    Run script.entrypoint in a separate Python process.
    Captures stdout/stderr and logs structured results.
    """

    run_id = str(uuid4())
    started = time.time()

    event_base = {
        "run_id": run_id,
        "script_id": script.id,
        "script_name": script.name,
        "started_at": started,
    }

    # Launch: python -c "import module; module.func()"
    payload_json = json.dumps(payload or {}, ensure_ascii=False)

    module_path, func_name = script.entrypoint.split(":")
    code = (
        "import os, json, importlib; "
        f"m=importlib.import_module('{module_path}'); "
        "payload=json.loads(os.environ.get('CONTROL_CORE_PAYLOAD','{}')); "
        f"fn=getattr(m, '{func_name}'); "
        "fn(payload) if fn.__code__.co_argcount >= 1 else fn() "
    )

    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env={**os.environ, "CONTROL_CORE_PAYLOAD": payload_json},
        )
        error = proc.stderr if proc.returncode != 0 else ""
        ended = time.time()

        ok = proc.returncode == 0
        log_event(
            {
                **event_base,
                "ended_at": ended,
                "ok": ok,
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                'error': error,
                "timeout_seconds": timeout_seconds,
            }
        )
        return ok, run_id
    
    except subprocess.TimeoutExpired as e:
        ended = time.time()
        log_event(
            {
                **event_base,
                "ended_at": ended,
                "ok": False,
                "exit_code": None,
                "stdout": e.stdout if isinstance(e.stdout, str) else "",
                "stderr": e.stderr if isinstance(e.stderr, str) else "",
                "timeout": True,
                "timeout_seconds": timeout_seconds,
            }
        )
        return False, run_id
    
    except Exception:
        ended = time.time()
        tb = traceback.format_exc()
        log_event({**event_base, "ended_at": ended, "ok": False, "error": tb})
        return False, run_id