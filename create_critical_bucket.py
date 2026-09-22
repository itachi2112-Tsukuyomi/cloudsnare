"""
CLOUDSNARE — demo helper: create a "critical" exposure.

Creates a genuinely public S3 bucket so CLOUDSNARE's Mapper flags it as a
HIGH-risk (critical) exposure, and the Remediation engine can then fix it.
This automates the manual steps used when testing, giving you a repeatable
way to spawn a red flag for a demo.

Safety notes:
  - The bucket name does NOT start with "cloudsnare", so remediation treats it
    as a REAL exposure (not a decoy) and will offer to fix it.
  - This makes a bucket publicly readable. That is the whole point (it is the
    misconfiguration CLOUDSNARE detects), but only do this in your isolated
    demo account.

Usage (project root, venv active):
    python scripts/create_critical_bucket.py               # create it
    python scripts/create_critical_bucket.py --destroy     # remove it
    python scripts/create_critical_bucket.py --name my-bucket-name
"""

import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION

# A realistic, tempting name — NOT starting with "cloudsnare" so it's treated
# as a real exposure by the remediation engine.
DEFAULT_NAME = "company-financial-records-demo"


def _public_policy(bucket):
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicRead",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket}/*",
        }],
    })


def create(bucket, region):
    s3 = boto3.client("s3", region_name=region)

    # 1. Create the bucket (region-aware: us-east-1 must NOT send a location).
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        print(f"[+] Created bucket: {bucket}")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"[i] Bucket already exists: {bucket}")
        else:
            print(f"[X] Could not create bucket: {e}")
            sys.exit(1)

    # 2. Turn OFF Block Public Access (so the public policy can take effect).
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    print("[+] Disabled Block Public Access")

    # 3. Attach a public-read bucket policy — this is what makes it "critical".
    s3.put_bucket_policy(Bucket=bucket, Policy=_public_policy(bucket))
    print("[+] Attached public-read policy")

    # 4. Drop a file in, so there's something 'exposed'.
    s3.put_object(Bucket=bucket, Key="salaries.csv",
                  Body=b"employee,salary\n(demo data - not real)\n")
    print("[+] Uploaded a sample object (salaries.csv)")

    print(f"\n[✓] '{bucket}' is now PUBLIC and will show as HIGH/critical.")
    print("    Next:")
    print("      python -m mapper.run_mapper          # detect it")
    print("      python -m remediation.remediate      # see the fix recommendation")


def destroy(bucket, region):
    s3 = boto3.client("s3", region_name=region)
    try:
        # empty then delete
        objs = s3.list_objects_v2(Bucket=bucket).get("Contents", [])
        for o in objs:
            s3.delete_object(Bucket=bucket, Key=o["Key"])
        s3.delete_bucket(Bucket=bucket)
        print(f"[+] Removed bucket: {bucket}")
    except ClientError as e:
        print(f"[i] Could not remove (may not exist): {e}")


def main():
    ap = argparse.ArgumentParser(description="Create a critical S3 exposure for demos")
    ap.add_argument("--name", default=DEFAULT_NAME,
                    help="bucket name (must be globally unique; avoid 'cloudsnare' prefix)")
    ap.add_argument("--destroy", action="store_true", help="remove the bucket")
    args = ap.parse_args()

    if args.name.startswith("cloudsnare"):
        print("[!] Warning: a name starting with 'cloudsnare' will be treated as a")
        print("    decoy and skipped by remediation. Use a different name.")

    if args.destroy:
        destroy(args.name, AWS_REGION)
    else:
        create(args.name, AWS_REGION)


if __name__ == "__main__":
    main()
