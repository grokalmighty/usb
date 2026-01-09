import json
import time
from collections import deque
from pathlib import Path
from typing import List, Optional

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"

