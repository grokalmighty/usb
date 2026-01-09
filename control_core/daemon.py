import json
import time
import signal
from pathlib import Path
from typing import Dict, Set

from .registry import discover_scripts, Script
from .runner import run_script
from .daemon_state import write_pid, clear_pid

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"

def _abs_path(p: str) -> Path:
    project_root = Path(__file__).resolve().parent.parent
    return (project_root / p).resolve()

def main(poll_interval: float = 0.5) -> None:
    print("Control Core daemon starting...(Ctrl+C to stop)")
    write_pid()

    stop_flag = {"stop": False}

    def _handle_term(signum, frame):
        stop_flag["stop"] = True

    signal.signal(signal.SIGTERM, _handle_term)

    # Interval schedules: due next epoch time
    next_due: Dict[str, float] = {}

    # File watches: last seen mtime
    last_mtime: Dict[str, float] = {}
    running: Set[str] = set()

    # Log-follow state
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch(exist_ok=True)
    log_pos = LOG_PATH.stat().st_size

    while not stop_flag["stop"]:
        now = time.time()

        scripts = discover_scripts()

        # Purge state for disabled/missing scripts
        enabled_ids = {sid for sid, s in scripts.items() if s.enabled}
        for sid in list(next_due.keys()):
            if sid not in enabled_ids:
                next_due.pop(sid, None)
        
        for sid in list(last_mtime.keys()):
            if sid not in enabled_ids:
                last_mtime.pop(sid, None)

        # Initialize state for enabled scripts
        for sid, s in scripts.items():
            if not s.enabled:
                continue
        
            
            sched = s.schedule or {}
            stype = sched.get("type")

            if stype == "interval":
                seconds = float(sched.get("seconds", 0))
                if seconds > 0 and sid not in next_due:
                    next_due[sid] = now 
            
            elif stype == "file_watch":
                p = sched.get("path")
                if not p:
                    continue
                watched = _abs_path(p)
                if sid not in last_mtime:
                    last_mtime[sid] = watched.stat().st_mtime if watched.exists() else 0.0

            elif stype == "on_failure":
                pass 
        
        try:
            size = LOG_PATH.stat().st_size
            if size < log_pos:
                log_pos = 0

        except FileNotFoundError:
            log_pos = 0
            
        # Detect new failures and fire on_failure scripts
        try:
            with LOG_PATH.open("r", encoding="utf-8") as f:
                f.seek(log_pos)
                new = f.read()
                log_pos = f.tell()
        except FileNotFoundError:
            new = ""
        
        if new:
            for line in new.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("ok") is True:
                    continue

                failed_script_id = event.get("script_id")
                if not failed_script_id:
                    continue

                # Prevent recursive failure scripts
                if failed_script_id == sid:
                    continue

                # Find all enabled on_failure scripts and run those matching target
                for sid, s in scripts.items():
                    sched = s.schedule or {}
                    if not s.enabled or sched.get("type") != "on_failure":
                        continue

                    target = sched.get("target", "*")
                    if target != "*" and target != failed_script_id:
                        continue

                    # Prevent alert scripts overlapping with themselves
                    if sid in running:
                        continue

                    running.add(sid)
                    try:
                        ok, run_id = run_script(s, timeout_seconds=20.0, payload={"failed_event": event})
                        print(f"[{time.strftime('%H:%M:%S')}] on_failure -> ran {sid} ok={ok} run_id={run_id} (failure from {failed_script_id})")

                    finally:
                        running.remove(sid)
                
        # Run due scripts
        for sid, s in scripts.items():
            if not s.enabled:
                continue

            sched = s.schedule or {}
            stype = sched.get("type")

            should_run = False 

            if stype == "interval":
                seconds = float(sched.get("seconds", 0))
                if seconds <= 0:
                    continue
                due = next_due.get(sid)
                if due is not None and now >= due:
                    should_run = True
            
            elif stype == "file_watch":
                p = sched.get("path")
                if not p:
                    continue
                watched = _abs_path(p)
                poll_seconds = float(sched.get("poll_seconds", 1.0))

                # Throttle polling per script
                due = next_due.get(sid, 0.0)
                if now < due:
                    continue
                next_due[sid] = now + poll_seconds

                m = watched.stat().st_mtime if watched.exists() else 0.0
                prev = last_mtime.get(sid, 0.0)
                if m != prev:
                    last_mtime[sid] = m
                    should_run = True
            
            else:
                continue
            
            if should_run:
                if sid in running:
                    continue
                running.add(sid)

                try:
                    ok, run_id = run_script(s, timeout_seconds=20.0)
                    print(f"[{time.strftime('%H:%M:%S')}] ran {sid} ok={ok} run_id={run_id}")

                    if stype == "interval":
                        seconds = float(sched.get("seconds", 0))
                        next_due[sid] = now + seconds
                
                finally:
                    running.remove(sid)

        time.sleep(poll_interval)

if __name__ == "__main__":
    try:
        main()
        print("SIGTERM received, shutting down...")
    except KeyboardInterrupt:
        print("\nDaemon stopped.")
    finally:
        clear_pid()