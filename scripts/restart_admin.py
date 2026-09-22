"""Restart the local admin (launchd com.finclator.admin), killing any stray `python -m src.admin` first
(a stray instance keeps the port and makes the launchd job fail with 'Address already in use')."""
import os
import signal
import subprocess
import time
import urllib.request

for pid in subprocess.run(["pgrep", "-f", "src.admin"], capture_output=True, text=True).stdout.split():
    os.kill(int(pid), signal.SIGTERM)
    print("killed", pid)
time.sleep(2)
subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.finclator.admin"])
for i in range(30):
    time.sleep(1)
    try:
        b = urllib.request.urlopen("http://127.0.0.1:8787/", timeout=20).read().decode()
        print("admin up after", i + 1, "s; new code:", "LOG_URL" in b)
        break
    except Exception:  # noqa: BLE001
        pass
else:
    print("admin NOT up")
    print(open("data/admin.out").read()[-1500:])
print(subprocess.run(["pgrep", "-fl", "src.admin"], capture_output=True, text=True).stdout)
