"""
CLOUDSNARE — central configuration.

This is the ONE place you set account-specific values.
No AWS keys ever go in here. boto3 reads your keys from
`aws configure` (~/.aws/credentials) automatically.
"""

import os

# ---- Region ----------------------------------------------------------------
# Change this to your AWS region. Common ones:
#   ap-south-1  = Mumbai (India)
#   us-east-1   = N. Virginia
# You can also set it via env var CLOUDSNARE_REGION.
AWS_REGION = os.environ.get("CLOUDSNARE_REGION", "ap-south-1")

# ---- Project prefix --------------------------------------------------------
# Every decoy CLOUDSNARE creates gets this prefix so you can always tell
# your traps apart from real resources (and clean them up easily).
DECOY_PREFIX = "cloudsnare-decoy"

# ---- Billing safety --------------------------------------------------------
# The billing alarm fires if estimated monthly charges cross this (USD).
# Keep it low — this is a student project on Free Tier.
BILLING_ALARM_THRESHOLD_USD = 5

# Email that receives the billing + breach alerts.
# Set via env var CLOUDSNARE_ALERT_EMAIL before running setup_billing_alarm.py
# (keeps your real address out of the committed file).
ALERT_EMAIL = os.environ.get("CLOUDSNARE_ALERT_EMAIL", "YOUR_EMAIL@example.com")

# ---- Deception (Part 3) ----------------------------------------------------
# How many decoy buckets to deploy by default.
DECOY_COUNT = 3

# Naming strategy: "mirror" | "juicy" | "both"
#   mirror = copy the naming style of your real resources
#   juicy  = use tempting fixed names (prod-db-backup, ...)
#   both   = mirror when real resources exist, else juicy
DECOY_NAMING = "both"

# Tempting fallback names used when there's nothing to mirror.
JUICY_NAMES = [
    "prod-db-backup",
    "admin-credentials",
    "internal-api-keys",
    "customer-data-export",
    "terraform-state-prod",
]

# Path to the Terraform executable. CLOUDSNARE calls Terraform through
# Python, so this works even if `terraform` isn't on your PATH.
# On Windows this is typically the full path to terraform.exe.
TERRAFORM_BIN = os.environ.get("CLOUDSNARE_TERRAFORM_BIN", r"C:\terraform\terraform.exe")

# ---- Capture (Part 4) ------------------------------------------------------
# How far back (minutes) the capture engine looks in CloudTrail each poll.
CAPTURE_LOOKBACK_MIN = 60

# Poll interval (seconds) for the live watch loop.
CAPTURE_POLL_SECONDS = 30

# SNS topic name reused for breach alerts (same one billing uses is fine,
# but we create a dedicated one for clarity).
BREACH_SNS_TOPIC = "cloudsnare-breach-alerts"

# ---- Intelligence (Part 6) -------------------------------------------------
# The AI incident report is OPTIONAL. If an Anthropic API key is present
# (env var ANTHROPIC_API_KEY), CLOUDSNARE writes an AI summary. Otherwise it
# falls back to a clean template report — so the project never depends on a key.
ANTHROPIC_MODEL = os.environ.get("CLOUDSNARE_AI_MODEL", "claude-sonnet-4-6")

# ---- LLM provider (RAG chat + agent) ---------------------------------------
# CLOUDSNARE's LLM features work with either Anthropic or an OpenAI-compatible
# provider like OpenRouter. Set LLM_PROVIDER to choose.
#   openrouter -> uses OPENROUTER_API_KEY + LLM_MODEL, base URL below
#   anthropic  -> uses ANTHROPIC_API_KEY + ANTHROPIC_MODEL
LLM_PROVIDER = os.environ.get("CLOUDSNARE_LLM_PROVIDER", "openrouter")

# OpenRouter (OpenAI-compatible) settings.
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# The model id. Nemotron 3 Super is free and supports a large context.
LLM_MODEL = os.environ.get(
    "CLOUDSNARE_LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

# ---- Exposure scoring --------------------------------------------------------
# Composite "Exposure Score" (0-100, higher = more exposed) computed from the
# current real findings (decoys excluded). Each finding adds its risk weight;
# the sum is capped at 100. Tune these to change how much a single HIGH vs a
# pile of LOWs moves the needle.
EXPOSURE_SEVERITY_WEIGHTS = {"HIGH": 15, "MEDIUM": 7, "LOW": 3}
EXPOSURE_SCORE_CAP = 100

# ---- Local paths -----------------------------------------------------------
SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "data", "snapshots")
DECEPTION_DIR = os.path.join(os.path.dirname(__file__), "deception")
DECOY_STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "decoys.json")
CAPTURE_FILE = os.path.join(os.path.dirname(__file__), "data", "captures.json")
INTEL_FILE = os.path.join(os.path.dirname(__file__), "data", "intelligence.json")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "data", "incident_report.md")
REMEDIATION_FILE = os.path.join(os.path.dirname(__file__), "data", "remediations.json")
REMEDIATION_REPORT = os.path.join(os.path.dirname(__file__), "data", "remediation_report.md")
ENDPOINTS_FILE = os.path.join(os.path.dirname(__file__), "data", "endpoints.json")
AGENT_AUDIT_LOG = os.path.join(os.path.dirname(__file__), "data", "agent_audit.json")
