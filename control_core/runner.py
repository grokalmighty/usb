import importlib
import json
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Tuple
from uuid import uuid4

from .registry import Script

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"

def _load_uncallable(entrypoint: str):
    module_path, func_name = entrypoint.split(":")
    module = importlib.import_module(module_path)
    fn = getattr(module, func_name)
    return fn

def log_event(event: Dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")