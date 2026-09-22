# CLOUDSNARE

**Cloud Attack Surface Intelligence & Deception Platform**

CLOUDSNARE continuously **maps** everything an AWS account exposes to the
internet, plants realistic **decoys** across that attack surface, **captures**
every attacker who takes the bait, **learns** from their behaviour, and — with
human approval — **acts** to remediate the real exposures.

```
   MAP  ->  DECEIVE  ->  CAPTURE  ->  LEARN  ->  ACT  ->  (back to MAP)
```

---

## What it does

| Stage | Module | What happens |
|-------|--------|--------------|
| **MAP** | `mapper/` | Scans the AWS account for internet-facing resources (public S3, open ports, exposed APIs, public RDS/Lambda/ELB) and diffs snapshots to detect changes. |
| **DECEIVE** | `deception/` | Deploys decoy resources via Terraform. "Mirror Decoys" copy the real environment's naming so they blend in. Each carries a real-but-powerless honeytoken credential. |
| **CAPTURE** | `capture/` | Reads CloudTrail. Any use of a planted honeytoken key is a high-confidence **confirmed breach**, attributed to the exact decoy and source IP. |
| **LEARN** | `intelligence/` | Computes Time-to-Attack, maps actions to MITRE ATT&CK-style techniques, builds a timeline, and writes a plain-English incident report (AI-optional). |
| **ACT** | `remediation/` | Recommends fixes, waits for human approval, applies them, and reports. Never touches decoys. |
| **API** | `api/` | FastAPI backend exposing every stage over REST, with interactive docs at `/docs`. |
| **Dashboard** | `dashboard/` | A single-file React SOC console — live threat state, attack feed, intelligence, and approve/apply controls. |

An **attacker simulation** (`attacker/`) reproduces a realistic
credential-compromise attack on command, so the whole loop can be demonstrated
reliably.

---

## Honest positioning

CLOUDSNARE is a student-scale implementation of **cloud deception-based threat
intelligence** — the same category commercial platforms like Wiz and Acalvio
operate in. It combines three real security domains (attack surface management,
deception, and threat intelligence) into one working loop. It is not a claim of
a novel idea; it is a working, self-built version to understand how these
systems work end to end.

---

## Security by design

- **Least privilege, split by role.** The scanner uses a read-only IAM policy
  (`iam/cloudsnare-scanner-policy.json`). Remediation uses a *separate*,
  narrowly scoped write policy (`iam/cloudsnare-remediation-policy.json`).
- **Human-in-the-loop.** No real resource is changed without explicit approval.
- **Harmless honeytokens.** Planted keys are deny-all: powerless yet fully
  logged when used.
- **Decoys are protected.** Remediation never "fixes" a decoy — that would
  break the deception.
- **No secrets in the repo.** Credentials come from `aws configure`; `.env`,
  Terraform state, and local data are gitignored.

---

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv myenv
myenv\Scripts\Activate.ps1        # Windows PowerShell
# source myenv/bin/activate       # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure AWS (stored locally, never in code)
aws configure

# 4. Set your email in config.py (ALERT_EMAIL), then verify
python scripts/verify_setup.py
python scripts/setup_billing_alarm.py
```

Requires: an AWS account (Free Tier is fine) with CloudTrail enabled, and
Terraform installed (set its path in `config.py` if not on PATH).

---

## Running the loop

```bash
python -m mapper.run_mapper            # MAP: scan the attack surface
python -m deception.deploy             # DECEIVE: plant decoys (Terraform)
python -m attacker.simulate            # (demo) run the attacker
python -m capture.watch                # CAPTURE: detect the breach
python -m intelligence.run_intel       # LEARN: intel + incident report
python -m remediation.remediate        # ACT: recommend fixes
```

Then launch the console:

```bash
python launch.py                       # starts API + opens the dashboard
# or manually:
# uvicorn api.main:app --port 8000  ->  http://localhost:8000/dashboard
```

Tear down decoys when done:

```bash
python -m deception.deploy --destroy
```

---

## Tech stack

Python, boto3, Terraform, AWS (CloudTrail, S3, IAM, EC2, SNS, CloudWatch),
FastAPI, Uvicorn, React, and an optional LLM for report writing.

## Future work

Endpoint agents reporting to the same SOC console; an ML classifier for
attacker-type profiling; predictive exposure analytics from snapshot history;
multi-cloud (Azure, GCP) coverage.
