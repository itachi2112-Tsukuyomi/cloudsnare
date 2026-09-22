"""
DEMO Step 3 — Deploy decoy buckets with honeytokens (the DECEIVE stage).

Creates decoy S3 buckets via Terraform, each containing a fake
credentials.txt with a deny-all honeytoken key. These traps blend
into the real environment and catch attackers who take the bait.

Usage:
    python demo/step3_deploy_decoys.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deception.deploy import main as deploy_decoys


def main():
    print("=" * 60)
    print("  STEP 3: DEPLOY DECOYS WITH HONEYTOKENS  (DECEIVE)")
    print("=" * 60)
    sys.argv = [sys.argv[0]]
    deploy_decoys()
    print("    Next -> python demo/step4_simulate_attacker.py")


if __name__ == "__main__":
    main()
