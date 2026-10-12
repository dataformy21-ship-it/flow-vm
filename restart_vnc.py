#!/usr/bin/env python3
"""Restart VNC services on Colab: websockify + Chrome. Lightweight, no apt."""
import subprocess, time, os, glob

def run(cmd, desc):
    print(f"⏳ {desc}...")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"  → rc={r.returncode} {r.stdout.strip()[:200]} {r.stderr.strip()[:200]}")
    return r

os.environ.setdefault("USER", "root")

# 1. websockify
r = subprocess.run("pgrep -f websockify", shell=True, capture_output=True, text=True)
if r.stdout.strip():
    print(f"✅ websockify already running (PID {r.stdout.strip()})")
else:
    print("🔄 Starting websockify...")
    subprocess.Popen(
        ["websockify", "--web=/usr/share/novnc/", "6080", "localhost:5901"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    r = run("curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:6080/vnc.html", "Check noVNC")
    print("✅ websockify started" if "200" in r.stdout else "❌ websockify check failed")

# 2. Chrome
r = subprocess.run("pgrep -f chromium", shell=True, capture_output=True, text=True)
if r.stdout.strip():
    print(f"✅ Chrome already running (PID {r.stdout.strip()})")
else:
    print("🔄 Starting Chrome...")
    chrome_bin = "/usr/bin/chromium-browser"
    if not os.path.exists(chrome_bin):
        for pat in [os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome")]:
            m = glob.glob(pat)
            if m:
                chrome_bin = m[0]
                break
    print(f"  Using: {chrome_bin}")
    env = os.environ.copy()
    env["DISPLAY"] = ":1"
    env["USER"] = "root"
    subprocess.Popen(
        [chrome_bin, "--remote-debugging-port=9222", "--no-sandbox",
         "--disable-dev-shm-usage", "--disable-gpu", "about:blank"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)
    r = run("curl -s --max-time 5 http://localhost:9222/json/version | head -c 150", "Check CDP")
    print("✅ Chrome CDP up" if "Chrome" in r.stdout or "chromium" in r.stdout.lower() else "❌ CDP not responding")

print("\nDone!")
