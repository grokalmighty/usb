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