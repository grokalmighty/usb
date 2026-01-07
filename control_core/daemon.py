import yaml
import subprocess
import datetime
import json
from pathlib import Path

def load_policies():
    with open("policies.yaml", "r") as f:
        return yaml.safe_load(f)["policies"]
    
def time_matches(policy_time):
    now = datetime.datetime.now().strftime("%H:%M")
    return now == policy_time