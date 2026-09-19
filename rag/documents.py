"""
VEILGUARD RAG — document builder.

RAG retrieves over a corpus of "documents". Here the corpus is VEILGUARD's
own data: every capture, decoy, exposure, remediation, and the intelligence
summary becomes one short text document with metadata.

Turning structured JSON into natural-language sentences matters: it lets the
retriever match a plain-English question ("what did the attacker do?") against
the data, and gives the LLM readable context to answer from.
"""

import os
import json


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _dedupe_captures(caps):
    seen, out = set(), []
    for c in caps:
        k = (c.get("type"), c.get("decoy"), c.get("access_key_id"),
             c.get("event_name"), c.get("time"))
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out


def build_documents(paths):
    """
    Build the document corpus from the data files.

    paths: dict with keys capture, intel, decoys, surface, remediation,
           each a file path (from config).
    Returns: list of {id, text, meta}
    """
    docs = []

    # --- captures (attacker activity) ---
    caps = _dedupe_captures(_load(paths["capture"], {"captures": []}).get("captures", []))
    for i, c in enumerate(caps):
        sev = "CONFIRMED BREACH" if c.get("severity") == "CONFIRMED_BREACH" else "suspicious activity"
        text = (f"{sev}: the action {c.get('event_name')} was performed against "
                f"decoy {c.get('decoy')} from source IP {c.get('source_ip')} "
                f"at {c.get('time')}.")
        if c.get("access_key_id"):
            text += f" It used honeytoken access key {c.get('access_key_id')} (token {c.get('token_id')})."
        docs.append({"id": f"capture-{i}", "text": text,
                     "meta": {"kind": "capture", "severity": c.get("severity")}})

    # --- intelligence summary ---
    intel = _load(paths["intel"], {})
    if intel:
        a = intel.get("attacker", {})
        techs = ", ".join(t.get("action", "") + " (" + t.get("tactic", "") + ")"
                          for t in intel.get("techniques", []))
        text = (f"Intelligence summary: time to first attacker interaction was "
                f"{intel.get('time_to_attack_human')}. "
                f"Confirmed breach: {a.get('confirmed_breach')}. "
                f"Source IPs: {', '.join(a.get('source_ips', {}).keys()) or 'unknown'}. "
                f"Decoys hit: {', '.join(a.get('decoys_hit', [])) or 'none'}. "
                f"Techniques observed: {techs or 'none'}.")
        docs.append({"id": "intel-summary", "text": text, "meta": {"kind": "intel"}})

    # --- decoys ---
    decoys = _load(paths["decoys"], {"decoys": []})
    for i, d in enumerate(decoys.get("decoys", [])):
        text = (f"Decoy {d.get('bucket')} is armed as a trap. It carries honeytoken "
                f"token {d.get('token_id')} with access key {d.get('real_access_key_id')}. "
                f"It is designed to look like a real resource named after {d.get('base')}.")
        docs.append({"id": f"decoy-{i}", "text": text, "meta": {"kind": "decoy"}})

    # --- attack surface (real exposures) ---
    surface = _load(paths["surface_latest"], {"findings": []})
    for i, f in enumerate(surface.get("findings", [])):
        text = (f"Attack surface finding: {f.get('service')} resource {f.get('resource')} "
                f"is exposed ({f.get('detail')}), risk {f.get('risk')}.")
        docs.append({"id": f"surface-{i}", "text": text, "meta": {"kind": "surface"}})

    # --- remediations ---
    rem = _load(paths["remediation"], {"recommendations": []})
    for i, r in enumerate(rem.get("recommendations", [])):
        f = r.get("finding", {})
        text = (f"Remediation for {f.get('resource')}: {r.get('recommendation')} "
                f"Status is {r.get('status')}.")
        if r.get("result"):
            text += f" Result: {r.get('result')}."
        docs.append({"id": f"remediation-{i}", "text": text, "meta": {"kind": "remediation"}})

    return docs
