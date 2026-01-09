import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"