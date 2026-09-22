"""
CLOUDSNARE Capture — correlation engine.

Takes raw CloudTrail events and the decoy state, and produces normalized
"capture events": clear records of an attacker touching a trap.

Two kinds of hit, in increasing severity:

  DECOY_ACCESS  — an event references a decoy bucket name (someone is
                  enumerating or reading the trap).

  HONEYTOKEN_USE — an event's accessKeyId matches a planted honeytoken key.
                   This is a CONFIRMED BREACH: those keys exist only inside
                   the decoy, so their use anywhere means the bait was taken.

The correlation logic is pure and deterministic, so it is unit-tested
offline without needing AWS.
"""

import json


def load_decoy_state(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _index_decoys(state):
    """Build fast lookups: honeytoken key id -> decoy, bucket name -> decoy."""
    by_key, by_bucket = {}, {}
    for d in state.get("decoys", []):
        if d.get("real_access_key_id"):
            by_key[d["real_access_key_id"]] = d
        by_bucket[d["bucket"]] = d
    return by_key, by_bucket


def _parse_event(evt):
    """Pull the useful fields out of a CloudTrail event record."""
    try:
        detail = json.loads(evt.get("CloudTrailEvent", "{}"))
    except json.JSONDecodeError:
        detail = {}
    access_key = (detail.get("userIdentity", {}) or {}).get("accessKeyId")
    src_ip = detail.get("sourceIPAddress")
    name = evt.get("EventName") or detail.get("eventName")
    time = evt.get("EventTime")
    # resources referenced (bucket names show up here for S3 events)
    resources = [r.get("ResourceName") for r in evt.get("Resources", [])
                 if r.get("ResourceName")]
    return {
        "event_name": name,
        "time": time.isoformat() if hasattr(time, "isoformat") else str(time),
        "access_key_id": access_key,
        "source_ip": src_ip,
        "resources": resources,
        "raw_detail": detail,
    }


def _actor_arn(detail):
    """Best-effort principal ARN/username from an event's userIdentity."""
    ui = detail.get("userIdentity", {}) or {}
    return ui.get("arn") or ui.get("userName") or ui.get("principalId")


def correlate(events, decoy_state, self_identifiers=None):
    """
    Compare events against decoys. Return a list of capture events,
    most severe first.

    self_identifiers: optional set of ARNs/usernames that represent
    CLOUDSNARE's own operator (e.g. the admin user that deploys decoys).
    DECOY_ACCESS events from these are skipped as self-noise — but
    HONEYTOKEN_USE is NEVER skipped (that's always a real breach signal).
    """
    self_identifiers = set(self_identifiers or [])
    by_key, by_bucket = _index_decoys(decoy_state)
    captures = []

    for evt in events:
        p = _parse_event(evt)

        # 1) Honeytoken use — confirmed breach. Never filtered.
        if p["access_key_id"] and p["access_key_id"] in by_key:
            d = by_key[p["access_key_id"]]
            captures.append({
                "severity": "CONFIRMED_BREACH",
                "type": "HONEYTOKEN_USE",
                "decoy": d["bucket"],
                "token_id": d.get("token_id"),
                "access_key_id": p["access_key_id"],
                "source_ip": p["source_ip"],
                "event_name": p["event_name"],
                "time": p["time"],
            })
            continue

        # 2) Decoy access — someone touched a trap bucket.
        hit_bucket = next((b for b in p["resources"] if b in by_bucket), None)
        if hit_bucket:
            # skip our own deployment / management activity
            actor = _actor_arn(p["raw_detail"])
            if actor and actor in self_identifiers:
                continue
            d = by_bucket[hit_bucket]
            captures.append({
                "severity": "SUSPICIOUS",
                "type": "DECOY_ACCESS",
                "decoy": d["bucket"],
                "token_id": d.get("token_id"),
                "access_key_id": p["access_key_id"],
                "source_ip": p["source_ip"],
                "event_name": p["event_name"],
                "time": p["time"],
            })

    order = {"CONFIRMED_BREACH": 0, "SUSPICIOUS": 1}
    captures.sort(key=lambda c: order.get(c["severity"], 9))
    return captures


def save_captures(captures, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"count": len(captures), "captures": captures}, f, indent=2)
