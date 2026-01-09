import csv
import json
from pathlib import Path
from typing import Iterable, Optional

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"