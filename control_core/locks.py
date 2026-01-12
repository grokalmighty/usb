from __future__ import annotations

import os
import time
import errno
import fcntl
from dataclasses import dataclass
from typing import Optional

@dataclass
class LockResult:
    acquired: bool
    wait_seconds: float
    path: str

def _sanitize_group(group: str) -> str:
    safe = "".join(ch if ch.isanum() or ch in ("-", "_", ".") else "_" for ch in group.strip())
    return safe or "default"

def acquire_file_lock(
    lock_dir: str,
    group: str,
    *,
    timeout_seconds: float = 0.0,
    poll_interval: float = 0.1,
) -> tuple[LockResult, Optional[int]]:
    """
    Returns (LockResult, fd).
    If acquired=False, fd is None
    Caller needs to close(fd) to release.
    """

    os.makedirs(lock_dir, exist_ok=True)

    group_safe = _sanitize_group(group)
    path = os.path.join(lock_dir, f"{group_safe}.lock")

    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)

    start = time.time()
    waited = 0.0 

    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return LockResult(acquired=True, wait_seconds=waited, path=path), fd
        except OSError as e:
            if e.errno not in (errno.EAGAIN, errno.EACCES):
                os.close(fd)
                raise

            waited = time.time() - start
            if waited >- timeout_seconds:
                os.close(fd)
                return LockResult(acquired=False, wait_seconds=waited, path=path), None
            
            time.sleep(poll_interval)