# CLOUDSNARE — Speaker Notes (5 Presenters)

**Project:** CLOUDSNARE — Cloud Attack Surface Intelligence & Deception Platform for AWS
**Repo:** https://github.com/itachi2112-Tsukuyomi/cloudsnare
**One-line pitch:** Most security tools scan and wait. CLOUDSNARE sets traps — and catches the attacker.

**Core loop (everyone should know this):**
```
MAP  →  DECEIVE  →  CAPTURE  →  LEARN  →  ACT  →  (repeat)
```

---

## PERSON 1 — Why We Chose This Project & Its Strengths
*~2–3 minutes · sets up everything that follows*

### Open with the problem
- Cloud misconfiguration is the **#1 cause of cloud data breaches**. One wrong setting on an S3 bucket exposes data to the entire internet.
- The average breach takes **~200 days to detect**. Attackers browse your data for months before anyone notices.
- Traditional tools are **reactive**: they scan, produce a report, and wait for a human to read it.

### The three gaps we targeted
1. **You can't tell a scan result from an actual attack.** A scanner says "this bucket is public." It never tells you whether anyone *used* it.
2. **Alert fatigue.** Scanners produce hundreds of findings; teams ignore them.
3. **No attacker intelligence.** Even after a breach: who attacked? what did they want? what should we fix first?

### Why deception is the answer
> If you plant a credential that has **no legitimate use anywhere**, then the moment it appears in your logs, you have a **confirmed breach** — not a maybe.

That is a **zero-false-positive** signal. That is the core idea of the project.

### Our plus points (say these clearly)
- **Zero false positives** — a honeytoken has no legitimate purpose, so any use is real.
- **Detection in minutes, not months.**
- **Complete loop, not just detection** — it finds exposure, traps attackers, learns from them, and fixes the real problems.
- **Human-in-the-loop** — nothing on the real account changes without explicit approval.
- **Least privilege by design** — our scanner uses a read-only IAM policy; remediation uses a separate, narrow write policy.
- **Intelligence-driven priorities** — if attackers target S3, our real S3 exposures get ranked first.

### Honest framing (use if asked "is this original?")
This is a student-scale implementation of **deception-based threat intelligence** — the same category commercial platforms like Wiz and Acalvio operate in. We're not claiming a new idea; we built a working version end-to-end to understand how these systems actually work.

### Hand off
> "So that's *why* deception works. To explain *how* we actually built the trap — over to [Person 2]."

---

## PERSON 2 — Honeytokens & Deception
*~3 minutes · this is the heart of the project*

### Define the terms first
| Term | Meaning | Our version |
|---|---|---|
| **Honeypot** | A fake system built to attract attackers | Decoy S3 buckets |
| **Honeytoken** | A fake credential that alerts when used | Deny-all IAM access keys |
| **Deception tech** | Planting fake assets to detect & study attackers | The whole DECEIVE→CAPTURE→LEARN pipeline |

### How we make decoys believable — two strategies
1. **Mirror decoys** — copy the naming style of your *real* buckets, so attackers can't tell which is which.
2. **Juicy names** — irresistible bait: `prod-db-backup`, `admin-credentials`, `customer-data-export`.

Each decoy is a public S3 bucket containing a file called `credentials.txt`.

### ⭐ THE KEY INSIGHT — emphasise this, it's your strongest technical point

Our first attempt used **random fake keys** that merely *looked* like AWS keys (`AKIA` + 16 characters).

**That failed completely.** Here's why:

> AWS only logs the use of a key that **actually exists** in the account. A random string is rejected before it's ever recorded — so CloudTrail never sees it. Our trap was **invisible**.

The fix: provision a **real IAM user with a deny-all policy**, and plant its **real** access key.

| Property | Result |
|---|---|
| Real key? | Yes — so **CloudTrail logs every use** |
| Can it do anything? | **No** — deny-all policy blocks everything |
| Unique per decoy? | Yes — so we know *exactly which trap* was triggered |

**The one-liner:** *"Harmless, but fully logged."* That's the canary-token pattern.

### The attack chain (walk through it)
1. **RECON** — attacker lists S3 buckets
2. **TARGET** — picks `prod-db-backup` (looks valuable)
3. **LOOT** — downloads `credentials.txt`
4. **USE** — authenticates with the stolen key → **this trips the wire**

Every attempt is **denied** (no damage) but **logged** (full evidence).

### What we captured in our real demo
- **Source IP:** `47.11.x.x`
- **Honeytoken used:** `AKIA…7A4M`
- **Decoy hit:** `cloudsnare-prod-db-backup-5e7b8de4`
- **Actions:** `GetCallerIdentity`, `ListBuckets`
- **Verdict:** CONFIRMED BREACH

