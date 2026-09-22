"""
CLOUDSNARE Intelligence — analysis (the LEARN stage).

Turns raw captures into insight. Pure functions, unit-tested offline.

Produces:
  - time_to_attack : how long from decoy deployment to first attacker touch
  - timeline       : de-duplicated, ordered story of what the attacker did
  - attacker       : profile (source IPs, actions, decoys hit, severity)
  - techniques     : each action mapped to a MITRE ATT&CK-style tactic
  - priority       : which real exposures to fix first, given what attackers want
"""

from datetime import datetime


# A small, readable map from AWS actions to attacker intent (MITRE-style).
TECHNIQUE_MAP = {
    "ListBuckets": ("Discovery", "T1580 Cloud Infrastructure Discovery"),
    "ListObjects": ("Collection", "T1530 Data from Cloud Storage"),
    "ListObjectsV2": ("Collection", "T1530 Data from Cloud Storage"),
    "GetObject": ("Collection", "T1530 Data from Cloud Storage"),
    "GetCallerIdentity": ("Discovery", "T1087 Account Discovery"),
    "GetBucketPolicy": ("Discovery", "T1580 Cloud Infrastructure Discovery"),
    "AssumeRole": ("Privilege Escalation", "T1548 Abuse Elevation Control"),
}


def _parse_time(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def dedupe(captures):
    """Collapse repeated captures (the watch loop re-reports the same events)."""
    seen, out = set(), []
    for c in captures:
        key = (c.get("type"), c.get("decoy"), c.get("access_key_id"),
               c.get("event_name"), c.get("time"))
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def build_timeline(captures):
    """Ordered list of distinct attacker actions, earliest first."""
    events = dedupe(captures)
    events.sort(key=lambda c: c.get("time") or "")
    return events


def time_to_attack(deployed_at, captures):
    """
    Seconds from decoy deployment to first attacker interaction.
    Returns (seconds, human_string) or (None, 'n/a').
    """
    dep = _parse_time(deployed_at)
    times = [_parse_time(c.get("time")) for c in captures]
    times = [t for t in times if t]
    if not dep or not times:
        return None, "n/a"
    first = min(times)
    delta = (first - dep).total_seconds()
    if delta < 0:
        return None, "n/a"
    if delta < 90:
        human = f"{int(delta)} seconds"
    elif delta < 5400:
        human = f"{delta/60:.1f} minutes"
    else:
        human = f"{delta/3600:.1f} hours"
    return delta, human


def profile_attacker(captures):
    """Summarize who/what: source IPs, action counts, decoys hit, worst severity."""
    events = dedupe(captures)
    ips, actions, decoys = {}, {}, set()
    breach = False
    for c in events:
        ip = c.get("source_ip") or "unknown"
        ips[ip] = ips.get(ip, 0) + 1
        a = c.get("event_name") or "unknown"
        actions[a] = actions.get(a, 0) + 1
        if c.get("decoy"):
            decoys.add(c["decoy"])
        if c.get("severity") == "CONFIRMED_BREACH":
            breach = True
    return {
        "source_ips": ips,
        "actions": actions,
        "decoys_hit": sorted(decoys),
        "confirmed_breach": breach,
        "total_events": len(events),
    }


def map_techniques(captures):
    """Map observed actions to MITRE-style tactics."""
    events = dedupe(captures)
    seen = {}
    for c in events:
        name = c.get("event_name")
        if name in TECHNIQUE_MAP and name not in seen:
            tactic, technique = TECHNIQUE_MAP[name]
            seen[name] = {"action": name, "tactic": tactic, "technique": technique}
    return list(seen.values())


def prioritize(real_findings, captures):
    """
    Feed intelligence back to the map: if attackers are going after a
    resource type (e.g. S3), rank the REAL exposures of that type first.
    real_findings: list from a Mapper snapshot (may be empty).
    """
    # what services did attackers show interest in?
    hot_services = set()
    for c in dedupe(captures):
        name = (c.get("event_name") or "").lower()
        if "bucket" in name or "object" in name:
            hot_services.add("S3")
        if "instance" in name:
            hot_services.add("EC2")

    ranked = []
    for f in real_findings or []:
        # skip our own decoys
        if str(f.get("resource", "")).startswith("cloudsnare"):
            continue
        boost = 1 if f.get("service") in hot_services else 0
        ranked.append({**f, "attacker_interest": bool(boost)})
    ranked.sort(key=lambda x: (not x["attacker_interest"],
                               {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x.get("risk"), 9)))
    return ranked


def analyze(deployed_at, captures, real_findings=None):
    """Run the full analysis and return one intelligence dict."""
    tta_seconds, tta_human = time_to_attack(deployed_at, captures)
    return {
        "time_to_attack_seconds": tta_seconds,
        "time_to_attack_human": tta_human,
        "attacker": profile_attacker(captures),
        "techniques": map_techniques(captures),
        "timeline": build_timeline(captures),
        "priority": prioritize(real_findings, captures),
    }
