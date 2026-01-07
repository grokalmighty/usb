from pathlib import Path

def main():
    p = Path("data/watchme.txt")
    text = p.read_text(encoding="utf-8") if p.exists() else "(missing)"
    print(f"watchme.txt now ssays: {text.strip()}")