### Plus: MITRE ATT&CK mapping
We map each observed action to a real attack technique:
- `ListBuckets` → **T1580** Cloud Infrastructure Discovery
- `GetObject` → **T1530** Data from Cloud Storage
- `GetCallerIdentity` → **T1087** Account Discovery

### Hand off
> "Those traps have to be built and destroyed reliably every time. [Person 3] will explain how Terraform does that."

---

## PERSON 3 — Terraform & Why We Used It
*~2–3 minutes*

### What Terraform is (assume some listeners don't know)
Infrastructure as Code. Instead of clicking through the AWS Console, you **write a file describing what you want**, and Terraform builds it.

### Why we chose it — three concrete reasons
1. **Reproducible** — the same file always produces the same traps. Our demo works identically every time.
2. **Reviewable** — anyone can read the `.tf` file and see exactly what will be created. Important for a *security* project.
3. **Destroyable** — `terraform destroy` removes everything cleanly. **Critical**, because we're deliberately creating public buckets; we must guarantee we can remove them.

> Without Terraform, we'd be hand-creating public buckets and IAM users — and risk leaving real exposures behind after a demo.

### What's clever in our implementation
We don't hand-write the Terraform. **Python generates it at runtime** (`deception/terraform_gen.py`), because decoy names are decided dynamically by mirroring the user's real environment.

### What each decoy creates — 6 resources
```
aws_s3_bucket                    → the decoy bucket (visible bait)
aws_s3_bucket_public_access_block → allow it to be public
aws_s3_bucket_policy             → make it publicly readable
aws_iam_user                     → the honeytoken identity
aws_iam_user_policy              → DENY ALL (makes it harmless)
aws_iam_access_key               → the real, logged key
aws_s3_object                    → credentials.txt holding that key
```

### The flow
```
Python writes decoys.tf
   → terraform init      (download AWS provider)
   → terraform apply     (create traps)
   → terraform output    (return the real key IDs)
   → [key IDs handed to the Capture Engine to watch in CloudTrail]
   → terraform destroy   (clean teardown)
```

**Say this:** the `terraform output` step is essential — it's how the detection half learns *which key IDs to watch for*. Terraform isn't just creating infrastructure, it's feeding our detection pipeline.

### Hand off
> "Now that we're capturing attacks, we needed a way to make sense of the data — [Person 4] on our AI layer."

---

## PERSON 4 — AI & RAG Chatbot
*~3 minutes*

We built **two** AI features.

### 1. SOC Analyst Chat (RAG)

**RAG = Retrieval-Augmented Generation.** Rather than letting an AI answer from general training data — where it might hallucinate — we **ground every answer in our own captured data**.

**Pipeline:**
```
Question: "Who attacked us?"
   1. Build a corpus from CLOUDSNARE's real data
      (captures, intelligence, decoys, scan results, remediations)
   2. TF-IDF retrieval → find the most relevant records
   3. Send ONLY those records to the LLM, with the instruction:
      "Answer using ONLY this context. Do not invent events."
   4. Grounded, factual answer
```

**Why TF-IDF instead of neural embeddings?** Our corpus is small and highly structured — event names, IPs, key IDs. Lexical matching is accurate here and needs zero heavy dependencies. The retriever sits behind a clean `build`/`query` interface, so embeddings can be swapped in later.

**Nice touch — synonym expansion:** analysts don't phrase questions the way data is worded. We map "fix" → "remediation", "trap" → "decoy", "who" → "source, ip".

**Live example from our system:**
> **Q:** "Which IP attacked us and what did they do?"
> **A:** "The attacker was IP 47.11.x.x. They performed GetCallerIdentity and ListBuckets against the decoy cloudsnare-prod-db-backup-5e7b8de4, using honeytoken access key AKIA…7A4M."

**Strong point to make:** it **degrades gracefully**. With no API key it falls back to retrieval-only and still shows the matching records — so the retrieval half is always demonstrable.

### 2. Cloud Assistant (AI Agent)

Lets a non-expert provision AWS resources by just talking.

**Brain-and-hands architecture:**
```
LLM (brain)          → decides WHICH tool to call, asks follow-up questions
Orchestrator (hands) → validates, enforces approval, executes, logs
```

**Three safety layers — this is the part to emphasise:**
1. **Whitelist only.** The LLM can *only* call our four predefined tools. It cannot run arbitrary commands.
2. **Secure by default.** Every bucket it creates is private, encrypted, versioned. Every EC2 instance has no public IP and no inbound rules. **There is no parameter to make it insecure** — we simply never wrote one.
3. **Human confirmation gate.** Read actions run freely; *write* actions always stop and ask.

| Tool | Type |
|---|---|
| `list_buckets`, `list_instances` | READ — no confirmation |
| `create_secure_bucket`, `create_secure_ec2` | WRITE — requires approval |

Every action, including declined ones, goes to an **audit log**.

