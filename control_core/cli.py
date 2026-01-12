import sys
import time

from .registry import discover_scripts, list_scripts, update_manifest
from .runner import run_script
from .installer import install_script_from_folder
from .logs import last_run_by_script, tail_follow
from .validator import validate_script_folder
from .daemon_state import read_pid, pid_is_running, PID_PATH, LOCKS_DIR
from .stats import compute_stats
from .history import get_history, format_event
from .log_rotate import rotate_logs
from .exporter import export_csv
from .report import build_report, format_report
from .locks import acquire_file_lock, release_file_lock
from .scheduler_state import load_state
from .scheduler import get_interval_seconds

def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python -m control_core.cli [list|run <id>|enable <id>|disable <id>|set-interval <id> <seconds>]")
        return 2
    
    cmd = argv[0]

    if cmd == "list":
        for s in list_scripts():
            status = "ENABLED" if s.enabled else "disabled"
            sched = s.schedule or {}
            if sched.get("type") == "interval":
                sched_str = f"interval={sched.get('seconds')}s"
            else:
                sched_str = "schedule=none"
            print(f"{s.id:10} {status:8} {sched_str:16} {s.name}")
        return 0
    
    if cmd == "run":
        if len(argv) < 2:
            print("Usage: python -m control_core.cli run <id>")
            return 2
        script_id = argv[1]
        scripts = discover_scripts()
        if script_id not in scripts:
            print(f"Unknown script id: {script_id}")
            return 1
        
        ok, run_id = run_script(scripts[script_id])
        print(f"run_id={run_id} ok={ok}")
        return 0 if ok else 1

    if cmd == "enable":
        if len(argv) < 2:
            print("Usage: python -m control_core.cli enable <id>")
            return 2
        script_id = argv[1]
        update_manifest(script_id, lambda m: m.__setitem__("enabled", True))
        print(f"Enabled {script_id}")
        return 0

    if cmd == "disable":
        if len(argv) < 2:
            print("Usage: python -m control_core.cli disable <id>")
            return 2
        script_id = argv[1]
        update_manifest(script_id, lambda m: m.__setitem__("enabled", False))
        print(f"Disabled {script_id}")
        return 0
    
    if cmd == "set-interval":
        if len(argv) < 3:
            print("Usage: python -m control_core.cli set-interval <id> <seconds>")
            return 2
        script_id = argv[1]
        try:
            seconds = float(argv[2])
        except ValueError:
            print("seconds must be a number")
            return 2

        if seconds <= 0:
            print("seconds must be > 0")
            return 2
        
        def updater(m):
            m["schedule"] = {"type": "interval", "seconds": seconds}

        update_manifest(script_id, updater)
        print(f"Set {script_id} interval to {seconds}s")
        return 0

    if cmd == "set-time":
        if len(argv) < 3:
            print("Usage: python -m control_core.cli set-time <id> <HH:MM> [--tz <IANA_TZ>]")
            return 2
        
        script_id = argv[1]
        at = argv[2]

        tz = "America/New_York"
        if "--tz" in argv:
            i = argv.index("--tz")
            if i + 1 >= len(argv):
                print("Missing value after --tz")
                return 2
            tz = argv[i + 1]
        
        def updater(m):
            m["schedule"] = {"type": "time", "at": at, "tz": tz}

        if ":" not in at or len(at.split(":")) != 2:
            print("time must be HH:MM (24-hour)")
            return 2
        try:
            hh = int(at.split(":")[0]); mm = int(at.split(":")[1])
            if not (0 <= hh <= 23 and 0 <= mm <= 59):
                raise ValueError()
        except ValueError:
            print("time must be HH:MM (00:00 to 23:59)")
            return 2
        update_manifest(script_id, updater)
        print(f"Set {script_id} daily time to {at} ({tz})")
        return 0
    
    if cmd == "set-time-weekdays":
        if len(argv) < 3:
            print("Usage: python -m control_core.cli set-time-weekdays <id> <HH:MM> [--tz <IANA_TZ>]")
            return 2
        
        script_id = argv[1]
        at = argv[2]

        tz = "America/New_York"
        if "--tz" in argv:
            i = argv.index("--tz")
            if i + 1 >= len(argv):
                print("Missing value after --tz")
                return 2
            tz = argv[i + 1]
        
        def updater(m):
            m["schedule"] = {"type": "time", "at": at, "tz": tz, "days": [1,2,3,4,5]}
        
        update_manifest(script_id, updater)
        print(f"Set {script_id} time to {at} on weekdays (Mon-Fri) ({tz})")
        return 0 
    
    if cmd == "install":
        if len(argv) < 2:
            print("Usage: python -m control_core.cli install <folder> [--force]")
            return 2

        folder = argv[1]
        force = "--force" in argv[2:]

        try:
            script_id = install_script_from_folder(folder, force=force)
        
        except Exception as e:
            print(f"Install failed: {e}")
            return 1
        
        print(f"Installed {script_id}")
        return 0

    if cmd == "status":
        scripts = discover_scripts()
        last = last_run_by_script()

        for sid in sorted(scripts.keys()):
            s = scripts[sid]
            status = "ENABLED" if s.enabled else "disabled"
            e = last.get(sid)

            if not e:
                print(f"{sid:10} {status:8} last_run=never")
                continue

            ok = e.get("ok")
            ended = e.get("ended_at", 0)
            when = time.strftime("%H:%M:%S", time.localtime(ended)) if ended else "unknown"
            print(f"{sid:10} {status:8} last_run={when} ok={ok}")
        return 0

    if cmd == "schedule":
        scripts = discover_scripts()
        state = load_state()
        now = time.time()

        print("Schedules:")
        for sid in sorted(scripts.keys()):
            s = scripts[sid]
            if not s.enabled:
                continue
            interval = get_interval_seconds(s)
            if interval is None:
                continue

            last = state.get(sid, {}).get("last_fired_at")
            if isinstance(last, (int, float)):
                due_in = max(0.0, interval - (now - float(last)))
                print(f"{sid:10} interval={interval:>6.1f}s due_in={due_in:>6.1f}s")
            else:
                print(f"{sid:10} interval={interval:>6.1f}s due_in= now")
        return 0
    
    if cmd == "tail":
        # Usage: tail [n]
        n = 20
        if len(argv) >= 2:
            try:
                n = int(argv[1])
            except ValueError:
                print("Usage: python -m control_core.cli tail [n]")
                return 2
        tail_follow(n=n)
        return 0
    
    if cmd == "validate":
        if len(argv) < 2:
            print("Usage: python -m control_core.cli validate <folder>")
            return 2
        ok, errs = validate_script_folder(argv[1])
        
        if ok:
            print("OK: Script folder looks valid")
            return 0
        print("NOT OK:")
        for e in errs:
            print(f" - {e}")
        return 1
    
    if cmd == "daemon-status":
        pid = read_pid()
        if pid is None:
            print(f"Daemon not running (no pid file at {PID_PATH})")
            return 1
        if pid_is_running(pid):
            print(f"Daemon is running with pid {pid} (pid file: {PID_PATH})")
            return 0
        print(f"Stale pid file: pid={pid} not running (pid file: {PID_PATH})")
        return 1
    
    if cmd == "stop-daemon":
        pid = read_pid()
        if pid is None:
            print(f"Daemon not running (no pid file at {PID_PATH})")
            return 1
        if not pid_is_running(pid):
            print(f"Stale pid file: pid={pid} not running (pid file: {PID_PATH})")
            from .daemon_state import clear_pid
            clear_pid()
            return 1
        try:
            from .daemon_state import stop_pid
            stop_pid(pid)
            print(f"Sent SIGTERM to daemon pid={pid}")
            return 0
        except Exception as e:
            print(f"Failed to stop daemon: {e}")
            return 1
    
    if cmd == "stats":
        # Usage: stats [n]
        n = 200
        if len(argv) >= 2:
            try:
                n = int(argv[1])
            except ValueError:
                print("Usage: python-m control_core.cli stats [n]")
                return 2
        
        stats = compute_stats(last_n=n)
        if not stats:
            print("No stats yet (logs empty).")
            return 0
    
        print(f"Stats (last {n} events):")
        print(f"{'script':10} {'runs':>5} {'fails':>5} {'fail':>6} {'avg_ms':>8} {'last_ok':>7} last_run_id")

        for sid in sorted(stats.keys()):
            d = stats[sid]
            runs = d["runs"]
            fails = d["fails"]
            fail_pct = (fails / runs * 100.0) if runs else 0.0
            avg_ms = d["avg_ms"]
            last_ok = d["last_ok"]
            rid = d["last_run_id"] or ""
            print(f"{sid:10} {runs:5} {fails:5} {fail_pct:6.1f}% {avg_ms:8.1f} {str(last_ok):>7} {rid}")
        return 0
    
    if cmd == "history":
        if len(argv) < 2:
            print("Usage: python -m control_core.cli history <script_id> [n]")
            return 2
        
        script_id = argv[1]
        n = 20
        if len(argv) >= 3:
            try:
                n = int(argv[2])
            except ValueError:
                print("Usage: python -m control_core.cli history <script_id> [n]")
                return 2
        
        events = get_history(script_id, n=n)
        if not events:
            print(f"No history for script_id={script_id}")
            return 0
        
        print(f"History for {script_id} (last {len(events)} runs):")
        for e in events:
            print(" - " + format_event(e))
        return 0
    
    if cmd == "rotate-logs":
        archived = rotate_logs()
        if archived.name == "logs.jsonl":
            print("No rotation needed (logs empty).")
        else:
            print(f"Rotated logs to {archived}")
        return 0

    if cmd == "export":
        if len(argv) < 2:
            print("Usage: python -m control_core.cli export <output.csv> [max_rows]")
            return 2
        out = argv[1]
        max_rows = None
        if len(argv) >= 3:
            try:
                max_rows = int(argv[2])
            except ValueError:
                print("max_rows must be an integer")
                return 2
        
        path = export_csv(out, max_rows=max_rows)
        print(f"Exported to {path}")
        return 0

    if cmd == "report":

        fails_only = "--fails-only" in argv 

        # Script filter
        script_id = None
        if "--script" in argv:
            j = argv.index("--script")
            if j + 1 >= len(argv):
                print("Usage: python -m control_core.cli report [n] [--script <id>] OR report --minutes <N> [--script <id>]")
                return 2
            script_id = argv[j + 1]

        # Minutes 
        if "--minutes" in argv:
            i = argv.index("--minutes")
            if i + 1 >= len(argv):
                print("Usage: python -m control_core.cli report --minutes <N>")
                return 2
            try:
                minutes = int(argv[i + 1])
            except ValueError:
                print("minutes must be an integer")
                return 2
            from .report import build_report_minutes, format_report
            rep = build_report_minutes(minutes=minutes, script_id=script_id, fails_only=fails_only)
            print(format_report(rep))
            return 0

        # Default last-n
        n = 200
        if len(argv) >= 2:
            try:
                n = int(argv[1])
            except ValueError:
                print("Usage: python -m control_core.cli report [n]")
                return 2
        
        from .report import build_report, format_report
        rep = build_report(last_n=n, script_id=script_id, fails_only=fails_only)
        print(format_report(rep))
        return 0

    if cmd == "trigger":
        if len(argv) < 2:
            print("Usage: python -m control_core.cli trigger <script_id>")
            return 2
        
        script_id = argv[1]

        payload = {"trigger": True}
        timeout = 20.0

        if "--timeout" in argv:
            i = argv.index("--timeout")
            if i + 1 >= len(argv):
                print("Missing value after --timeout")
                return 2
            try:
                timeout = float(argv[i + 1])
            except ValueError:
                print("timeout must be a number")
                return 2
        
        if "--payload" in argv:
            i = argv.index("--payload")
            if i + 1 >= len(argv):
                print("Missing value after --payload")
                return 2
            import json as _json
            try:
                user_payload = _json.loads(argv[i + 1])
            except Exception as e:
                print(f"Invalid JSON for --payload: {e}")
                return 2
            if not isinstance(user_payload, dict):
                print("--payload nust be a JSON object")
                return 2
            
            payload.update(user_payload)

        from .registry import discover_scripts
        from .runner import run_script

        scripts = discover_scripts()
        s = scripts.get(script_id)
        if not s:
            print(f"Unkown script_id: {script_id}")
            return 1
        if not s.enabled:
            print(f"Script is disabled: {script_id}")
            return 1

        ok, run_id = run_script(s, timeout_seconds=timeout, payload=payload)
        print(f"Triggered {script_id} ok={ok} run_id={run_id}")
        return 0
    
    if cmd == "locks":
        LOCKS_DIR.mkdir(parents=True, exist_ok=True)

        lock_files = sorted(LOCKS_DIR.glob("*.lock"))
        if not lock_files:
            print(f"No lock files in {LOCKS_DIR}")
            return 0
        
        print(f"Locks in {LOCKS_DIR}:")
        for p in lock_files:
            group = p.stem
            res, fd = acquire_file_lock(str(LOCKS_DIR), group, timeout_seconds=0.0)
            if res.acquired and fd is not None:
                release_file_lock(fd)
                status = "FREE"
            else:
                status = "BUSY"
            print(f" - {group:20} {status}")
        return 0
            
    print(f"Unknown command: {cmd}")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())