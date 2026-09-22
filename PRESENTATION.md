# CLOUDSNARE — Project Presentation

---

## Part 1: The Real-World Problem & How CLOUDSNARE Solves It

### The Problem

Every organization using cloud services (AWS, Azure, GCP) faces a critical security gap:

- **Misconfigured resources are everywhere.** A single misconfigured S3 bucket or an open security group port can expose sensitive data to the entire internet. According to industry reports, cloud misconfigurations are the #1 cause of data breaches.

- **Traditional security tools are reactive.** They scan, generate a report, and wait. By the time someone reads the report, an attacker may have already found and exploited the exposure.

- **You don't know when you've been breached.** An attacker can silently enumerate your cloud resources, find a misconfigured bucket, download your data, and leave — without triggering any alert. You only find out weeks later when the data shows up on the dark web.

- **No intelligence about the attacker.** Even if you detect a breach, traditional tools can't tell you: Who attacked? What did they want? How fast did they find the vulnerability? Which exposures should you fix first?

### How CLOUDSNARE Solves It

CLOUDSNARE takes a fundamentally different approach — **deception-based threat intelligence**:

1. **Don't just scan — set traps.** Instead of only scanning for vulnerabilities, CLOUDSNARE plants realistic-looking decoy resources (fake buckets with fake credentials) across your AWS account. These blend in with your real resources.

2. **If a trap is touched, you know you're breached.** The fake credentials (honeytokens) have ZERO legitimate use. If they appear anywhere in AWS CloudTrail logs, it is a 100% confirmed breach — no false positives.

3. **Learn from the attacker.** CLOUDSNARE captures the attacker's IP address, actions, timing, and maps their behavior to MITRE ATT&CK techniques. This intelligence tells you what attackers are going after — so you fix those things first.

4. **Close the loop with human-approved remediation.** CLOUDSNARE recommends fixes (block public access, restrict security groups) and applies them — but only after a human approves. Nothing changes without your consent.

### The 5-Stage Loop

```
MAP  →  DECEIVE  →  CAPTURE  →  LEARN  →  ACT  →  (back to MAP)
```

| Stage | What happens |
|-------|-------------|
| **MAP** | Scan the AWS account — find every resource exposed to the internet |
| **DECEIVE** | Deploy realistic decoy resources with hidden honeytokens |
| **CAPTURE** | Monitor CloudTrail — detect any attacker touching the traps |
| **LEARN** | Analyze the attack: who, what, when, how, and what to fix first |
| **ACT** | Recommend and apply fixes (with human approval) |

### Why This Matters

- Cloud breaches cost companies millions of dollars
- The average time to detect a breach is 197 days (IBM Cost of a Data Breach Report)
- CLOUDSNARE reduces detection time to minutes — the moment an attacker touches a trap
- Zero false positives — a honeytoken has no legitimate use, so any usage is a real breach

---

## Part 2: Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLOUDSNARE Architecture                      │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  MAPPER   │───>│ DECEPTION│───>│ CAPTURE  │───>│  INTEL   │  │
│  │ scanner.py│    │ deploy.py│    │ watch.py │    │analyze.py│  │
│  │ scoring.py│    │ terra*.py│    │ engine.py│    │report.py │  │
│  └─────┬─────┘    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘  │
│        │               │               │               │        │
│        v               v               v               v        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              FastAPI REST Backend (api/main.py)           │   │
│  │     /surface  /decoys  /attacks  /intel  /score  /status │   │
│  └──────────────────────────────┬────────────────────────────┘   │
│                                 │                                │
│                                 v                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          React SOC Dashboard (dashboard/index.html)       │   │
│  │   Exposure Gauge | Attack Feed | Intel | Remediation     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │
│  │REMEDIATION│    │ RAG Chat │    │  Agent   │                   │
│  │ engine.py │    │  chat.py │    │orchestr. │                   │
│  │ actions.py│    │retriever │    │ tools.py │                   │
│  └──────────┘    └──────────┘    └──────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            v
              ┌──────────────────────────┐
              │        AWS Cloud          │
              │  S3 | EC2 | IAM | SNS    │
              │  CloudTrail | CloudWatch  │
              └──────────────────────────┘
