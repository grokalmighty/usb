import sys
import time

from .registry import discover_scripts, list_scripts, update_manifest
from .runner import run_script
from .installer import install_script_from_folder
from .logs import last_run_by_script, tail_follow
from .validator import validate_script_folder

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
    
    if cmd == "install":
        if len(argv) < 2:
            print("Usage: python -m control_core.cli install <folder> [--force]")
            return 2

        folder = argv[1]
        force = "--force" in argv[2:]
        script_id = install_script_from_folder(folder, force=force)
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
    
    print(f"Unknown command: {cmd}")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())