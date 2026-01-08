from pathlib import Path

def main(payload=None):
    payload = payload or {}
    failed = payload.get("failed_event", {})

    print("ALERT: Script failure")
    print(f"script_id: {failed.get('script_id')}")
    print(f"run_id: {failed.get('run_id')}")

    err = failed.get("error") or ""
    stderr = failed.get("stderr") or ""
    stdout = failed.get("stdout") or ""

    tb = err if err else stderr

    if tb:
        print("\ntraceback:")
        print(tb.strip())
    
    if stdout and stdout.strip():
        print("\nfailed stdout:")
        print(stdout.strip()) 