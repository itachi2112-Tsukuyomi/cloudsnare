"""
VEILGUARD Intelligence Engine — entry point (the LEARN stage).

Reads the captures (Part 4/5), the decoy state (deploy time), and the
latest Mapper snapshot (real exposures), then produces:
  - a structured intelligence file (data/intelligence.json)
  - a plain-English incident report (data/incident_report.md)

Usage (project root, venv active):
    python -m intelligence.run_intel

The AI report is optional: set ANTHROPIC_API_KEY to enable it, otherwise
a clean template report is produced.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DECOY_STATE_FILE, CAPTURE_FILE, INTEL_FILE, REPORT_FILE,
    SNAPSHOT_DIR, ANTHROPIC_MODEL,
)
from intelligence.analyze import analyze
from intelligence.report import generate_report
from mapper.snapshot import list_snapshots, load_snapshot


def _load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _latest_real_findings():
    snaps = list_snapshots(SNAPSHOT_DIR)
    if not snaps:
        return []
    return load_snapshot(snaps[-1]).get("findings", [])


def main():
    decoy_state = _load(DECOY_STATE_FILE, {"decoys": []})
    captures = _load(CAPTURE_FILE, {"captures": []}).get("captures", [])

    if not captures:
        print("[i] No captures yet. Run the attack + capture first:")
        print("    python -m attacker.simulate")
        print("    python -m capture.watch")
        return

    deployed_at = decoy_state.get("deployed_at")
    real = _latest_real_findings()

    print("[*] Analyzing captures...")
    intel = analyze(deployed_at, captures, real_findings=real)

    with open(INTEL_FILE, "w", encoding="utf-8") as f:
        json.dump(intel, f, indent=2, default=str)

    # ---- print a quick summary ----
    a = intel["attacker"]
    print("\n=== INTELLIGENCE SUMMARY ===")
    print(f"Verdict            : "
          f"{'CONFIRMED BREACH' if a['confirmed_breach'] else 'SUSPICIOUS'}")
    print(f"Time to attack     : {intel['time_to_attack_human']}")
    print(f"Source IP(s)       : {', '.join(a['source_ips']) or 'unknown'}")
    print(f"Decoys hit         : {', '.join(a['decoys_hit']) or 'none'}")
    print(f"Techniques mapped  : {len(intel['techniques'])}")
    print(f"Timeline events    : {len(intel['timeline'])}")

    mode, path = generate_report(intel, decoy_state, ANTHROPIC_MODEL, REPORT_FILE)
    print(f"\n[+] Intelligence saved : {os.path.basename(INTEL_FILE)}")
    print(f"[+] Incident report    : {os.path.basename(path)}  ({mode} mode)")
    print("    Open it to read the full write-up.\n")


if __name__ == "__main__":
    main()
