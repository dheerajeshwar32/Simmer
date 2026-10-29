#!/usr/bin/env python3
"""
Simmer Studio — One-Click Visual Dashboard Launcher
===================================================
Launches the Flask web backend and automatically opens
the interactive compiler dashboard in your web browser.

Usage:
    python run_dashboard.py
    python run_dashboard.py --port 8080
    python run_dashboard.py --no-browser

Authors: N. Dheeraj Eshwar & G. Surya Prakash
Course:  BCSE307P — Compiler Design Lab
"""

import sys
import os
import time
import webbrowser
import threading
import argparse

# Enable UTF-8 encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.system("color")

# Add web directory and venv site-packages to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
venv_site = os.path.join(BASE_DIR, "venv", "Lib", "site-packages")

if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, WEB_DIR)

from web.app import app

# Colors
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
GREEN   = "\033[92m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
YELLOW  = "\033[93m"
WHITE   = "\033[97m"

BANNER = rf"""
{MAGENTA}{BOLD}
   ███████╗██╗███╗   ███╗███╗   ███╗███████╗██████╗ 
   ██╔════╝██║████╗ ████║████╗ ████║██╔════╝██╔══██╗
   ███████╗██║██╔████╔██║██╔████╔██║█████╗  ██████╔╝
   ╚════██║██║██║╚██╔╝██║██║╚██╔╝██║██╔══╝  ██╔══██╗
   ███████║██║██║ ╚═╝ ██║██║ ╚═╝ ██║███████╗██║  ██║
   ╚══════╝╚═╝╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝
{RESET}
{CYAN}{BOLD}  ╔════════════════════════════════════════════════════════════════╗
  ║                 🍲  SIMMER STUDIO DASHBOARD  🍲               ║
  ║      Interactive Web UI for Compiler Design Lab Presentation   ║
  ╚════════════════════════════════════════════════════════════════╝{RESET}
"""


def open_browser_delayed(url):
    """Wait 1 second for the server to bind, then open the browser."""
    time.sleep(1.2)
    print(f"  {GREEN}✓ Opening browser at:{RESET} {BOLD}{url}{RESET}")
    webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(description="Simmer Studio Visual Dashboard Launcher")
    parser.add_argument("--port", type=int, default=5000, help="Port to run web dashboard on (default: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    port = args.port
    url = f"http://127.0.0.1:{port}"

    print(BANNER)
    print(f"  {CYAN}▸ Frontend Pipeline :{RESET} Hand-rolled Lexer → Recursive-Descent Parser → Symbol Table")
    print(f"  {CYAN}▸ Backend Pipeline  :{RESET} Strongly-typed LLVM IR → PassBuilder (-O3) → Native JIT/AOT")
    print(f"  {CYAN}▸ Host Target       :{RESET} Native x86_64 / ARM64")
    print(f"\n  {YELLOW}Starting local dashboard server on:{RESET} {BOLD}{url}{RESET}\n")

    if not args.no_browser:
        threading.Thread(target=open_browser_delayed, args=(url,), daemon=True).start()

    try:
        app.run(host="127.0.0.1", port=port, debug=False)
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}Simmer Studio shutdown cleanly.{RESET}\n")


if __name__ == "__main__":
    main()

