import json 
import time
from pathlib import Path
from typing import Dict, Iterator, Optional

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "logs.jsonl"