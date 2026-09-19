"""
VEILGUARD — reset demo state.

Clears captured attacks, intelligence, and remediation state so you can
run a clean end-to-end demo from scratch. Does NOT touch AWS resources or
your decoys — only local demo data files.

Usage:
    python scripts/reset_demo.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    CAPTURE_FILE, INTEL_FILE, REPORT_FILE,
    REMEDIATION_FILE, REMEDIATION_REPORT, SNAPSHOT_DIR,
)


def main():
    targets = [CAPTURE_FILE, INTEL_FILE, REPORT_FILE,
               REMEDIATION_FILE, REMEDIATION_REPORT]
    removed = 0
    for path in targets:
        if os.path.exists(path):
            os.remove(path)
            removed += 1
            print(f"  cleared {os.path.basename(path)}")

    # clear old snapshots too (keeps the surface history clean for the demo)
    if os.path.isdir(SNAPSHOT_DIR):
        for f in os.listdir(SNAPSHOT_DIR):
            if f.startswith("snapshot_") and f.endswith(".json"):
                os.remove(os.path.join(SNAPSHOT_DIR, f))
                removed += 1

    print(f"\n[+] Demo state reset ({removed} file(s) cleared).")
    print("[i] Your AWS resources and decoys are untouched.")
    print("    Run a fresh loop: deploy -> attack -> capture -> intel.\n")


if __name__ == "__main__":
    main()
