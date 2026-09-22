"""
DEMO Step 6 — Analyze the attack (the LEARN stage).

Processes captured events to produce:
  - Time-to-Attack metric
  - Attacker profile (IPs, actions, decoys hit)
  - MITRE ATT&CK technique mapping
  - Attack timeline
  - Plain-English incident report

Usage:
    python demo/step6_analyze_attack.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.run_intel import main as run_intel


def main():
    print("=" * 60)
    print("  STEP 6: ANALYZE THE ATTACK  (LEARN)")
    print("=" * 60)
    run_intel()
    print("    Next -> python demo/step7_remediate.py")


if __name__ == "__main__":
    main()
