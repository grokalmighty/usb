import json
import time
import signal
from pathlib import Path
from typing import Dict, Set

from .registry import discover_scripts
from .runner import run_script
from .daemon_state import write_pid, clear_pid
from .scheduler_state import load_state, save_state
from .scheduler import due_to_run, mark_fired
from .events import get_idle_seconds_macos, list_process_names, get_local_ip, match_apps

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"

def _abs_path(p: str) -> Path:
    project_root = Path(__file__).resolve().parent.parent
    return (project_root / p).resolve()

def main(poll_interval: float = 0.5) -> int:
    print("Control Core daemon starting...(Ctrl+C to stop)")
    write_pid()

    stop_flag = {"stop": False}

    def _handle_term(signum, frame):
        stop_flag["stop"] = True

    signal.signal(signal.SIGTERM, _handle_term)
    signal.signal(signal.SIGINT, _handle_term)

    # Persistent scheduler state for interval triggers
    sched_state: Dict[str, dict] = load_state()

    # File watches: last seen mtime
    last_mtime: Dict[str, float] = {}

    # File watch polling throttle
    next_poll: Dict[str, float] = {}
    
    # Prevent re-entrant runs in this process
    running: Set[str] = set()

    # Log-follow state
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch(exist_ok=True)
    log_pos = LOG_PATH.stat().st_size

    try:

        # Event detector state
        last_idle_mode = "active"
        last_proc_names = list_process_names()
        last_ip = get_local_ip()
        last_net_up = last_ip is not None
        last_net_change_ts = 0.0

        while not stop_flag["stop"]:
            now = time.time()
            scripts = discover_scripts()
            events = []

            # Idle detection
            idle_seconds = get_idle_seconds_macos()

            if idle_seconds is not None:
                idle_thresholds = []
                for sid, s in scripts.items():
                    if not s.enabled:
                        continue
                    sched = s.schedule or {}
                    if sched.get("type") == "event" and sched.get("event") == "idle":
                        try:
                            idle_thresholds.append(float(sched.get("seconds", 0)))
                        except Exception:
                            pass
                
                if idle_thresholds:
                    mode = "idle" if idle_seconds >= min(idle_thresholds) else "active"
                    if mode != last_idle_mode:
                        last_idle_mode = mode
                        events.append({"type": "idle_state", "mode": mode, "idle_seconds": idle_seconds})

            # App open/close 
            cur = list_process_names()
            opened = sorted(cur - last_proc_names)
            closed = sorted(last_proc_names - cur)
            last_proc_names = cur
            
            for name in opened:
                events.append({"type": "app_open", "app": name})
            for name in closed:
                events.append({"type": "app_close", "app": name})
            
            # Dispatch
            for ev in events:
                for sid, s in scripts.items():
                    if not s.enabled:
                        continue
                    sched = s.schedule or {}
                    if sched.get("type") != "event":
                        continue

                    want = sched.get("event")
                    if want == "idle":
                        if ev.get("type") != "idle_state" or ev.get("mode") != "idle":
                            continue
                        try:
                            threshold = float(sched.get("seconds", 0))
                        except Exception:
                            continue
                        if float(ev.get("idle_seconds", 0)) < threshold:
                            continue

                    elif want == "app_open":
                        if ev.get("type") != "app_open":
                            continue
                        apps = sched.get("apps")
                        if isinstance(apps, list) and apps:
                            if ev.get("app") not in apps:
                                continue

                    elif want == "app_close":
                        if ev.get("type") != "app_close":
                            continue
                        apps = sched.get("apps")
                        if isinstance(apps, list) and apps:
                            if ev.get("app") not in apps:
                                continue

                    elif want == "network_up":
                        if ev.get("type") != "network_up":
                            continue

                    elif want == "network_down":
                        if ev.get("type") != "network_down":
                            continue
                    
                    else:
                        continue

                    if sid in running:
                        continue
                    running.add(sid)
                    try:
                        ok, run_id = run_script(
                            s,
                            timeout_seconds=20.0,
                            payload={"event": ev, "trigger": "event"},
                        )
                        print(f"[{time.strftime('%H:%M:%S')}] event -> ran {sid} ok={ok} run_id={run_id} (event={want})")
                    finally:
                        running.remove(sid)

            # Network
            ip = get_local_ip()
            net_up = ip is not None
            if net_up != last_net_up:
                if now - last_net_change_ts >= 2.0:
                    last_net_change_ts = now
                    last_net_up = net_up
                    if net_up:
                        events.append({"type": "network_up", "ip": ip})
                    else:
                        events.append({"type": "network_down"})
                        
            # Purge state for disabled/missing scripts
            enabled_ids = {sid for sid, s in scripts.items() if s.enabled}
            for sid in list(last_mtime.keys()):
                if sid not in enabled_ids:
                    last_mtime.pop(sid, None)
            
            for sid in list(next_poll.keys()):
                if sid not in enabled_ids:
                    next_poll.pop(sid, None)
            
            for sid in list(sched_state.keys()):
                if sid not in enabled_ids:
                    sched_state.pop(sid, None)

            try:
                size = LOG_PATH.stat().st_size
                if size < log_pos:
                    log_pos = 0
            except FileNotFoundError:
                log_pos = 0 # 

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

                    # Find all enabled on_failure scripts and run those matching the target
                    for sid, s in scripts.items():
                        sched = s.schedule or {}
                        if not s.enabled or sched.get("type") != "on_failure":
                            continue
                        
                        if failed_script_id == sid:
                            continue 

                        target = sched.get("target", "*")
                        if target != "*" and target != failed_script_id:
                            continue

                        if sid in running:
                            continue

                        running.add(sid)
                        try:
                            ok, run_id = run_script(
                                s,
                                timeout_seconds=20.0,
                                payload={"failed_event": event, "trigger": "on_failure"},
                            )
                            print(
                                f"[{time.strftime('%H:%M:%S')}] on_failure -> ran {sid} ok={ok} run_id={run_id} (failure from {failed_script_id})"
                            )
                        finally:
                            running.remove(sid)

            any_sched_change = False
                    
            # Run due scripts
            for sid, s in scripts.items():
                if not s.enabled:
                    continue

                sched = s.schedule or {}
                stype = sched.get("type")

                if stype in ("interval", "time"):
                    is_due, interval = due_to_run(s, sched_state, now)
                    if not is_due:
                        continue

                    if sid in running:
                        continue

                    mark_fired(s, sched_state, now)
                    any_sched_change = True

                    running.add(sid)
                    try:
                        ok, run_id = run_script(
                            s,
                            timeout_seconds=20.0,
                            payload={"scheduled": True, "trigger": "interval"},
                        )
                        print(f"[{time.strftime('%H:%M:%S')}] ran {sid} ok={ok} run_id={run_id}")
                    finally:
                        running.remove(sid)
                
                elif stype == "file_watch":
                    p = sched.get("path")
                    if not p:
                        continue
                    watched = _abs_path(p)
                    poll_seconds = float(sched.get("poll_seconds", 1.0) or 1.0)

                    # Throttle polling per script
                    due = next_poll.get(sid, 0.0)
                    if now < due:
                        continue
                    next_poll[sid] = now + poll_seconds

                    m = watched.stat().st_mtime if watched.exists() else 0.0
                    prev = last_mtime.get(sid)
                    if prev is None:
                        last_mtime[sid] = m
                        continue
                        
                    if m != prev:
                        last_mtime[sid] = m

                        if sid in running:
                            continue

                        running.add(sid)
                        try:
                            ok, run_id = run_script(
                                s,
                                timeout_seconds=20.0,
                                payload={"trigger": "file_watch", "path": str(watched)},
                            )
                            print(f"[{time.strftime('%H:%M:%S')}] file_watch -> ran {sid} ok={ok} run_id={run_id}")
                        finally:
                            running.remove(sid)
            
                else:
                    continue
                
            if any_sched_change:
                save_state(sched_state)
            
            time.sleep(poll_interval)

        return 0
        
    finally:
        save_state(sched_state)
        clear_pid()

if __name__ == "__main__":
    code = 0
    try:
        code = main()
        print("Daemon exiting")
    except KeyboardInterrupt:
        print("\nDaemon stopped.")
    raise SystemExit(code)