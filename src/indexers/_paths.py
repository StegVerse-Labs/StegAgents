from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # .../src
REPO_ROOT = BASE_DIR.parent                     # repo root

RESEARCH_ROOT = REPO_ROOT / "research"
INBOX_DIR = RESEARCH_ROOT / "inbox"
OUT_DIR = RESEARCH_ROOT / "out"
STATE_DIR = RESEARCH_ROOT / "state"

for _d in (RESEARCH_ROOT, INBOX_DIR, OUT_DIR, STATE_DIR):
    _d.mkdir(parents=True, exist_ok=True)
