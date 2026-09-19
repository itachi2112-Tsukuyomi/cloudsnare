# IAM setup for VEILGUARD

`veilguard-scanner-policy.json` is a **least-privilege** policy. It grants only
read/describe access for the services the Mapper scans, plus permission to
create the billing alarm. No write/delete on your real resources.

## Attach it (AWS Console — easiest)

1. IAM → Policies → **Create policy** → JSON tab.
2. Paste the contents of `veilguard-scanner-policy.json`.
3. Name it `VeilguardScannerPolicy` → Create.
4. IAM → Users → your VEILGUARD user → **Add permissions** → attach
   `VeilguardScannerPolicy`.

## Why least-privilege matters here

This is a security project. An evaluator opening your repo should see that even
your *own* tooling follows the principle of least privilege — it can look, but
it can't touch. That's the correct posture and it looks professional.

> Note: The Deception Engine (Part 3) needs additional *write* permissions to
> create decoys via Terraform. Those live in a separate policy we add in Part 3,
> kept apart on purpose so the read-only scanner stays read-only.
