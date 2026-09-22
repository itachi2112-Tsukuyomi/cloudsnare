"""
CLOUDSNARE Agent — CLI chat (the ACT-through-conversation interface).

Talk to your AWS account in plain English. The assistant can list your
resources and create secure-by-default S3 buckets and EC2 instances. It asks
follow-up questions when it needs details, and always asks you to confirm
before creating anything.

Requires:
    pip install anthropic
    set ANTHROPIC_API_KEY=...   (Windows: $env:ANTHROPIC_API_KEY="...")

Usage (project root, venv active):
    python -m agent.chat

Try:
    "I need somewhere to store customer files"
    "list my buckets"
    "spin up a small server called test-box"
Type 'exit' to quit.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AWS_REGION, LLM_PROVIDER, LLM_MODEL, ANTHROPIC_MODEL, AGENT_AUDIT_LOG
from agent.orchestrator import Agent
from agent.llm import available


def _confirm(action_text):
    print(f"\n  ⚠  About to: {action_text}")
    ans = input("     Proceed? (yes/no): ").strip().lower()
    return ans in ("y", "yes")


def main():
    if not available():
        if LLM_PROVIDER == "openrouter":
            print("[!] Set OPENROUTER_API_KEY first (and: pip install openai).")
        else:
            print("[!] Set ANTHROPIC_API_KEY first (and: pip install anthropic).")
        sys.exit(1)

    model = LLM_MODEL if LLM_PROVIDER == "openrouter" else ANTHROPIC_MODEL

    print("=" * 60)
    print("  CLOUDSNARE Cloud Assistant")
    print("  Secure-by-default AWS provisioning through chat.")
    print(f"  Provider: {LLM_PROVIDER}  |  Model: {model}")
    print(f"  Region: {AWS_REGION}   |   type 'exit' to quit")
    print("=" * 60)

    agent = Agent(region=AWS_REGION, model=model,
                  log_path=AGENT_AUDIT_LOG, confirm_fn=_confirm)

    while True:
        try:
            msg = input("\nyou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break
        if msg.lower() in ("exit", "quit"):
            print("bye.")
            break
        if not msg:
            continue
        result = agent.send(msg)
        print(f"\nassistant > {result['reply']}")


if __name__ == "__main__":
    main()
