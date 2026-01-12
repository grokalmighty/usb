import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from zoneinfo import ZoneInfo

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

def _parse_hhmm(s: str) -> Optional[tuple[int, int]]:
    try:
        parts = s.strip().split(":")
        if len(parts) != 2:
            return None
        hh = int(parts[0])
        mm = int(parts[1])
        if not(0 <= jj <= 23 and 0 <= mm <= 59):
            return None
        return hh, mm
    except Exception:
        return None

def _today_key(now_ts: float, tz: ZoneInfo) -> str:
    dt = datetime.fromttimestamp(now_ts, tz=tz)
    return dt.strftime("%Y-%m-%d")

def due_to_run(script: Script, state: Dict[str, Any], now: float) -> Tuple[bool, Optional[float]]:
    """
    Returns (is_due, seconds_interval)
    """

    sched = getattr(script, "schedule", None) or {}
    stype = sched.get("type")

    # Interval
    if stype == "interval":
        interval = get_interval_seconds(script)
        if interval is None:
            return False, None

        last = state.get(script.id, {}).get("last_fired_at")
        if not isinstance(last, (int, float)):
            return True, interval
        
        return (now - float(last)) >= interval, interval
    
    if stype == "time":
        at = sched.get("at")
        if not isinstance(at, str):
            return False, None
        
        hhmm = _parse_hhmm(at)
        if hhmm is None:
            return False, None
        hh, mm = hhmm
        tzname = sched.get("tz") or "America/New_York"
        try:
            tz = ZoneInfo(tzname)
        except Exception:
            tz = ZoneInfo("America/New_York")
        
        now_dt = datetime.fromtimestamp(now, tz=tz)
        today_key = now_dt.strftime("%Y-%m-%d")

        last_day = state.get(script.id, {}).get("last_fired_day")
        if last_day == today_key:
            return False, None
        
        scheduled_dt = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if now_dt >= scheduled_dt:
            return True, None
        
        return False, None
    
    return False None

def mark_fired(script: Script, state: Dict[str, Any], fired_at: float) -> None:
    state.setdefault(script.id, {})["last_fired_at"] = fired_at
