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

def main(poll_interval: float = 0.5) -> None:
    print("Control Core daemon starting...(Ctrl+C to stop)")

    scripts = discover_scripts()
    next_due = _next_due_times(scripts)

    while True:
        now = time.time()

        scripts = discover_scripts()

        for script_id, s in scripts.items():
            sched = s.schedule or {}
            if not s.enabled:
                continue
            if sched.get("type") != "interval":
                continue
            
            seconds = float(sched.get("seconds", 0))
            if seconds <= 0:
                continue

            due = next_due.get(script_id, now)
            if now >= due:
                ok, run_id = run_script(s)
                print(f"[{time.strftime('%H:%M:%S')}] ran {script_id} ok={ok} run_id={run_id}")
                next_due[script_id] = now + seconds
        
        time.sleep(poll_interval)