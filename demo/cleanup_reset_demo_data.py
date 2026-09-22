"""
CLEANUP — Reset all local demo data.

Clears captures, intelligence, remediation state, and snapshots so you
can run a clean end-to-end demo from scratch. Does NOT touch any AWS
resources — only local JSON/MD data files.

Usage:
    python demo/cleanup_reset_demo_data.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.reset_demo import main as reset_demo


def main():
    print("=" * 60)
    print("  CLEANUP: RESET LOCAL DEMO DATA")
    print("=" * 60)
    reset_demo()


if __name__ == "__main__":
    main()
