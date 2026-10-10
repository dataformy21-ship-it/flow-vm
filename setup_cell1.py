#!/usr/bin/env python3
"""Flow Colab Setup v2 - Fixed
Run in Colab with: !python setup_cell1.py
"""
import subprocess, time, os, glob, sys

def run(cmd, desc):
    print(f"⏳ {desc}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ {desc}: {result.stderr[:300]}")
    else:
        print(f"✅ {desc}")
    return result

# Fix USER env var (needed for vncserver)
if "USER" not in os.environ:
    os.environ["USER"] = "root"
    print("✅ Set USER=root")

# Install packages
run("apt-get update -qq", "Updating apt")
run("apt-get install -y -qq tightvncserver xfce4 xfce4-terminal novnc websockify xvfb", "Installing VNC/desktop")
run("pip install -q playwright", "Installing Playwright")
run("python -m playwright install chromium", "Installing Chromium")

# Find Chromium - try multiple paths
chrome_bin = None
for pattern in [
    os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/headless_shell"),
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
]:
    matches = glob.glob(pattern)
    if matches:
        chrome_bin = matches[0]
        print(f"✅ Found Chromium: {chrome_bin}")
        break

if not chrome_bin:
    print("❌ Chromium not found, trying apt install...")
    run("apt-get install -y -qq chromium-browser", "Installing chromium-browser")
    for p in ["/usr/bin/chromium-browser", "/usr/bin/chromium"]:
        if os.path.exists(p):
            chrome_bin = p
            print(f"✅ Found Chromium: {chrome_bin}")
            break

if not chrome_bin:
    print("❌ Chromium not found anywhere!")
    sys.exit(1)

# VNC password
os.makedirs(os.path.expanduser("~/.vnc"), exist_ok=True)
subprocess.run("echo 'flow1234' | vncpasswd -f > ~/.vnc/passwd", shell=True, env=os.environ)
subprocess.run("chmod 600 ~/.vnc/passwd", shell=True)
print("✅ VNC password set")

# Kill old VNC
subprocess.run("vncserver -kill :1 > /dev/null 2>&1", shell=True, env=os.environ)
subprocess.run("pkill -f websockify > /dev/null 2>&1", shell=True)
subprocess.run("pkill -f Xvfb > /dev/null 2>&1", shell=True)
time.sleep(2)

# Start VNC server
result = run("vncserver :1 -geometry 1280x800 -depth 24", "Starting VNC server")
if "USER environment variable" in result.stderr:
    print("❌ USER var still not set, trying with explicit env...")
    env = os.environ.copy()
    env["USER"] = "root"
    result = subprocess.run("vncserver :1 -geometry 1280x800 -depth 24",
                           shell=True, capture_output=True, text=True, env=env)
    print(result.stdout[:500])
    print(result.stderr[:500])

# Verify VNC is running
time.sleep(2)
result = subprocess.run("pgrep -f Xvnc", shell=True, capture_output=True, text=True)
if result.stdout.strip():
    print(f"✅ VNC running (PID: {result.stdout.strip()})")
else:
    print("❌ VNC not running!")

# Start websockify for noVNC
import subprocess as sp
proc = sp.Popen(
    ["websockify", "--web=/usr/share/novnc/", "6080", "localhost:5901"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
time.sleep(3)

# Verify port 6080 is listening
result = subprocess.run("ss -tln | grep 6080", shell=True, capture_output=True, text=True)
if "6080" in result.stdout:
    print("✅ noVNC listening on port 6080")
else:
    print("❌ Port 6080 not listening!")
    print("Checking websockify process...")
    result = subprocess.run("pgrep -f websockify", shell=True, capture_output=True, text=True)
    print(f"websockify PIDs: {result.stdout.strip() or 'none'}")

# Launch Chromium with CDP in VNC display
subprocess.run("pkill -f chromium > /dev/null 2>&1", shell=True)
subprocess.run("pkill -f chrome > /dev/null 2>&1", shell=True)
time.sleep(1)

env = os.environ.copy()
env["DISPLAY"] = ":1"
env["USER"] = "root"
sp.Popen(
    [chrome_bin, "--remote-debugging-port=9222", "--no-sandbox",
     "--disable-dev-shm-usage", "--disable-gpu", "about:blank"],
    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
time.sleep(2)
print("✅ Chromium launched (CDP on port 9222)")

print()
print("=" * 50)
print("VNC Password: flow1234")
print("Setup complete!")
print("=" * 50)
