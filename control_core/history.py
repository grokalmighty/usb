import json
import time
from collections import deque
from pathlib import Path
from typing import List, Optional

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"

def _safe_load(line: str) -> Optional[dict]:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None

def get_history(script_id: str, n: int = 20) -> List[dict]:
    """
    Return last n events for a given script_id.
    """

    if not LOG_PATH.exists():
        return []
    
    buf = deque(maxlen=n)
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            e = _safe_load(line)
            if not e:
                continue

            if e.get("script_id") == script_id:
                buf.append(e)

    return list(buf)

def formal_event(e: dict) -> str:
    ended = e.get("ended_at") or e.get("started_at")
    t = time.strftime("%H:%M:%S", time.localtime(ended)) if isinstance(ended, (int, float)) else "unknown"

    ok = e.get("ok")
    run_id = e.get("run_id", "")
    started = e.get("started_at")
    ended2 = e.get("ended_at")
    ms = ""

    if isinstance(started, (int, float)) and isinstance(ended2, (int, float)) and ended2 >= started:
        ms = f"{(ended2 - started) * 1000.0:.1f}ms"

    # Show a short error if any
    err = (e.get("error") or e.get("stderr") or "").strip()
    err_line = ""
    if err:
        lines = [ln.strip() for ln in err.splitlines() if ln.strip()]
        err_line = lines[-1] if lines else ""
    
    tail = f" {err_line}" if err_line else ""
    return f"{t} ok={ok} {ms:>10} run_id={run_id}{tail}"