#!/usr/bin/env python3
"""Flow Colab Setup - Cell 1
Run in Colab with: !python setup_cell1.py
Sets up VNC + Chromium for Google sign-in.
"""
import subprocess, time, os, glob, sys

def run(cmd, desc):
    print(f"⏳ {desc}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ {desc} had issues: {result.stderr[:200]}")
    else:
        print(f"✅ {desc}")

# Install packages
run("apt-get update -qq", "Updating apt")
run("apt-get install -y -qq tightvncserver xfce4 xfce4-terminal novnc websockify", "Installing VNC/desktop")
run("pip install -q playwright", "Installing Playwright")
run("python -m playwright install chromium", "Installing Chromium")
run("python -m playwright install-deps chromium", "Installing Chromium deps")

# VNC password
os.makedirs(os.path.expanduser("~/.vnc"), exist_ok=True)
subprocess.run("echo 'flow1234' | vncpasswd -f > ~/.vnc/passwd", shell=True)
subprocess.run("chmod 600 ~/.vnc/passwd", shell=True)

# Kill old VNC
subprocess.run("vncserver -kill :1 > /dev/null 2>&1", shell=True)
time.sleep(1)

# Start VNC
run("vncserver :1 -geometry 1280x800 -depth 24", "Starting VNC server")

# Start noVNC
subprocess.run("pkill -f websockify > /dev/null 2>&1", shell=True)
time.sleep(1)
subprocess.Popen(
    ["websockify", "--web=/usr/share/novnc/", "6080", "localhost:5901"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
time.sleep(2)
print("✅ noVNC started on port 6080")

# Launch Chromium with CDP
subprocess.run("pkill -f chromium > /dev/null 2>&1", shell=True)
subprocess.run("pkill -f chrome > /dev/null 2>&1", shell=True)
time.sleep(1)

matches = glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"))
if not matches:
    print("❌ Chromium not found!")
    sys.exit(1)

chrome_bin = matches[0]
env = os.environ.copy()
env["DISPLAY"] = ":1"
subprocess.Popen(
    [chrome_bin, "--remote-debugging-port=9222", "--no-sandbox",
     "--disable-dev-shm-usage", "--disable-gpu", "about:blank"],
    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
print("✅ Chromium launched (CDP on port 9222)")

print()
print("=" * 50)
print("VNC Password: flow1234")
print("=" * 50)
print()
print("Now run this in a new cell to open VNC:")
print("  from google.colab import output")
print("  output.serve_kernel_port_as_window(6080)")
