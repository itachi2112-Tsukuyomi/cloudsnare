"""
DEMO Step 7 — Remediate exposures (the ACT stage).

Shows fix recommendations, approves them, and applies them —
with human approval at every step. Decoys are never "fixed".

Usage:
    python demo/step7_remediate.py                  # show recommendations
    python demo/step7_remediate.py --approve-all    # approve all fixes
    python demo/step7_remediate.py --apply          # apply approved fixes
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from remediation.remediate import main as remediate


def main():
    print("=" * 60)
    print("  STEP 7: REMEDIATE EXPOSURES  (ACT)")
    print("=" * 60)
    remediate()
    print("\n    Next -> python demo/step8_launch_dashboard.py")


if __name__ == "__main__":
    main()
