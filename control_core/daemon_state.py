import os 
import signal
from pathlib import Path
from typing import Optional

PID_PATH = Path(__file__).resolve().parent.parent / "data" / "daemon.pid"

def write_pid() -> None:
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")

def read_pid() -> Optional[int]:
    if not PID_PATH.exists():
        return None
    try:
        return int(PID_PATH.read_text(encoding="utf-8").strip())
    except Exception:
        return None
    
def clear_pid() -> None:
    try:
        PID_PATH.unlink(missing_ok=True)
    except TypeError:
        if PID_PATH.exists():
            PID_PATH.unlink()

def pid_is_running(pid: int) -> bool:
    """
    os.kill(pid, 0) checks existence/permission.
    """

    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

def stop_pid(pid: int) -> None:
    os.kill(pid, signal.SIGTERM)