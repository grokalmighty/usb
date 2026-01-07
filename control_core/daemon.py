import time
from typing import Dict, Set

from .registry import discover_scripts, Script
from .runner import run_script

def _initial_next_due(scripts: Dict[str, Script]) -> Dict[str, float]:
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
    next_due = _initial_next_due(scripts)
    running: Set[str] = set()

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
                if script_id in running:
                    next_due[script_id] = now + 1.0
                    continue
                    
                running.add(script_id)
                try:
                    ok, run_id = run_script(s, timeout_seconds=20.0)
                    print(f"[{time.strftime('%H:%M:%S')}] ran {script_id} ok={ok} run_id{run_id}")
                    next_due[script_id] = now + seconds
                finally:
                    running.remove(script_id)
        
        time.sleep(poll_interval)

if __name__ == "__main__":
    main()