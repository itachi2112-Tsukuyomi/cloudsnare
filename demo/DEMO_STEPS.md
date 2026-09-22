# CLOUDSNARE — Demo Steps (Practical Demonstration)

Run each script in order from the **project root** with your venv active.

## The Demo Loop

| Step | Script | What it does |
|------|--------|-------------|
| 1 | `python demo/step1_create_public_bucket.py` | Creates a public S3 bucket (the "misconfiguration" to detect) |
| 2 | `python demo/step2_scan_attack_surface.py` | Scans AWS for all internet-facing resources (MAP) |
| 3 | `python demo/step3_deploy_decoys.py` | Deploys decoy buckets with honeytokens via Terraform (DECEIVE) |
| 4 | `python demo/step4_simulate_attacker.py` | Runs a scripted attacker who steals the fake credentials |
| 5 | `python demo/step5_detect_breach.py` | Reads CloudTrail and detects the honeytoken usage (CAPTURE) |
| 6 | `python demo/step6_analyze_attack.py` | Analyzes the attack: timeline, MITRE mapping, report (LEARN) |
| 7 | `python demo/step7_remediate.py` | Shows fix recommendations, approve and apply (ACT) |
| 8 | `python demo/step8_launch_dashboard.py` | Opens the SOC dashboard in your browser |

## Cleanup (after the demo)

| Script | What it does |
|--------|-------------|
| `python demo/cleanup_destroy_decoys.py` | Tears down all decoy buckets and honeytoken IAM users |
| `python demo/cleanup_destroy_public_bucket.py` | Deletes the public bucket from Step 1 |
| `python demo/cleanup_reset_demo_data.py` | Clears local data files for a fresh run |

## Notes

- Run from the project root: `cd path/to/cloudsnare`
- Activate venv first: `myenv\Scripts\Activate.ps1` (Windows) or `source myenv/bin/activate` (Linux/Mac)
- Step 5 may need a short wait (~2-5 min) for CloudTrail to log the attacker's actions
- Step 7 has sub-commands: run it plain to see recommendations, then with `--approve-all`, then `--apply`
