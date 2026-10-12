#!/usr/bin/env python3
"""Expose VNC via cloudflared quick tunnel (no signup needed)."""
import subprocess, time, os, re, sys

def run(cmd, desc, timeout=60):
    print(f"⏳ {desc}...")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r

# Install cloudflared if missing
if not os.path.exists("/usr/local/bin/cloudflared"):
    print("📥 Installing cloudflared...")
    r = run("wget -q -O /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && dpkg -i /tmp/cloudflared.deb 2>&1 | tail -2", "Install cloudflared", 120)
    print(r.stdout[-500:] if r.stdout else "")
else:
    print("✅ cloudflared already installed")

# Check VNC is up
r = run("curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:6080/vnc.html", "Check local VNC")
if "200" not in r.stdout:
    print("❌ Local VNC not responding! Run setup first.")
    sys.exit(1)
print("✅ Local VNC OK (200)")

# Start tunnel in background, capture URL
print("🚀 Starting cloudflared tunnel...")
proc = subprocess.Popen(
    ["cloudflared", "tunnel", "--url", "http://localhost:6080"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

url = None
start = time.time()
print("⏳ Waiting for tunnel URL (up to 60s)...")
while time.time() - start < 60:
    line = proc.stdout.readline()
    if not line:
        time.sleep(0.5)
        continue
    # print progress lines
    if "trycloudflare.com" in line:
        m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if m:
            url = m.group(0)
            print(f"\n{'='*60}")
            print(f"✅ VNC PUBLIC URL:")
            print(f"   {url}/vnc.html")
            print(f"   Password: flow1234")
            print(f"{'='*60}\n")
            break

if not url:
    print("❌ Could not get tunnel URL. Output so far:")
    proc.terminate()

# Keep running - don't exit, tunnel needs to stay alive
print("🔗 Tunnel is live. Keep this cell running!")
print("   (Do NOT stop this cell or the tunnel dies)")
try:
    proc.wait()
except KeyboardInterrupt:
    print("\n🛑 Tunnel stopped.")
