import json 
import time
from pathlib import Path
from typing import Dict, Iterator, Optional

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"

def iter_log_lines() -> Iterator[dict]:
    if not LOG_PATH.exists():
        return
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def last_run_by_script() -> Dict[str, dict]:
    last: Dict[str, dict] = {}
    for e in iter_log_lines():
        sid = e.get("script_id")
        if not sid:
            continue
        last[sid] = e
    return last

def tail_follow(n: int = 20, poll: float = 0.5) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch(exist_ok=True)

    with LOG_PATH.open("r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[-n:]:
            print(line.rstrip())
        try:
            while True:
                where = f.tell()
                line = f.readline()
                if not line:
                    time.sleep(poll)
                    f.seek(where)
                    continue
                print(line.rstrip())
        except KeyboardInterrupt:
            print("\nStopped tail.")
        