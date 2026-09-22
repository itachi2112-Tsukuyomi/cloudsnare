"""
CLEANUP — Tear down all deployed decoys.

Runs Terraform destroy to remove all decoy S3 buckets and honeytoken
IAM users created during the demo. Run this when you're done.

Usage:
    python demo/cleanup_destroy_decoys.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deception.deploy import main as deploy_main


def main():
    print("=" * 60)
    print("  CLEANUP: DESTROY ALL DECOYS")
    print("=" * 60)
    sys.argv = [sys.argv[0], "--destroy"]
    deploy_main()


if __name__ == "__main__":
    main()
