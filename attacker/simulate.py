"""
CLOUDSNARE Attacker Simulation (the demo adversary).

This script plays an attacker who has gained a foothold in the account and
goes hunting. It is intentionally scripted so the demo is reliable and
repeatable — you can run the whole attack on command in front of a panel.

Attack chain (mirrors a real credential-compromise scenario):
  1. RECON     — enumerate S3 buckets (what can I see?)
  2. TARGET    — spot a tempting bucket (prod-db-backup, admin-credentials)
  3. LOOT      — download credentials.txt from the decoy
  4. USE       — authenticate with the STOLEN honeytoken key and probe

Step 4 is the money shot: using the honeytoken key generates a CloudTrail
management event tagged with that key's ID. CLOUDSNARE's Capture Engine then
detects it as a CONFIRMED BREACH — and knows exactly which decoy leaked it.

SAFETY: the stolen key is a deny-all honeytoken, so every action it attempts
is either harmless (GetCallerIdentity) or denied. Nothing real is touched.
This is a simulation of an attacker, run against your own traps.

Usage (project root, venv active):
    python -m attacker.simulate            # run the full attack
    python -m attacker.simulate --step     # pause between phases (good for demos)
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION


JUICY_HINTS = ("backup", "credential", "prod", "secret", "admin",
               "internal", "keys", "db", "export", "archive")


def _banner():
    print("=" * 64)
    print("  CLOUDSNARE ATTACKER SIMULATION")
    print("  (controlled demo adversary — targets only your own decoys)")
    print("=" * 64)


def _pause(step):
    if step:
        input("\n    [press Enter to continue to the next phase]\n")


def recon(region):
    """Phase 1: what buckets can the attacker see?"""
    print("\n[PHASE 1] RECON — enumerating S3 buckets...")
    s3 = boto3.client("s3", region_name=region)
    buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    for b in buckets:
        print(f"    found bucket: {b}")
    print(f"    -> {len(buckets)} buckets visible.")
    return buckets


def pick_target(buckets):
    """Phase 2: choose the most tempting-looking bucket."""
    print("\n[PHASE 2] TARGET — looking for something juicy...")
    ranked = sorted(
        buckets,
        key=lambda b: sum(h in b.lower() for h in JUICY_HINTS),
        reverse=True,
    )
    target = next((b for b in ranked
                   if any(h in b.lower() for h in JUICY_HINTS)), None)
    if target:
        print(f"    attacker picks: {target}  (looks valuable!)")
    else:
        print("    nothing obviously juicy found.")
    return target


def loot(region, bucket):
    """Phase 3: download the credentials file from the target."""
    print(f"\n[PHASE 3] LOOT — grabbing credentials from {bucket}...")
    s3 = boto3.client("s3", region_name=region)
    try:
        obj = s3.get_object(Bucket=bucket, Key="credentials.txt")
        body = obj["Body"].read().decode("utf-8", errors="replace")
    except ClientError as e:
        print(f"    couldn't read credentials.txt: {e}")
        return None, None

    print("    got a credentials file! contents:")
    for line in body.splitlines():
        print(f"      | {line}")

    key_id = secret = None
    for line in body.splitlines():
        if "aws_access_key_id" in line:
            key_id = line.split("=", 1)[1].strip()
        elif "aws_secret_access_key" in line:
            secret = line.split("=", 1)[1].strip()
    return key_id, secret


def use_stolen(region, key_id, secret):
    """Phase 4: authenticate with the stolen key — this trips the wire."""
    print("\n[PHASE 4] USE — trying the stolen credentials...")
    if not key_id or not secret:
        print("    no usable key parsed. stopping.")
        return

    session = boto3.Session(
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name=region,
    )

    # (a) GetCallerIdentity — succeeds for any valid key, always logged.
    sts = session.client("sts")
    for attempt in range(3):
        try:
            ident = sts.get_caller_identity()
            print(f"    whoami -> {ident.get('Arn')}")
            break
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("InvalidClientTokenId", "AccessDenied") and attempt < 2:
                print("    key not active yet, retrying...")
                time.sleep(5)
                continue
            print(f"    sts call result: {code}")
            break

    # (b) Try to expand access — this will be DENIED, but still logged.
    print("    attacker tries to list buckets with the stolen key...")
    try:
        s3 = session.client("s3")
        s3.list_buckets()
        print("    (unexpectedly succeeded)")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        print(f"    denied ({code}) — but AWS just logged this attempt.")

    print("\n[!] The stolen key has now been used. Every use was a deny-all")
    print("    honeytoken, so nothing real happened — but CloudTrail recorded")
    print("    it. Run:  python -m capture.watch   to see CLOUDSNARE catch it.")


def main():
    ap = argparse.ArgumentParser(description="CLOUDSNARE Attacker Simulation")
    ap.add_argument("--step", action="store_true",
                    help="pause between phases (good for live demos)")
    ap.add_argument("--target", help="force a specific decoy bucket name")
    args = ap.parse_args()

    _banner()

    buckets = recon(AWS_REGION)
    _pause(args.step)

    target = args.target or pick_target(buckets)
    if not target:
        print("\n[x] No target found. Deploy decoys first: "
              "python -m deception.deploy")
        return
    _pause(args.step)

    key_id, secret = loot(AWS_REGION, target)
    _pause(args.step)

    use_stolen(AWS_REGION, key_id, secret)


if __name__ == "__main__":
    main()
