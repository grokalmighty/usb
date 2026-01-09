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