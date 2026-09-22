"""Install/refresh the launchd job that runs scripts/daily.sh every day at 06:00 local (fetch cost ≈ $0.02–0.05).

    .venv/bin/python scripts/install_daily.py            # install or replace
    .venv/bin/python scripts/install_daily.py --run-now  # also kick it immediately (real fetch + classify + deploy)
    .venv/bin/python scripts/install_daily.py --remove
"""
import os
import plistlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL = "com.finclator.daily"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
DOM = f"gui/{os.getuid()}"

subprocess.run(["launchctl", "bootout", f"{DOM}/{LABEL}"], capture_output=True)
if "--remove" in sys.argv:
    PLIST.unlink(missing_ok=True)
    print("removed", LABEL)
    sys.exit(0)
PLIST.parent.mkdir(parents=True, exist_ok=True)
with PLIST.open("wb") as f:
    plistlib.dump({
        "Label": LABEL,
        "WorkingDirectory": str(ROOT),
        "ProgramArguments": ["/bin/bash", str(ROOT / "scripts" / "daily.sh")],
        "StartCalendarInterval": {"Hour": 6, "Minute": 0},
        "StandardOutPath": str(ROOT / "data" / "daily.log"),
        "StandardErrorPath": str(ROOT / "data" / "daily.log"),
        "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin", "HOME": str(Path.home())},
    }, f)
subprocess.run(["launchctl", "bootstrap", DOM, str(PLIST)], check=True)
out = subprocess.run(["launchctl", "print", f"{DOM}/{LABEL}"], capture_output=True, text=True).stdout
print(out.splitlines()[0] if out else "not loaded?")
if "--run-now" in sys.argv:
    subprocess.run(["launchctl", "kickstart", f"{DOM}/{LABEL}"], check=True)
    print("kicked; tail data/daily.log")
