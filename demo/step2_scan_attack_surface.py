"""
DEMO Step 2 — Scan the AWS attack surface (the MAP stage).

Scans S3, EC2, RDS, Lambda, and ELB for internet-facing resources.
Saves a snapshot and shows what changed since the last scan.

Usage:
    python demo/step2_scan_attack_surface.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapper.run_mapper import main as run_mapper


def main():
    print("=" * 60)
    print("  STEP 2: SCAN THE ATTACK SURFACE  (MAP)")
    print("=" * 60)
    run_mapper()
    print("    Next -> python demo/step3_deploy_decoys.py")


if __name__ == "__main__":
    main()
