"""
CLOUDSNARE Remediation — engine (approval state machine).

Turns Mapper findings into remediation recommendations, tracks their
approval status, and applies ONLY the ones a human approved.

State per recommendation:
    pending  -> waiting for a human decision
    approved -> human said yes; ready to apply
    applied  -> fix was performed (with result)
    skipped  -> recommend-only / human declined
    failed   -> apply attempted but errored

Crucially, decoys are excluded here: a decoy is a deliberately public
bucket, so "fixing" it would break the deception. We filter out any
finding whose resource is one of our decoys before recommending anything.
"""

import json
import hashlib

from remediation.actions import handler_for


def _rec_id(finding):
    """Stable id for a recommendation, derived from the finding id."""
    return hashlib.sha1(finding["id"].encode()).hexdigest()[:10]


def _decoy_names(decoy_state):
    return {d["bucket"] for d in (decoy_state or {}).get("decoys", [])}


def build_recommendations(findings, decoy_state):
    """
    Turn findings into recommendations, skipping decoys and unknown types.
    """
    decoys = _decoy_names(decoy_state)
    recs = []
    for f in findings or []:
        # never remediate our own traps
        if f.get("resource") in decoys or str(f.get("resource", "")).startswith("cloudsnare"):
            continue
        h = handler_for(f.get("type"))
        if not h:
            continue
        recs.append({
            "id": _rec_id(f),
            "finding": f,
            "recommendation": h["recommend"](f),
            "auto_fixable": h["auto"],
            "status": "pending",
            "result": None,
        })
    return recs


def load_state(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"recommendations": []}


def save_state(state, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def merge_recommendations(existing, fresh):
    """
    Keep human decisions across re-scans: if a recommendation already exists
    (same id) and was approved/applied/skipped, preserve that status.
    """
    by_id = {r["id"]: r for r in existing.get("recommendations", [])}
    merged = []
    for r in fresh:
        prior = by_id.get(r["id"])
        if prior and prior.get("status") in ("approved", "applied", "skipped"):
            r["status"] = prior["status"]
            r["result"] = prior.get("result")
        merged.append(r)
    return {"recommendations": merged}


def approve(state, rec_id):
    for r in state["recommendations"]:
        if r["id"] == rec_id:
            if not r["auto_fixable"]:
                r["status"] = "skipped"
                r["result"] = "recommend-only (manual action required)"
                return "recommend-only — marked for manual handling"
            r["status"] = "approved"
            return "approved"
    return "not found"


def refresh_state(findings, decoy_state, path):
    """
    Rebuild recommendations from a fresh set of findings, preserving any
    human decisions already made (approved/applied/skipped), and persist.

    This is the single place that keeps the remediation queue in sync with
    the latest MAP scan — call it any time findings change.
    """
    fresh = build_recommendations(findings, decoy_state)
    existing = load_state(path)
    state = merge_recommendations(existing, fresh)
    save_state(state, path)
    return state


def apply_approved(state, region):
    """Apply every approved recommendation. Returns list of outcomes."""
    outcomes = []
    for r in state["recommendations"]:
        if r["status"] != "approved":
            continue
        h = handler_for(r["finding"].get("type"))
        try:
            result = h["apply"](r["finding"], region)
            r["status"] = "applied"
            r["result"] = result
            outcomes.append((r["id"], "applied", result))
        except Exception as e:  # noqa: BLE001
            r["status"] = "failed"
            r["result"] = str(e)
            outcomes.append((r["id"], "failed", str(e)))
    return outcomes
