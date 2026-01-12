import time
from typing import Dict, Any, Optional, Tuple

from .registry import Script

def get_interval_seconds(script: Script) -> Optional[float]:
    sched = getattr(script, "schedule", None) or {}
    if sched.get("type") != "interval":
        return None
    try:
        seconds = float(sched.get("seconds"))
    except Exception:
        return None
    return seconds if seconds > 0 else None