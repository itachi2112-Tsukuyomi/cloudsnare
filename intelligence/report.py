"""
CLOUDSNARE Intelligence — incident report generator.

Produces a plain-English incident report from the analysis. Two modes:

  AI mode (optional): if ANTHROPIC_API_KEY is set and the SDK is installed,
    an LLM writes a natural-language summary from the structured facts.
  Template mode (default fallback): a clean, deterministic report built
    directly from the analysis — no API key required.

The project never DEPENDS on the API key; the template report is a
first-class output on its own.
"""

import os
import json


def _template_report(intel, decoy_state):
    a = intel["attacker"]
    lines = []
    lines.append("# CLOUDSNARE Incident Report\n")

    verdict = ("CONFIRMED BREACH" if a["confirmed_breach"]
               else "SUSPICIOUS ACTIVITY")
    lines.append(f"**Verdict:** {verdict}\n")
    lines.append(f"**Time to first attacker interaction:** "
                 f"{intel['time_to_attack_human']}\n")

    lines.append("## Summary\n")
    if a["confirmed_breach"]:
        lines.append(
            "A planted honeytoken credential was used, confirming that an "
            "attacker located a decoy, extracted the credentials inside it, "
            "and attempted to use them. Because honeytoken keys exist only "
            "within decoys and have no legitimate purpose, this is a "
            "high-confidence indicator of compromise.\n")
    else:
        lines.append(
            "One or more decoy resources were accessed by a non-operator "
            "identity. No planted honeytoken has been used yet, so this is "
            "treated as suspicious reconnaissance rather than a confirmed "
            "breach.\n")

    lines.append("## Attacker profile\n")
    ips = ", ".join(f"{ip} ({n} events)" for ip, n in a["source_ips"].items())
    lines.append(f"- Source IP(s): {ips or 'unknown'}")
    lines.append(f"- Decoys touched: {', '.join(a['decoys_hit']) or 'none'}")
    lines.append(f"- Distinct actions observed: {len(a['actions'])}")
    lines.append(f"- Total attacker events: {a['total_events']}\n")

    if intel["techniques"]:
        lines.append("## Techniques (MITRE ATT&CK-style)\n")
        for t in intel["techniques"]:
            lines.append(f"- **{t['action']}** -> {t['tactic']} ({t['technique']})")
        lines.append("")

    lines.append("## Attack timeline\n")
    for e in intel["timeline"]:
        tag = "BREACH" if e["severity"] == "CONFIRMED_BREACH" else "access"
        lines.append(f"- `{e.get('time')}` [{tag}] {e.get('event_name')} "
                     f"on {e.get('decoy')} from {e.get('source_ip')}")
    lines.append("")

    if intel["priority"]:
        lines.append("## Recommended focus (real exposures)\n")
        for p in intel["priority"][:5]:
            flag = " <- attackers are hunting this" if p.get("attacker_interest") else ""
            lines.append(f"- ({p.get('risk')}) {p.get('resource')} "
                         f"— {p.get('detail')}{flag}")
        lines.append("")

    return "\n".join(lines)


def _ai_report(intel, decoy_state, model):
    """Try to generate an AI report. Returns text or None on any failure."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    facts = {
        "verdict": ("CONFIRMED_BREACH" if intel["attacker"]["confirmed_breach"]
                    else "SUSPICIOUS"),
        "time_to_attack": intel["time_to_attack_human"],
        "attacker": intel["attacker"],
        "techniques": intel["techniques"],
        "timeline": intel["timeline"][:20],
    }
    prompt = (
        "You are a cloud security analyst. Write a concise, professional "
        "incident report (Markdown) for a cloud deception platform called "
        "CLOUDSNARE, based ONLY on these structured facts. Be factual and "
        "calm; do not invent details not present.\n\n"
        f"FACTS:\n{json.dumps(facts, indent=2, default=str)}\n\n"
        "Sections: Verdict, Summary, Attacker Profile, Techniques, "
        "Timeline (brief), Recommended Actions."
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        )
    except Exception:
        return None


def generate_report(intel, decoy_state, model, report_path):
    """
    Write the incident report to disk. Uses AI if available, else template.
    Returns (mode, path).
    """
    text = _ai_report(intel, decoy_state, model)
    mode = "AI"
    if not text:
        text = _template_report(intel, decoy_state)
        mode = "template"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(text)
    return mode, report_path