**Closing line:** *"This is the opposite of the AWS Console, where the default is often insecure and you have to remember to lock things down. Here, security isn't optional — it's structural."*

### Hand off
> "[Person 5] will show how all of these pieces fit together."

---

## PERSON 5 — Architecture
*~3 minutes · you tie the whole talk together*

### Start by restating the loop
```
MAP  →  DECEIVE  →  CAPTURE  →  LEARN  →  ACT  →  (back to MAP)
```
Each stage is **its own Python module** — clean separation of concerns.

### Layer diagram
```
┌──────────────────────────────────────────────────────────┐
│  MAPPER  →  DECEPTION  →  CAPTURE  →  INTELLIGENCE       │
│  scanner     deploy       watch       analyze            │
│  scoring     terraform    engine      report             │
└────────────────────────┬─────────────────────────────────┘
                         ↓
         FastAPI REST Backend  (api/main.py)
   /surface /decoys /attacks /intel /score /remediations
                         ↓
         React SOC Dashboard  (dashboard/index.html)
                         ↓
    REMEDIATION  ·  RAG Chat  ·  Cloud Assistant
                         ↓
   AWS: S3 · EC2 · IAM · CloudTrail · SNS · CloudWatch
```

### Walk the five stages
| Stage | Module | What it does |
|---|---|---|
| **MAP** | `mapper/` | Scans 6 services (S3, EC2-SG, EC2, RDS, Lambda, ELB); saves snapshots; **diffs** them to detect change |
| **DECEIVE** | `deception/` | Generates decoy names + honeytokens, writes Terraform, deploys |
| **CAPTURE** | `capture/` | Reads CloudTrail, correlates events against decoys |
| **LEARN** | `intelligence/` | Time-to-attack, MITRE mapping, timeline, incident report |
| **ACT** | `remediation/` | Recommends fixes, waits for approval, applies, reports |

### The Exposure Score — a nice concrete detail
A single composite **0–100** number (higher = worse):

| Risk | Weight | | Score | Band |
|---|---|---|---|---|
| HIGH | +15 | | 0 | CLEAR |
| MEDIUM | +7 | | 1–24 | LOW |
| LOW | +3 | | 25–49 | MEDIUM |
| | | | 50–74 | HIGH |
| | | | 75–100 | CRITICAL |

**Important nuance:** decoys are **excluded** from the score. They're *deliberately* public, so counting them would make your security posture look falsely terrible.

### Tech stack
**Python · boto3 · Terraform · AWS · FastAPI · React · TF-IDF · LLM**

### Five design principles (strong close)
1. **Least privilege** — read-only scanner policy, separate narrow write policy for remediation
2. **Human-in-the-loop** — no real resource changes without approval
3. **Harmless honeytokens** — powerless, yet fully logged
4. **Decoys are protected** — remediation *never* "fixes" a trap; that would break the deception
5. **No secrets in the repo** — credentials from `aws configure`; `.env`, Terraform state and data are gitignored

### Closing line
> "CLOUDSNARE combines three real security domains — attack surface management, deception, and threat intelligence — into one working loop. Thank you."

---

## LIKELY QUESTIONS (anyone can field these)

**"Is the honeytoken dangerous? Could an attacker use it?"**
No. It has a deny-all IAM policy — every action it attempts is refused. It's real enough for AWS to log, powerless enough to be harmless.

**"What if an attacker realises it's a decoy?"**
Mirror decoys copy the naming of real resources, so they're hard to distinguish. And even recognising a trap means they already touched it — we've detected them either way.

**"Why not just use GuardDuty?"**
GuardDuty detects anomalies and can produce false positives. A honeytoken has no legitimate use, so there's no ambiguity. They're complementary, not competing.

**"How do you avoid false positives from your own activity?"**
We pass our own operator ARN as `self_identifiers` and filter our own decoy access. But honeytoken *use* is never filtered — that's always a real breach signal.

**"Does this cost money?"**
It runs on AWS Free Tier. We also set a CloudWatch billing alarm at $5 as a safety net.

**"What would you do next?"**
Endpoint agents reporting to the same console, an ML classifier for attacker profiling, predictive analytics from snapshot history, and multi-cloud (Azure/GCP) support.

---

## PRE-PRESENTATION CHECKLIST

- [ ] **AWS account is currently empty** — run `demo/step1`, `step2`, `step3` beforehand so there's something to show
- [ ] CloudTrail lags **2–5 minutes** — run the attack (`step4`) *before* you start speaking, so results are ready by Person 2
- [ ] Check the OpenRouter API key still works (Person 4's demo needs it)
- [ ] Open the dashboard at `http://localhost:8000/dashboard`
- [ ] Have the repo open in a browser tab
- [ ] After the session: run all three `demo/cleanup_*` scripts
