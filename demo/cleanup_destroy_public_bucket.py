"""
CLEANUP — Delete the public S3 bucket created in Step 1.

Empties and removes the demo bucket that was used as a "real"
misconfiguration for CLOUDSNARE to detect and remediate.

Usage:
    python demo/cleanup_destroy_public_bucket.py
    python demo/cleanup_destroy_public_bucket.py --name my-bucket-name
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from create_critical_bucket import destroy, DEFAULT_NAME
from config import AWS_REGION


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Remove the demo public bucket")
    ap.add_argument("--name", default=DEFAULT_NAME,
                    help="bucket name to remove")
    args = ap.parse_args()

    print("=" * 60)
    print("  CLEANUP: DELETE THE PUBLIC S3 BUCKET")
    print("=" * 60)
    destroy(args.name, AWS_REGION)


if __name__ == "__main__":
    main()
