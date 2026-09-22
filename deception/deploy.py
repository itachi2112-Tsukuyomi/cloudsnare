"""
CLOUDSNARE Deception Engine — entry point (the DECEIVE stage).

Reads the latest Mapper snapshot to learn your real naming style,
generates Mirror Decoys + honeytokens, writes Terraform, and deploys.

Usage (from project root, venv active):
    python -m deception.deploy            # plan + apply decoys
    python -m deception.deploy --plan     # show what WOULD happen, no changes
    python -m deception.deploy --destroy  # tear everything down

CLOUDSNARE calls Terraform through Python using config.TERRAFORM_BIN, so
this works even if `terraform` isn't on your PATH.
"""

import sys
import os
import json
import argparse
import subprocess
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    AWS_REGION, DECOY_COUNT, DECOY_NAMING, JUICY_NAMES,
    TERRAFORM_BIN, DECEPTION_DIR, DECOY_STATE_FILE, SNAPSHOT_DIR,
)
from deception.mirror import generate_decoy_names
from deception.honeytoken import generate_honeytoken
from deception.terraform_gen import write_terraform
from mapper.snapshot import list_snapshots, load_snapshot


def _real_resource_names():
    """Pull real resource names from the latest Mapper snapshot (for mirroring)."""
    snaps = list_snapshots(SNAPSHOT_DIR)
    if not snaps:
        return []
    latest = load_snapshot(snaps[-1])
    names = []
    for f in latest.get("findings", []):
        # skip our own decoys if they show up
        if f.get("resource", "").startswith("cloudsnare"):
            continue
        names.append(f.get("resource", ""))
    return [n for n in names if n]


def _unique_suffix():
    # S3 bucket names are globally unique; add a short random suffix.
    return uuid.uuid4().hex[:8]


def _terraform(*args):
    """Run a terraform command in the deception dir; stream output."""
    cmd = [TERRAFORM_BIN, *args]
    print(f"    $ terraform {' '.join(args)}")
    result = subprocess.run(cmd, cwd=DECEPTION_DIR)
    if result.returncode != 0:
        print(f"[X] terraform {args[0]} failed (exit {result.returncode}).")
        sys.exit(result.returncode)


def _terraform_outputs():
    """Read `terraform output -json` and return the parsed dict."""
    cmd = [TERRAFORM_BIN, "output", "-json"]
    result = subprocess.run(cmd, cwd=DECEPTION_DIR,
                            capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def _merge_real_keys_into_state():
    """
    After apply, Terraform knows the REAL honeytoken access key IDs.
    Pull them from outputs and record them in decoys.json so the Capture
    engine knows which key IDs to watch for in CloudTrail.
    """
    outputs = _terraform_outputs()
    if not outputs:
        return
    # outputs look like {"honeytoken_1": {"value": {"bucket":..,"token_id":..,"access_key_id":..}}, ...}
    by_bucket = {}
    for _k, v in outputs.items():
        val = v.get("value", {})
        if "bucket" in val and "access_key_id" in val:
            by_bucket[val["bucket"]] = val["access_key_id"]

    if not os.path.exists(DECOY_STATE_FILE):
        return
    with open(DECOY_STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    for d in state.get("decoys", []):
        if d["bucket"] in by_bucket:
            d["real_access_key_id"] = by_bucket[d["bucket"]]
    with open(DECOY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print("[+] Recorded real honeytoken key IDs for capture watching.")


def _check_terraform_bin():
    if not os.path.exists(TERRAFORM_BIN):
        print(f"[X] Terraform not found at: {TERRAFORM_BIN}")
        print("    Set the correct path in config.py (TERRAFORM_BIN) or via")
        print("    the CLOUDSNARE_TERRAFORM_BIN environment variable.")
        sys.exit(1)


def build_decoys():
    """Generate decoy names + honeytokens and write Terraform. Returns state dict."""
    real = _real_resource_names()
    base_names = generate_decoy_names(real, DECOY_COUNT, DECOY_NAMING, JUICY_NAMES)

    decoys = []
    for base in base_names:
        # ensure global-uniqueness for the actual bucket name
        bucket = f"cloudsnare-{base}-{_unique_suffix()}"[:63].lower()
        token = generate_honeytoken(bucket)
        decoys.append({"bucket": bucket, "base": base, "token": token})

    write_terraform(DECEPTION_DIR, AWS_REGION, decoys)

    state = {
        "region": AWS_REGION,
        "naming": DECOY_NAMING,
        "mirrored_from_real": bool(real),
        "deployed_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "decoys": [
            {
                "bucket": d["bucket"],
                "base": d["base"],
                "token_id": d["token"]["token_id"],
                "fake_access_key": d["token"]["fake_access_key"],
                "honeytoken_file": d["token"]["file_name"],
            }
            for d in decoys
        ],
    }
    os.makedirs(os.path.dirname(DECOY_STATE_FILE), exist_ok=True)
    with open(DECOY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    return state


def print_state(state):
    print("\n=== DECOYS ===")
    print(f"Naming strategy : {state['naming']}"
          f"  (mirrored from real resources: {state['mirrored_from_real']})")
    for d in state["decoys"]:
        print(f"  - {d['bucket']}")
        print(f"      honeytoken file : {d['honeytoken_file']}")
        print(f"      fake access key : {d['fake_access_key']}  (token {d['token_id']})")
    print()


def main():
    ap = argparse.ArgumentParser(description="CLOUDSNARE Deception Engine")
    ap.add_argument("--plan", action="store_true", help="preview only, no changes")
    ap.add_argument("--destroy", action="store_true", help="tear down all decoys")
    args = ap.parse_args()

    _check_terraform_bin()

    if args.destroy:
        print("[*] Destroying all decoys ...")
        _terraform("init", "-input=false")
        _terraform("destroy", "-auto-approve")
        if os.path.exists(DECOY_STATE_FILE):
            os.remove(DECOY_STATE_FILE)
        print("[+] All decoys removed. Attack surface is clean of traps.\n")
        return

    print("[*] Building Mirror Decoys from your attack surface ...")
    state = build_decoys()
    print_state(state)

    print("[*] Initializing Terraform ...")
    _terraform("init", "-input=false")

    if args.plan:
        print("[*] Planning (no changes will be made) ...")
        _terraform("plan")
        print("\n[i] Plan only. Re-run without --plan to actually deploy.\n")
        return

    print("[*] Deploying decoys to AWS ...")
    _terraform("apply", "-auto-approve")
    _merge_real_keys_into_state()
    print("\n[+] Decoys deployed. Run the Mapper now — it should see them as")
    print("    public buckets, blended into your attack surface.")
    print("[!] Remember: `python -m deception.deploy --destroy` cleans them up.\n")


if __name__ == "__main__":
    main()
