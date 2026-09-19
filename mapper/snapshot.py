"""
VEILGUARD Mapper — snapshots & change detection.

A snapshot is one scan frozen in time, saved as JSON. Comparing the
newest snapshot against the previous one is what turns a one-off audit
into continuous monitoring: it tells you what just appeared, what
disappeared, and what changed.

This "diff" is the heart of the MAP stage — a new HIGH-risk exposure
showing up between two scans is exactly the signal VEILGUARD exists to
catch.
"""

import os
import json
import glob
from datetime import datetime, timezone


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def save_snapshot(findings, errors, snapshot_dir):
    """Write a snapshot to disk and return its file path."""
    os.makedirs(snapshot_dir, exist_ok=True)
    ts = _timestamp()
    payload = {
        "timestamp": ts,
        "count": len(findings),
        "findings": findings,
        "errors": errors,
    }
    path = os.path.join(snapshot_dir, f"snapshot_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def list_snapshots(snapshot_dir):
    """Return snapshot file paths, oldest first."""
    files = glob.glob(os.path.join(snapshot_dir, "snapshot_*.json"))
    return sorted(files)


def load_snapshot(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff_snapshots(old, new):
    """
    Compare two snapshots.

    Returns a dict:
        added   — findings present now but not before (NEW exposures)
        removed — findings present before but not now (closed/fixed)
        changed — same id, but the detail/risk changed
    """
    old_map = {f["id"]: f for f in old.get("findings", [])}
    new_map = {f["id"]: f for f in new.get("findings", [])}

    added = [f for fid, f in new_map.items() if fid not in old_map]
    removed = [f for fid, f in old_map.items() if fid not in new_map]

    changed = []
    for fid, f in new_map.items():
        if fid in old_map:
            before = old_map[fid]
            if (before.get("detail") != f.get("detail") or
                    before.get("risk") != f.get("risk")):
                changed.append({"before": before, "after": f})

    return {"added": added, "removed": removed, "changed": changed}


def diff_latest_two(snapshot_dir):
    """
    Convenience: diff the two most recent snapshots.

    Returns (diff, old_path, new_path) or (None, ...) if there aren't
    at least two snapshots yet.
    """
    snaps = list_snapshots(snapshot_dir)
    if len(snaps) < 2:
        return None, None, (snaps[-1] if snaps else None)
    old_path, new_path = snaps[-2], snaps[-1]
    diff = diff_snapshots(load_snapshot(old_path), load_snapshot(new_path))
    return diff, old_path, new_path
