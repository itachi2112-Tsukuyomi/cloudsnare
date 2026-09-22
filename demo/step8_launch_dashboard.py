"""
DEMO Step 8 — Launch the SOC dashboard.

Starts the FastAPI backend and opens the React SOC console in your
browser. Shows live threat state, exposure score, attack feed,
intelligence, and remediation controls.

Usage:
    python demo/step8_launch_dashboard.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from launch import main as launch


def main():
    print("=" * 60)
    print("  STEP 8: LAUNCH THE SOC DASHBOARD")
    print("=" * 60)
    launch()


if __name__ == "__main__":
    main()
