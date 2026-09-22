"""
DEMO Step 5 — Detect the breach via CloudTrail (the CAPTURE stage).

Reads AWS CloudTrail logs, correlates events against deployed decoys,
and flags any honeytoken usage as a CONFIRMED BREACH.

Usage:
    python demo/step5_detect_breach.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capture.watch import scan_once


def main():
    print("=" * 60)
    print("  STEP 5: DETECT THE BREACH  (CAPTURE)")
    print("=" * 60)
    scan_once()
    print("\n    Next -> python demo/step6_analyze_attack.py")


if __name__ == "__main__":
    main()
