import sys

from .registry import discover_scripts, list_scripts, update_manifest
from .runner import run_script

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
    
    print(f"Unknown command: {cmd}")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())