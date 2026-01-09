import json
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"

def _iter_events() -> Iterable[dict]:
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue

def _duration_ms(e: dict) -> float | None:
    s = e.get("started_at")
    en = e.get("ended_at")

    if isinstance(s, (int, float)) and isinstance(en, (int, float)) and en >= s:
        return (en - s) * 1000.0
    return None

def _err_line(e: dict) -> str:
    text = (e.get("error") or e.get("stderr") or "").strip()
    if not text:
        return ""
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    return lines[-1] if lines else ""

def build_report(last_n: int = 200) -> dict:
    recent = deque(maxlen=last_n)
    for e in _iter_events():
        recent.append(e)

    per = defaultdict(lambda: {
        "runs": 0,
        "fails": 0,
        "dur_sum": 0.0,
        "dur_n": 0,
        "last_fail_time": None,
        "last_fail_line": "",
    })

    slowest: List[Tuple[float, str, str]] = []

    for e in recent:
        sid = e.get("script_id")
        if not sid:
            continue

        d = per[sid]
        d["runs"] += 1

        ok = bool(e.get("ok"))
        ms = _duration_ms(e)
        if ms is not None:
            d["dur_sum"] += ms
            d["dur_n"] += 1
            slowest.append((ms, sid, e.get("run_id", "")))
        
        if not ok:
            d["fails"] += 1
            t = e.get("ended_at") or e.get("started_at")
            if isinstance(t, (int, float)):
                d["last_fail_time"] = t
            d["last_fail_line"] = _err_line(e)
    
    rows = []
    for sid, d in per.items():
        runs = d["runs"]
        fails = d["fails"]
        fail_pct = (fails / runs * 100.0) if runs else 0.0
        avg_ms = (d["dur_sum"] / d["dur_n"]) if d["dur_n"] else None
        rows.append((fail_pct, fails, sid, runs, avg_ms, d["last_fail_time"], d["last_fail_line"]))
    
    rows.sort(reverse=True)

    slowest.sort(reverse=True)
    slowest = slowest[:10]

    return {"rows": rows, "slowest": slowest, "last_n": last_n}

def format_report(rep: dict) -> str:
    lines: List[str] = []
    last_n = rep["last_n"]
    lines.append(f"Report (last {last_n} events)")
    lines.append("")
    lines.append("Top failure rates:")
    lines.append(f"{'script':10} {'runs':>5} {'fails':>5} {'fail%':>6} {'avg_ms':>8} last_failure")
    for fail_pct, fails, sid, runs, avg_ms, last_fail_time, last_fail_line in rep["rows"][:10]:
        avg_ms_s = f"{avg_ms:.1f}" if isinstance(avg_ms, (int, float)) else "-"
        if isinstance(last_fail_time, (int, float)):
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_fail_time))
            msg = (last_fail_line or "").strip()
            last_fail_s = f"{t} | {msg}" if msg else t
        else:
            last_fail_s = "-"
        lines.append(f"{sid:10} {runs:5d} {fails:5d} {fail_pct:6.1f} {avg_ms_s:>8} {last_fail_s}")
    
    lines.append("")
    lines.append("Slowest runs:")
    lines.append(f"{'ms':>8} {'script':10} run_id")
    for ms, sid, run_id, in rep["slowest"]:
        lines.append(f"{ms:8.1f} {sid:10} {run_id}")
    
    return "\n".join(lines)