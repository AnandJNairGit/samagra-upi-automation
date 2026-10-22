"""
Single-Click Python Runner for Samagra UPI Live Test Seeder
===========================================================
Usage:
  python run_live_seed.py
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_command(cmd_list):
    res = subprocess.run(cmd_list, cwd=BASE_DIR)
    if res.returncode != 0:
        print(f"\n[ERROR] Command failed with return code {res.returncode}")
        sys.exit(res.returncode)

def main():
    print("=" * 75)
    print("[*] SYNCING AND RUNNING LIVE TEST SEEDER IN DOCKER")
    print("=" * 75)

    # 1. Copy script and json to running backend container
    print("[*] Copying seed_live_test.py and live_test_seed.json into Docker container...")
    run_command(["docker", "compose", "cp", "seed_live_test.py", "backend:/tmp/seed_live_test.py"])
    run_command(["docker", "compose", "cp", "live_test_seed.json", "backend:/tmp/live_test_seed.json"])

    # 2. Execute seeder inside container
    print("[*] Executing seeder inside backend container...")
    run_command(["docker", "compose", "exec", "backend", "python", "/tmp/seed_live_test.py"])

if __name__ == "__main__":
    main()
