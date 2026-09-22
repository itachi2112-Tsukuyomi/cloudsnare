"""
DEMO Step 1 — Create a public S3 bucket (the "misconfiguration").

Creates a genuinely public S3 bucket so CLOUDSNARE's Mapper flags it as a
HIGH-risk exposure, and the Remediation engine can later fix it.

The bucket name does NOT start with "cloudsnare", so the system treats it
as a REAL exposure (not a decoy).

Usage:
    python demo/step1_create_public_bucket.py
    python demo/step1_create_public_bucket.py --name my-bucket-name
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from create_critical_bucket import create, DEFAULT_NAME
from config import AWS_REGION


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Step 1: Create a public S3 bucket")
    ap.add_argument("--name", default=DEFAULT_NAME,
                    help="bucket name (must be globally unique; avoid 'cloudsnare' prefix)")
    args = ap.parse_args()

    if args.name.startswith("cloudsnare"):
        print("[!] Warning: a name starting with 'cloudsnare' will be treated as a")
        print("    decoy and skipped by remediation. Use a different name.")

    print("=" * 60)
    print("  STEP 1: CREATE A PUBLIC S3 BUCKET (the misconfiguration)")
    print("=" * 60)
    create(args.name, AWS_REGION)
    print("\n    Next -> python demo/step2_scan_attack_surface.py")


if __name__ == "__main__":
    main()