```

### Project Structure

```
cloudsnare/
├── config.py                  # Central configuration (region, thresholds, paths)
├── launch.py                  # One-command launcher (API + dashboard)
│
├── mapper/                    # STAGE 1: MAP
│   ├── scanner.py             #   Scans S3, EC2, RDS, Lambda, ELB
│   ├── scoring.py             #   Computes Exposure Score (0-100)
│   ├── snapshot.py            #   Save/load/diff scan snapshots
│   └── run_mapper.py          #   CLI entry point
│
├── deception/                 # STAGE 2: DECEIVE
│   ├── deploy.py              #   Orchestrates decoy deployment
│   ├── terraform_gen.py       #   Generates Terraform IaC
│   ├── decoys.tf              #   Generated Terraform file
│   ├── honeytoken.py          #   Generates fake credentials
│   └── mirror.py              #   Copies real naming patterns
│
├── capture/                   # STAGE 3: CAPTURE
│   ├── watch.py               #   Polls CloudTrail for trap triggers
│   ├── cloudtrail.py          #   Reads CloudTrail events
│   └── engine.py              #   Correlates events with decoys
│
├── intelligence/              # STAGE 4: LEARN
│   ├── analyze.py             #   Time-to-attack, MITRE mapping, profiling
│   ├── report.py              #   AI or template incident report
│   └── run_intel.py           #   CLI entry point
│
├── remediation/               # STAGE 5: ACT
│   ├── remediate.py           #   CLI: recommend, approve, apply
│   ├── engine.py              #   State machine (pending→approved→applied)
│   └── actions.py             #   Actual fix functions (block public access, etc.)
│
├── api/                       # REST API
│   ├── main.py                #   FastAPI app with all endpoints
│   └── models.py              #   Pydantic response models
│
├── dashboard/                 # Frontend
│   └── index.html             #   Single-file React SOC console
│
├── rag/                       # RAG Chatbot
│   ├── chat.py                #   Full RAG pipeline
│   ├── retriever.py           #   TF-IDF vector search
│   └── documents.py           #   Builds corpus from CLOUDSNARE data
│
├── agent/                     # AI Cloud Assistant
│   ├── orchestrator.py        #   Brain-and-hands agent loop
│   ├── tools.py               #   Secure-by-default AWS actions
│   ├── schemas.py             #   Tool definitions for the LLM
│   └── llm.py                 #   LLM provider abstraction
│
├── attacker/                  # Demo Adversary
│   └── simulate.py            #   Scripted attack chain
│
├── demo/                      # Step-by-step demo scripts
│   ├── step1_create_public_bucket.py
│   ├── step2_scan_attack_surface.py
│   ├── step3_deploy_decoys.py
│   ├── step4_simulate_attacker.py
│   ├── step5_detect_breach.py
│   ├── step6_analyze_attack.py
│   ├── step7_remediate.py
│   ├── step8_launch_dashboard.py
│   ├── cleanup_destroy_decoys.py
│   ├── cleanup_destroy_public_bucket.py
│   └── cleanup_reset_demo_data.py
│
├── scripts/                   # Utility scripts
├── iam/                       # IAM policy files (least privilege)
├── tests/                     # Unit tests
└── data/                      # Runtime data (gitignored)
```

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Language | Python 3 | Widely used, great AWS SDK support |
| AWS SDK | boto3 | Official AWS SDK for Python |
| Infrastructure | Terraform | Industry-standard IaC, reproducible, destroyable |
| Backend API | FastAPI | Auto-generated docs, async support, Pydantic validation |
| Frontend | React (single-file) | Interactive SOC dashboard, no build step needed |
| AI (optional) | Claude / OpenRouter | Incident reports and RAG chat |
| Cloud Services | S3, EC2, IAM, CloudTrail, SNS, CloudWatch | Core AWS services |

### Security Design Principles

1. **Least Privilege** — Scanner uses read-only IAM policy; remediation uses a separate narrow write policy
2. **Human-in-the-Loop** — No real resource is changed without explicit human approval
3. **No Secrets in Code** — AWS credentials come from `aws configure`, alert email from env var
4. **Decoy Protection** — Remediation engine automatically skips decoys (they're supposed to be public)
5. **Secure-by-Default Agent** — The AI agent can only create private, encrypted, locked-down resources

---

## Part 3: Terraform (Infrastructure as Code)

### What is Terraform?

Terraform is an Infrastructure as Code (IaC) tool. Instead of clicking around the AWS Console to create resources, you write a `.tf` file describing what you want, and Terraform creates it all automatically. The key benefits:

- **Reproducible** — same file always creates the same infrastructure
- **Reviewable** — you can read the code to see exactly what will be created
- **Destroyable** — `terraform destroy` tears everything down cleanly

### How CLOUDSNARE Uses Terraform

CLOUDSNARE generates Terraform code dynamically to deploy decoy traps. The Python code in `deception/terraform_gen.py` writes a `decoys.tf` file, then runs Terraform to deploy it.

### What Each Decoy Creates (in Terraform)

For EACH decoy, Terraform creates 5 AWS resources:

```
1. aws_s3_bucket         → The decoy bucket (the visible bait)
2. aws_s3_bucket_policy   → Makes the bucket publicly readable
3. aws_iam_user           → A REAL IAM user (the honeytoken identity)
4. aws_iam_user_policy    → Deny-all policy (the user can't do ANYTHING)
5. aws_iam_access_key     → Real AWS access key (logged by CloudTrail)
6. aws_s3_object          → credentials.txt containing the real key
```

### The Terraform Flow

```
Python generates decoys.tf
        │
        v
terraform init        → Download AWS provider plugin
        │
        v
terraform apply       → Create all resources in AWS
        │
        v
terraform output      → Return the real access key IDs
        │                (so Capture Engine knows what to watch)
        v
terraform destroy     → Clean removal when demo is done
```

### Why a Real IAM Key (Not Just a Random String)?

This is the critical design decision:

- A **random fake string** (like `AKIAXXXXXXXXXXXXXXXX`) would look like a key, but AWS would reject it immediately and **never log it in CloudTrail**. We'd have no way to detect the attacker used it.

- A **real IAM access key** with a **deny-all policy** is the best of both worlds:
  - It is a real, valid AWS key → CloudTrail logs every attempt to use it
  - The deny-all policy means it **cannot do anything** → completely harmless
  - When the attacker uses it, we see exactly who, when, from where, and what they tried

### Example Generated Terraform

```hcl
resource "aws_s3_bucket" "decoy_1" {
  bucket        = "cloudsnare-prod-db-backup-a1b2c3d4"
  force_destroy = true
  tags = { cloudsnare = "decoy", token_id = "abc123def456" }
}

resource "aws_iam_user" "decoy_1" {
  name = "cloudsnare-prod-db-backup-a1b2c3d4"
  tags = { cloudsnare = "honeytoken" }
}

resource "aws_iam_user_policy" "decoy_1" {
  name   = "deny-all"
  user   = aws_iam_user.decoy_1.name
  policy = jsonencode({
    Statement = [{ Effect = "Deny", Action = "*", Resource = "*" }]
  })
}

resource "aws_s3_object" "decoy_1_token" {
  bucket  = aws_s3_bucket.decoy_1.id
  key     = "credentials.txt"
  content = <<-EOT
    # Production credentials - DO NOT SHARE
    aws_access_key_id = ${aws_iam_access_key.decoy_1.id}
    aws_secret_access_key = ${aws_iam_access_key.decoy_1.secret}
  EOT
}
```

---

## Part 4: Honeypot, Honeytokens & Deception Technology

### Key Concepts

| Term | What it is | CLOUDSNARE Example |
|------|-----------|-------------------|
| **Honeypot** | A fake system designed to attract attackers | Our decoy S3 buckets with tempting names |
| **Honeytoken** | A fake credential that triggers an alert when used | The deny-all IAM access keys planted inside decoys |
| **Deception Technology** | The practice of planting fake assets to detect and study attackers | The entire DECEIVE→CAPTURE→LEARN pipeline |
| **Canary Token** | A specific type of honeytoken that "calls home" when accessed | Our keys use CloudTrail as the "call home" mechanism |

### How the Deception Works (Step by Step)

**Step 1: Generate decoy names that blend in**

CLOUDSNARE uses two naming strategies:
- **Mirror** — copies the naming pattern of your REAL buckets (e.g., if you have `myapp-logs`, it creates `cloudsnare-myapp-backup-a1b2c3d4`)
- **Juicy names** — uses irresistible names attackers can't ignore: `prod-db-backup`, `admin-credentials`, `customer-data-export`

**Step 2: Generate honeytokens**

For each decoy, `honeytoken.py` creates:
- A fake AWS access key shaped like `AKIA` + 16 random characters (the real AWS key format)
- A fake secret key (40 random characters)
- A `credentials.txt` file containing them (looks exactly like a real credentials file)

**Step 3: Deploy via Terraform**

Terraform creates each decoy as a public S3 bucket + deny-all IAM user + real access key. The `credentials.txt` inside the bucket contains the REAL (but powerless) key.

**Step 4: The attacker finds the bait**

The attacker enumerates S3 buckets, sees `prod-db-backup`, opens it, finds `credentials.txt`, and thinks they've hit gold.

**Step 5: The attacker uses the stolen key**

The attacker tries to authenticate with the stolen key (e.g., `sts:GetCallerIdentity`, `s3:ListBuckets`). Every call is:
- **Denied** (deny-all policy) — so no damage occurs
- **Logged by CloudTrail** — with the exact key ID, source IP, action, and timestamp

**Step 6: CLOUDSNARE detects the breach**

The Capture Engine (`capture/engine.py`) reads CloudTrail and correlates:
- **DECOY_ACCESS** (suspicious) — someone touched a decoy bucket
- **HONEYTOKEN_USE** (confirmed breach) — someone used the planted key

This is a **zero false positive** detection: the key has no legitimate use, so ANY usage is a confirmed breach.

### The Attack Chain (Demo)

```
ATTACKER                                    CLOUDSNARE
   │                                            │
   │  1. ListBuckets (recon)                    │
   │─────────────────────────────>  sees decoys │
   │                                            │
   │  2. Picks "prod-db-backup"                 │
   │─────────────────────────────>  trap bucket │
   │                                            │
   │  3. GetObject credentials.txt              │
   │─────────────────────────────>  gets key    │
   │                                            │
   │  4. Uses stolen key (GetCallerIdentity)    │
   │──────────────────┐                         │
   │                  │  CloudTrail logs it      │
   │                  └────────────────────>  CAPTURED!
   │                                            │
   │  DENIED (deny-all)                         │  Source IP: 203.0.113.42
   │  No damage done                            │  Key: AKIA...
   │                                            │  Decoy: prod-db-backup
   │                                            │  Time: 3m 22s after deployment
```

### MITRE ATT&CK Mapping

CLOUDSNARE maps each observed attacker action to real-world attack techniques:

| AWS API Call | MITRE Tactic | MITRE Technique |
|-------------|--------------|-----------------|
| ListBuckets | Discovery | T1580 Cloud Infrastructure Discovery |
| GetObject | Collection | T1530 Data from Cloud Storage |
| GetCallerIdentity | Discovery | T1087 Account Discovery |
| GetBucketPolicy | Discovery | T1580 Cloud Infrastructure Discovery |
| AssumeRole | Privilege Escalation | T1548 Abuse Elevation Control |

### Exposure Score

CLOUDSNARE computes a composite **Exposure Score** (0-100) from all real findings:

| Risk Level | Weight per Finding |
|-----------|-------------------|
| HIGH | +15 points |
| MEDIUM | +7 points |
| LOW | +3 points |

| Score Range | Band | Meaning |
|------------|------|---------|
| 0 | CLEAR | No exposures detected |
| 1-24 | LOW | Minor issues |
| 25-49 | MEDIUM | Attention needed |
| 50-74 | HIGH | Significant risk |
| 75-100 | CRITICAL | Immediate action required |

---

## Part 5: AI Chat, RAG Chatbot & Cloud Assistant

### Two AI Features in CLOUDSNARE

CLOUDSNARE includes two AI-powered components:

### 1. RAG Chatbot (rag/)

**RAG = Retrieval-Augmented Generation**

Instead of asking an AI to answer from its general training data (which might be wrong or outdated), RAG grounds the AI's answer in YOUR actual data.

**How it works:**

```
Analyst asks: "Who attacked us?"
        │
        v
Step 1: Build corpus from CLOUDSNARE's real data
        (captures, intelligence, decoy state, scan results)
        │
        v
Step 2: TF-IDF retrieval — find the most relevant records
        (e.g., capture events showing source IP 203.0.113.42)
        │
        v
Step 3: Send retrieved records + question to the LLM
        "Answer ONLY using this context. Don't invent events."
        │
        v
Step 4: LLM gives a grounded, factual answer
        "Your decoy prod-db-backup was accessed from IP 203.0.113.42
         at 14:32 UTC. The attacker used honeytoken AKIA... which
         constitutes a confirmed breach."
```

**Why TF-IDF (not neural embeddings)?**

The corpus is small and structured (event names, IPs, decoy names), so lexical matching with TF-IDF is accurate and has zero external dependencies. The retriever has a clean interface (`build` / `query`), so neural embeddings can be swapped in later.

**Synonym expansion** bridges the gap between how analysts ask questions and how the data is worded:
- "Who attacked?" → searches for "breach", "source", "honeytoken"
- "What traps were hit?" → searches for "decoy", "honeytoken"
- "How fast?" → searches for "time", "minutes", "seconds"

**Works without an API key:** If no LLM API key is set, the chatbot falls back to retrieval-only mode — it returns the relevant records directly, so retrieval is always demonstrable.

### 2. Cloud Assistant Agent (agent/)

An **autonomous LLM agent** that helps users provision AWS resources securely through conversation.

**Brain-and-Hands Architecture:**

```
┌──────────────────────────────────┐
│          LLM (Brain)             │
│  Reads conversation + tool menu  │
│  Decides which tool to call      │
│  Asks follow-up questions        │
└───────────────┬──────────────────┘
                │  tool_call(name, params)
                v
┌──────────────────────────────────┐
│      Orchestrator (Hands)        │
│  Validates the tool call         │
│  WRITE actions → asks human      │
│  Executes via boto3              │
│  Logs to audit trail             │
└──────────────────────────────────┘
```

**Safety Layers (the key design):**

1. **Whitelist-only tools** — The LLM can ONLY call tools defined in `tools.py`. There is no way to run arbitrary commands.

2. **Secure-by-default** — Every resource the agent creates is private, encrypted, and locked down. There is literally no parameter to make a bucket public or open a port.

3. **Human confirmation gate** — WRITE operations (create bucket, launch instance) always ask the human first. READ operations (list buckets, list instances) proceed automatically.

4. **Audit log** — Every action (including declined ones) is logged with timestamp, tool name, parameters, and result.

**Available Tools:**

| Tool | Type | What it does |
|------|------|-------------|
| `list_buckets` | READ (safe) | Lists S3 buckets in the account |
| `list_instances` | READ (safe) | Lists EC2 instances |
| `create_secure_bucket` | WRITE (needs approval) | Creates a private, encrypted, versioned S3 bucket |
| `create_secure_ec2` | WRITE (needs approval) | Launches a locked-down EC2 instance (no public IP, no inbound rules) |

**Example Conversation:**

```
User: "I need a place to store my project files"

Agent: "I'll create a private S3 bucket for you. What would you
        like to name it?"

User: "project-files-2024"

Agent: "I'll create a PRIVATE, encrypted, versioned S3 bucket
        named 'project-files-2024'. Confirm?"

User: "Yes"

Agent: "Done! Bucket 'project-files-2024' created — private,
        encrypted (AES256), versioned, public access fully blocked."
```

**Why "secure-by-default" matters:**

The agent CANNOT create an insecure resource even if someone asks it to. There is no "make it public" parameter. This is the opposite of the AWS Console, where the default is often insecure and users have to manually lock things down.

**Multi-provider support:** Works with either Anthropic (Claude) or any OpenAI-compatible provider (like the free Nemotron model via OpenRouter).

---

## Part 6: Thank You

### What We Built

CLOUDSNARE is a working, end-to-end cloud security platform that:

- **Scans** AWS for internet-facing resources across 6 services
- **Deploys** realistic decoy traps using Terraform (Infrastructure as Code)
- **Detects** attackers with zero false positives using honeytokens
- **Analyzes** attacker behavior with MITRE ATT&CK mapping
- **Remediates** exposures with human-approved automated fixes
- **Visualizes** everything in a real-time SOC dashboard
- **Answers** security questions via a grounded RAG chatbot
- **Assists** with secure cloud provisioning via an AI agent

### Technologies Used

Python, boto3, Terraform, AWS (S3, EC2, IAM, CloudTrail, SNS, CloudWatch),
FastAPI, React, TF-IDF, LLM (Claude/OpenRouter)

### Key Takeaways

1. **Deception > Detection** — Don't just scan for problems. Set traps. If someone touches a trap, it's a guaranteed breach.
2. **Infrastructure as Code** — Terraform makes decoy deployment reproducible, reviewable, and cleanly removable.
3. **Human-in-the-Loop** — Automation is powerful, but critical decisions (like modifying production resources) should always require human approval.
4. **Secure by Default** — The AI agent proves that you can make tools that are impossible to misuse, not just tools that warn you.
5. **Intelligence-Driven Remediation** — Fix what attackers are actually targeting first, not just what looks worst on paper.

### GitHub Repository

https://github.com/itachi2112-Tsukuyomi/cloudsnare

### Thank You!
