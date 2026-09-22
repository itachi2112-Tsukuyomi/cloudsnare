"""
CLOUDSNARE Capture Engine — entry point (the CAPTURE stage).

Reads CloudTrail, correlates against your decoys, and reports any traps
that were touched. A honeytoken hit is a confirmed breach.

Usage (from project root, venv active):
    python -m capture.watch              # one-shot scan of recent history
    python -m capture.watch --loop       # keep watching (poll continuously)

Requires that decoys are deployed (data/decoys.json exists with real
honeytoken key IDs recorded by the deploy step).
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    AWS_REGION, CAPTURE_LOOKBACK_MIN, CAPTURE_POLL_SECONDS,
    DECOY_STATE_FILE, CAPTURE_FILE,
)
from capture.cloudtrail import fetch_recent_events
from capture.engine import load_decoy_state, correlate, save_captures


def _print_captures(captures):
    if not captures:
        print("[i] No decoy interactions found in the lookback window.")
        return
    print("\n" + "=" * 60)
    for c in captures:
        if c["severity"] == "CONFIRMED_BREACH":
            print("  🚨 CONFIRMED BREACH — HONEYTOKEN USED")
            print(f"     decoy      : {c['decoy']}")
            print(f"     key used   : {c['access_key_id']}  (token {c['token_id']})")
            print(f"     source IP  : {c['source_ip']}")
            print(f"     action     : {c['event_name']}  at {c['time']}")
        else:
            print("  ⚠️  SUSPICIOUS — decoy accessed")
            print(f"     decoy      : {c['decoy']}")
            print(f"     source IP  : {c['source_ip']}")
            print(f"     action     : {c['event_name']}  at {c['time']}")
        print("-" * 60)


def _self_identifiers(region):
    """Learn CLOUDSNARE operator's own identity so we can filter self-noise."""
    try:
        import boto3
        ident = boto3.client("sts", region_name=region).get_caller_identity()
        arn = ident.get("Arn", "")
        ids = {arn}
        # also add the bare username (last path segment) for matching
        if "/" in arn:
            ids.add(arn.rsplit("/", 1)[-1])
        return ids
    except Exception:
        return set()


def scan_once():
    if not os.path.exists(DECOY_STATE_FILE):
        print("[X] No decoys deployed (data/decoys.json missing).")
        print("    Deploy decoys first: python -m deception.deploy")
        sys.exit(1)

    state = load_decoy_state(DECOY_STATE_FILE)
    watched = [d.get("real_access_key_id") for d in state.get("decoys", [])
               if d.get("real_access_key_id")]
    print(f"[*] Watching {len(state.get('decoys', []))} decoys "
          f"({len(watched)} live honeytoken keys) in {AWS_REGION}.")
    print(f"[*] Reading CloudTrail (last {CAPTURE_LOOKBACK_MIN} min)...")

    events = fetch_recent_events(AWS_REGION, CAPTURE_LOOKBACK_MIN)
    print(f"[*] {len(events)} events pulled. Correlating against decoys...")

    self_ids = _self_identifiers(AWS_REGION)
    captures = correlate(events, state, self_identifiers=self_ids)
    save_captures(captures, CAPTURE_FILE)
    _print_captures(captures)
    return captures


def main():
    ap = argparse.ArgumentParser(description="CLOUDSNARE Capture Engine")
    ap.add_argument("--loop", action="store_true",
                    help="keep polling CloudTrail continuously")
    args = ap.parse_args()

    if not args.loop:
        scan_once()
        return

    print("[*] Live watch mode. Ctrl+C to stop.\n")
    try:
        while True:
            scan_once()
            print(f"\n[.] Sleeping {CAPTURE_POLL_SECONDS}s...\n")
            time.sleep(CAPTURE_POLL_SECONDS)
    except KeyboardInterrupt:
        print("\n[+] Watch stopped.")


if __name__ == "__main__":
    main()
