"""
CLOUDSNARE Remediation Engine - entry point (the ACT stage).

Human-in-the-loop remediation:
    detect exposure -> recommend fix -> HUMAN APPROVES -> auto-fix -> report

Usage (project root, venv active):
    python -m remediation.remediate                 # show recommendations
    python -m remediation.remediate --approve <id>  # approve one fix
    python -m remediation.remediate --approve-all   # approve all auto-fixable
    python -m remediation.remediate --apply         # apply approved + report

Nothing on your real account changes until you approve AND run --apply.
Decoys are automatically excluded - they're meant to stay public.
"""

import sys
import os
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tabulate import tabulate

from config import (
    AWS_REGION, SNAPSHOT_DIR, DECOY_STATE_FILE,
    REMEDIATION_FILE, REMEDIATION_REPORT,
)
from mapper.snapshot import list_snapshots, load_snapshot
from remediation.engine import (
    load_state, save_state, refresh_state, approve, apply_approved,
)
import json


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _latest_findings():
    snaps = list_snapshots(SNAPSHOT_DIR)
    if not snaps:
        return []
    return load_snapshot(snaps[-1]).get("findings", [])


def _refresh_state():
    """Rebuild recommendations from the latest scan, preserving decisions."""
    findings = _latest_findings()
    decoys = _load_json(DECOY_STATE_FILE, {"decoys": []})
    return refresh_state(findings, decoys, REMEDIATION_FILE)


def _print_state(state):
    recs = state["recommendations"]
    if not recs:
        print("\n[+] No remediable exposures found (decoys are excluded).")
        print("    Your real attack surface is clean.\n")
        return
    rows = []
    for r in recs:
        f = r["finding"]
        rows.append([r["id"], r["status"], f.get("risk"),
                     f.get("resource"), r["recommendation"][:60]])
    print("\n=== REMEDIATION RECOMMENDATIONS ===")
    print(tabulate(rows, headers=["ID", "Status", "Risk", "Resource", "Proposed fix"],
                   tablefmt="github"))
    print("\nApprove with:  python -m remediation.remediate --approve <ID>")
    print("Then apply:    python -m remediation.remediate --apply\n")


def _write_report(state):
    recs = state["recommendations"]
    applied = [r for r in recs if r["status"] == "applied"]
    failed = [r for r in recs if r["status"] == "failed"]
    lines = ["# CLOUDSNARE Remediation Report\n",
             f"Generated: {datetime.now(timezone.utc).isoformat()}\n",
             f"- Applied: {len(applied)}   Failed: {len(failed)}   "
             f"Total tracked: {len(recs)}\n"]
    if applied:
        lines.append("## Fixes applied (human-approved)\n")
        for r in applied:
            lines.append(f"- **{r['finding']['resource']}** - {r['result']}")
        lines.append("")
    if failed:
        lines.append("## Failed\n")
        for r in failed:
            lines.append(f"- {r['finding']['resource']} - {r['result']}")
        lines.append("")
    with open(REMEDIATION_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description="CLOUDSNARE Remediation Engine")
    ap.add_argument("--approve", metavar="ID", help="approve one recommendation")
    ap.add_argument("--approve-all", action="store_true",
                    help="approve all auto-fixable recommendations")
    ap.add_argument("--apply", action="store_true",
                    help="apply approved fixes and write a report")
    args = ap.parse_args()

    state = _refresh_state()

    if args.approve:
        msg = approve(state, args.approve)
        save_state(state, REMEDIATION_FILE)
        print(f"[{args.approve}] {msg}")
        _print_state(state)
        return

    if args.approve_all:
        n = 0
        for r in state["recommendations"]:
            if r["status"] == "pending":
                approve(state, r["id"])
                n += 1
        save_state(state, REMEDIATION_FILE)
        print(f"[+] Approved {n} recommendation(s).")
        _print_state(state)
        return

    if args.apply:
        approved = [r for r in state["recommendations"] if r["status"] == "approved"]
        if not approved:
            print("[i] Nothing approved to apply. Approve fixes first.")
            return
        print(f"[*] Applying {len(approved)} approved fix(es)...")
        outcomes = apply_approved(state, AWS_REGION)
        save_state(state, REMEDIATION_FILE)
        for rid, status, result in outcomes:
            mark = "✓" if status == "applied" else "✗"
            print(f"  {mark} [{rid}] {status}: {result}")
        _write_report(state)
        print(f"\n[+] Remediation report written: "
              f"{os.path.basename(REMEDIATION_REPORT)}\n")
        return

    _print_state(state)


if __name__ == "__main__":
    main()
