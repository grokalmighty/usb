from __future__ import annotations
import subprocess
import time
import socket
from typing import Optional, Set, Dict, Any, List

def is_process_running_exact(name: str) -> bool:
    """
    True if a process with exact name exists.
    """

    try:
        subprocess.check_output(["pgrep", "-x", name], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False
    
def get_idle_seconds_macos() -> Optional[float]:
    """
    Returns idle seconds, or None if unsupported
    """
    try:
        out = subprocess.check_output(
            ["ioreg", "-c", "IOHIDSystem"],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in out.splitlines():
            if "HIDIdleTime" in line:
                parts = line.strip().split()
                for token in reversed(parts):
                    if token.isdigit():
                        ns = int(token)
                        return ns / 1e9
        return None
    except Exception:
        return None

def list_process_names() -> Set[str]:
    try:
        out = subprocess.check_output(["ps", "-axo", "comm="], text=True)
        names: Set[str] = set()
        for line in out.splitlines():
            name = line.strip()
            if not name:
                continue
            
            name = name.split("/")[-1]
            names.add(name)
        return names
    except Exception:
        return set()
    
def get_local_ip() -> Optional[str]:
    """
    Returns local IP used for default route, or None if network seems down.
    """

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.settimeout(1.0)
            s.connect(("8.8.8.8", 53))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        return None

def match_apps(event_apps: Optional[List[str]], opened_or_closed: str) -> bool:
    """
    If event_apps is None/empty => match any app.
    Else match against list.
    """

    if not event_apps:
        return True
    return opened_or_closed in set(event_apps)