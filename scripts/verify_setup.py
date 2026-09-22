"""
CLOUDSNARE — Setup verification.

Run this FIRST, before anything else. It confirms:
  1. Your AWS credentials are configured and working.
  2. Which AWS account you're pointed at (so you don't
     accidentally run CLOUDSNARE against the wrong account).
  3. Your region is set.

If this passes, your foundation (Part 1) is done.

Usage:
    python scripts/verify_setup.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from config import AWS_REGION


def main():
    print("=== CLOUDSNARE setup check ===\n")
    try:
        sts = boto3.client("sts", region_name=AWS_REGION)
        identity = sts.get_caller_identity()
    except NoCredentialsError:
        print("[X] No AWS credentials found.")
        print("    Run `aws configure` and enter your access key + secret.")
        sys.exit(1)
    except ClientError as e:
        print(f"[X] AWS rejected the request: {e}")
        sys.exit(1)

    print(f"[+] Credentials work.")
    print(f"[+] Account ID : {identity['Account']}")
    print(f"[+] Identity   : {identity['Arn']}")
    print(f"[+] Region     : {AWS_REGION}")
    print("\n[!] Confirm the Account ID above is your ISOLATED CLOUDSNARE account,")
    print("    NOT a personal or production account.")
    print("\nFoundation looks good. Ready for Part 2 (the Mapper).")


if __name__ == "__main__":
    main()
