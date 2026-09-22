# CLOUDSNARE - Demo Runbook

A clean, repeatable sequence for presenting the full loop live. Total time
~10 minutes (plus the CloudTrail delay, which you plan around).

## Before the panel arrives

1. Activate the venv and confirm AWS works:
   ```
   myenv\Scripts\Activate.ps1
   python scripts/verify_setup.py
   ```
2. Reset demo state for a clean feed:
   ```
   python scripts/reset_demo.py
   ```
3. Deploy the decoys (so they're live):
   ```
   python -m deception.deploy
   ```
4. Run the attacker now (because CloudTrail has a ~5-15 min delay):
   ```
   python -m attacker.simulate
   ```
5. Start the capture watch loop and leave it running until the breach lands:
   ```
   python -m capture.watch --loop
   ```
   Once you see CONFIRMED BREACH, Ctrl+C.
6. Build the intelligence + report:
   ```
   python -m intelligence.run_intel
   ```
7. Launch the console:
   ```
   python launch.py
   ```

Now the dashboard shows a live CONFIRMED BREACH with a full attack feed.

## The live walkthrough (what to say)

1. **The problem** - cloud misconfigurations expose resources; attackers scan
   for them constantly; companies often don't know.
2. **The dashboard** - "This is the SOC console. Right now it shows a confirmed
   breach." Point to the red banner, the attack feed with source IP and the
   honeytoken key, the Time-to-Attack metric.
3. **Show the loop live** - open a terminal and run the attacker again with
   `--step` to pause between phases:
   ```
   python -m attacker.simulate --step
   ```
   Narrate: recon -> finds the juicy decoy -> steals the credentials -> uses
   them. Explain the used key is a deny-all honeytoken, so nothing real is
   touched, but AWS logs it.
4. **Remediation** - create or point to a real exposure, show the recommendation
   on the dashboard, click Approve, then Apply. Re-scan to show it fixed.
   Emphasise: nothing changes without human approval; decoys are never touched.
5. **The API** - open http://localhost:8000/docs to show the REST layer.

## If asked "is it original?"

"It's a student-scale implementation of cloud deception-based threat
intelligence - the category Wiz and Acalvio work in. I built the full loop to
understand how these systems work. The integration of mapping, deception, and
intelligence into one loop is the interesting part."

## Cleanup after

```
python -m deception.deploy --destroy
```

## Screenshots worth having

- Dashboard in CONFIRMED BREACH state (the hero shot)
- The attacker simulation terminal output
- The /docs API page
- The remediation approve -> apply -> fixed sequence
