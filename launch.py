"""
CLOUDSNARE — one-command launcher.

Starts the API server and opens the SOC dashboard in your browser.

Usage (project root, venv active):
    python launch.py

Then the dashboard opens at http://localhost:8000/dashboard
Press Ctrl+C to stop.
"""

import sys
import time
import threading
import webbrowser
import subprocess

URL = "http://localhost:8000/dashboard"


def _open_when_ready():
    # give uvicorn a moment to bind, then open the browser once.
    time.sleep(2.5)
    webbrowser.open(URL)
    print(f"\n[+] Dashboard opening at {URL}")
    print("[+] API docs at http://localhost:8000/docs")
    print("[i] Press Ctrl+C in this window to stop.\n")


def main():
    print("[*] Starting CLOUDSNARE API + dashboard...")
    threading.Thread(target=_open_when_ready, daemon=True).start()
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "api.main:app", "--port", "8000",
        ])
    except KeyboardInterrupt:
        print("\n[+] Stopped.")


if __name__ == "__main__":
    main()
