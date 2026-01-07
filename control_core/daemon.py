import time
from typing import Dict

from .registry import discover_scripts, Script
from .runner import run_script

def _next_due_times(scripts: Dict[str, Script]) -> Dict[str, float]:
    """
    For each enabled interval script, store the next time it should run
    """

    now = time.time()
    next_due: Dict[str, float] = {}

    for s in scripts.values():
        if not s.enabled:
            continue

        sched = s.schedule or {}
        if sched.get("type") != "interval":
            continue

        seconds = float(sched.get("seconds", 0))
        if seconds <= 0:
            continue

        next_due[s.id] = now

    return next_due