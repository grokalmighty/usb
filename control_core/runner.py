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
