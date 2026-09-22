"""
DEMO Step 4 — Simulate an attacker (controlled adversary).

Runs a scripted attacker who enumerates buckets, picks a juicy-looking
decoy, downloads the fake credentials.txt, and uses the stolen
honeytoken key. Every action is logged by CloudTrail.

The stolen key is deny-all, so nothing real is touched.

Usage:
    python demo/step4_simulate_attacker.py
    python demo/step4_simulate_attacker.py --step   # pause between phases
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from attacker.simulate import main as simulate


def main():
    print("=" * 60)
    print("  STEP 4: SIMULATE AN ATTACKER  (credential compromise)")
    print("=" * 60)
    simulate()
    print("\n    Next -> python demo/step5_detect_breach.py")


if __name__ == "__main__":
    main()
