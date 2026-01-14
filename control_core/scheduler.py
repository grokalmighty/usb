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
        if not(0 <= hh <= 23 and 0 <= mm <= 59):
            return None
        return hh, mm
    except Exception:
        return None

def _today_key(now_ts: float, tz: ZoneInfo) -> str:
    dt = datetime.fromtimestamp(now_ts, tz=tz)
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
        tzname = sched.get("tz") or "America/New_York"
        try:
            tz = ZoneInfo(tzname)
        except Exception:
            tz = ZoneInfo("America/New_York")
        
        now_dt = datetime.fromtimestamp(now, tz=tz)
        today_key = now_dt.strftime("%Y-%m-%d")

        # Day of week
        dow = sched.get("days")
        if isinstance(dow, list) and dow:
            try:
                allowed = {int(d) for d in dow}
                if now_dt.isoweekday() not in allowed:
                    return False, None
            except Exception: 
                return False, None
        
        # Month
        months = sched.get("months")
        if isinstance(months, list) and months:
            try:
                allowed_months = {int(m) for m in months}
                if now_dt.month not in allowed_months:
                    return False, None
            except Exception:
                return False, None
        
        # Day of month
        dom = sched.get("dom")
        if isinstance(dom, list) and dom:
            try:
                allowed_dom = {int(d) for d in dom}
                if now_dt.day not in allowed_dom:
                    return False, None
            except Exception:
                return False, None

        # Normalize 
        times: list[str]
        if isinstance(at, str):
            times = [at]
        elif isinstance(at, list):
            times = [x for x in at if isinstance(x, str)]
        else:
            return False, None
        
        # Parse valid times
        parsed: list[tuple[int, int, str]] = []
        for t in times:
            hhmm = _parse_hhmm(t)
            if hhmm is None:
                continue
            hh, mm = hhmm
            parsed.append((hh, mm, f"{hh:02d}:{mm:02d}"))
        
        if not parsed:
            return False, None
        
        fired = state.get(script.id, {}).get("fired_times")
        fired_set = set(fired) if isinstance(fired, list) else set()

        parsed.sort()
        for hh, mm, key in parsed:
            scheduled_dt = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if now_dt >= scheduled_dt and key not in fired_set:
                state.setdefault(script.id, {})["_pending_time_key"] = key
                state.setdefault(script.id, {})["_pending_day"] = today_key
                return True, None
            
        return False, None

    return False, None

def mark_fired(script: Script, state: Dict[str, Any], fired_at: float) -> None:
    sched = getattr(script, "schedule", None) or {}
    stype = sched.get("type")

    if stype == "interval":
        state.setdefault(script.id, {})["last_fired_at"] = fired_at
        return
    
    if stype == "time":
        tzname = sched.get("tz") or "America/New_York"
        try:
            tz = ZoneInfo(tzname)
        except Exception:
            tz = ZoneInfo("America/New_York")
        
        day = _today_key(fired_at, tz)

        entry = state.setdefault(script.id, {})

        if entry.get("last_fired_day") != day:
            entry["last_fired_day"] = day
            entry["fired_times"] = []

        key = entry.pop("_pending_time_key", None)
        entry.pop("_pending_day", None)

        if isinstance(key, str):
            ft = entry.get("fired_times")
            if not isinstance(ft, list):
                ft = []
            if key not in ft:
                ft.append(key)
            entry["fired_times"] = ft
        return 
