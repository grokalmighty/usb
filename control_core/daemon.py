import yaml
import subprocess
import datetime
import json
from pathlib import Path

def load_policies():
    with open("policies.yaml", "r") as f:
        return yaml.safe_load(f)["policies"]