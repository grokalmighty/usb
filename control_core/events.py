from __future__ import annotations
import subprocess
import time
import socket
from typing import Optional, Set, Dict, Any, List

def list_running_apps_macos() -> set[str]:
    """
    Returns a set of GUI app process names
    """

    try:
        out = subprocess.check_output(
            ["osascript", "-e", 'tell application "System Events" to get name of application processes'],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        apps = set()
        for part in out.split(","):
            name = part.strip()
            if name:
                apps.add(name)
        return apps
    except Exception:
        return set()
    
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

def normalize_app_name(name: str) -> str:
    n = (name or "").strip()

    for suf in ("Helper", " Helper (Renderer)", " Helper (GPU)", " Helper (Plugin)", " Helper (Alerts)"):
        if n.endswith(suf):
            n = n[: -len(suf)]
    return n