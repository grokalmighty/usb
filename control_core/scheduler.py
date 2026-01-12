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

def due_to_run(script: Script, state: Dict[str, Any], now: float) -> Tuple[bool, Optional[float]]:
    """
    Returns (is_due, seconds_interval)
    """

    interval = get_interval_seconds(script)
    if interval is None:
        return False, None
    
    sid = script.id
    last = state.get(sid, {}).get("last_fired_at")

    if not isinstance(last, (int, float)):
        return True, interval
    
    return (now - float(last)) >= interval, interval

def mark_fired(script: Script, state: Dict[str, Any], fired_at: float) -> None:
    state.setdefault(script.id, {})["last_fired_at"] = fired_at
