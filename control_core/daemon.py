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

def run_script(script_id):
    script_dir = Path("scripts") / script_id
    manifest_path = script_dir / "manifest.yaml"

    if not manifest_path.exists():
        raise Exception("Missing manifest")
    
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    entrypoint = script_dir / manifest["entrypoint"]

    result = subprocess.run(
        ["python3", entrypoint],
        capture_output=True,
        text=True,
        timeout=manifest.get("timeout_seconds", 10)
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }