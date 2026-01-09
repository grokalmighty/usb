import json
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"
