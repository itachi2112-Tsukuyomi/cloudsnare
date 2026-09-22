"""
CLOUDSNARE Mapper — entry point (the MAP stage).

Run this to scan your AWS account for internet-facing resources.
Each run:
  1. Scans every supported service.
  2. Saves the result as a timestamped snapshot.
  3. Diffs against the previous snapshot and prints what changed.

Usage (from the project root, with venv active):
    python -m mapper.run_mapper

Run it once to get a baseline. Run it again after you change something
(e.g. make a bucket public) to watch the change get detected.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tabulate import tabulate

from config import AWS_REGION, SNAPSHOT_DIR
from mapper.scanner import scan_all
from mapper.snapshot import save_snapshot, diff_latest_two


RISK_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def print_findings(findings):
    if not findings:
        print("\n[+] No internet-facing resources found. Clean surface.\n")
        return
    findings = sorted(findings, key=lambda f: RISK_ORDER.get(f["risk"], 9))
    rows = [[f["risk"], f["service"], f["type"], f["resource"], f["detail"]]
            for f in findings]
    print("\n=== ATTACK SURFACE (internet-facing resources) ===")
    print(tabulate(rows, headers=["Risk", "Service", "Type", "Resource", "Detail"],
                   tablefmt="github"))
    print(f"\nTotal exposed resources: {len(findings)}")


def print_diff(diff, new_path):
    if diff is None:
        print("\n[i] First snapshot saved — no previous scan to compare against.")
        print("    Run the mapper again after a change to see diff detection.\n")
        return

    added, removed, changed = diff["added"], diff["removed"], diff["changed"]
    if not (added or removed or changed):
        print("\n[i] No change since the last scan.\n")
        return

    print("\n=== CHANGES SINCE LAST SCAN ===")
    for f in added:
        print(f"  [+ NEW EXPOSURE]  ({f['risk']}) {f['resource']} — {f['detail']}")
    for f in removed:
        print(f"  [- CLOSED]        {f['resource']} — {f['detail']}")
    for c in changed:
        a, b = c["before"], c["after"]
        print(f"  [~ CHANGED]       {b['resource']}: "
              f"{a['risk']}/{a['detail']} -> {b['risk']}/{b['detail']}")
    print()


def main():
    print(f"[*] Scanning account in region {AWS_REGION} ...")
    findings, errors = scan_all(AWS_REGION)

    path = save_snapshot(findings, errors, SNAPSHOT_DIR)
    print(f"[+] Snapshot saved: {os.path.basename(path)}")

    print_findings(findings)

    if errors:
        print("\n[!] Some services could not be scanned "
              "(often just missing permissions — safe to ignore for those):")
        for e in errors:
            print(f"    - {e['service']}: {e['error'][:120]}")

    diff, _old, _new = diff_latest_two(SNAPSHOT_DIR)
    print_diff(diff, path)


if __name__ == "__main__":
    main()
