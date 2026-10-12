#!/usr/bin/env python3
"""Fast VNC + Cloudflare + keep-alive. No password.
Based on the fast notebook approach: xfce4 + tigervnc + real Google Chrome.

Run: !python3 /tmp/vnc_fast.py
Keep this cell running.
"""
import subprocess, time, os, re, sys

def sh(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""

def alive(pattern):
    return bool(sh(f"pgrep -f '{pattern}'"))

def install():
    print("📦 Installing (5-10 min, one time only)...")
    sh("apt-get update -qq", 120)
    sh("DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xfce4 xfce4-terminal tigervnc-standalone-server websockify dbus-x11 > /dev/null 2>&1", 600)
    if not os.path.exists("/opt/novnc/vnc.html"):
        print("📦 noVNC...")
        sh("mkdir -p /opt/novnc && curl -sL https://github.com/novnc/noVNC/archive/refs/tags/v1.5.0.tar.gz | tar -xz -C /opt/novnc --strip-components=1", 120)
    if not sh("which google-chrome-stable"):
        print("📦 Google Chrome...")
        sh("wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && apt-get install -y -qq ./google-chrome-stable_current_amd64.deb > /dev/null 2>&1; rm -f google-chrome-stable_current_amd64.deb", 300)
    if not os.path.exists("/usr/local/bin/cloudflared"):
        print("📦 cloudflared...")
        sh("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared", 120)
    print("✅ Install done")

def setup_vnc():
    print("🖥️  Setting up VNC (NO password)...")
    # xstartup for xfce
    os.makedirs(os.path.expanduser("~/.vnc"), exist_ok=True)
    with open(os.path.expanduser("~/.vnc/xstartup"), "w") as f:
        f.write("#!/bin/sh\nunset SESSION_MANAGER\nunset DBUS_SESSION_BUS_ADDRESS\nexec startxfce4\n")
    os.chmod(os.path.expanduser("~/.vnc/xstartup"), 0o755)

    # Chrome autostart
    os.makedirs(os.path.expanduser("~/.config/autostart"), exist_ok=True)
    with open(os.path.expanduser("~/.config/autostart/chrome.desktop"), "w") as f:
        f.write("[Desktop Entry]\nType=Application\nName=Google Chrome\n"
                "Exec=google-chrome-stable --no-sandbox --disable-dev-shm-usage "
                "--remote-debugging-port=9222 --start-maximized\n")

    # Kill old
    sh("vncserver -kill :1 2>/dev/null; pkill -f websockify 2>/dev/null; pkill -f 'cloudflared tunnel' 2>/dev/null")
    time.sleep(2)

    # Start VNC with NO password
    r = sh("vncserver :1 -geometry 1280x800 -depth 24 -SecurityTypes None 2>&1")
    print(f"   VNC: {r[:100]}")
    time.sleep(3)

    # websockify (no auth since VNC has none)
    subprocess.Popen("websockify --web=/opt/novnc 6080 localhost:5901 > /tmp/websockify.log 2>&1", shell=True)
    time.sleep(3)

    code = sh("curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:6080/vnc.html")
    print(f"   Local check: {code}")
    return code == "200"

def start_tunnel():
    print("🚀 Starting Cloudflare tunnel...")
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:6080"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = None
    start = time.time()
    while time.time() - start < 60:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.5)
            continue
        if "trycloudflare.com" in line:
            m = re.search(r'https://[a-zA-Z0-9.-]+\.trycloudflare\.com', line)
            if m:
                url = m.group(0)
                break
    if url:
        print("")
        print("=" * 60)
        print("✅ VNC URL (NO PASSWORD):")
        print(f"   {url}/vnc.html")
        print("   Click Connect — no password!")
        print("=" * 60)
        print("")
    else:
        print("⚠️  Tunnel URL not captured, check manually")
    return proc

def main():
    # Install only if needed
    if not sh("which vncserver") or not os.path.exists("/opt/novnc/vnc.html"):
        install()
    else:
        print("✅ Software already installed, skipping...")

    if not setup_vnc():
        print("❌ VNC failed to start!")
        sys.exit(1)

    tunnel = start_tunnel()

    print("👀 Keep-alive running — do NOT stop this cell!")
    while True:
        time.sleep(30)
        fixed = []
        if not alive("Xtigervnc") and not alive("Xvnc"):
            print("⚠️  VNC died → restarting...")
            sh("vncserver :1 -geometry 1280x800 -depth 24 -SecurityTypes None 2>&1")
            fixed.append("VNC")
        if not alive("websockify"):
            print("⚠️  websockify died → restarting...")
            subprocess.Popen("websockify --web=/opt/novnc 6080 localhost:5901 > /tmp/websockify.log 2>&1", shell=True)
            fixed.append("websockify")
        if not alive("chrome"):
            print("⚠️  Chrome died → restarting...")
            env = os.environ.copy()
            env["DISPLAY"] = ":1"
            subprocess.Popen("google-chrome-stable --no-sandbox --disable-dev-shm-usage --remote-debugging-port=9222 --start-maximized > /tmp/chrome.log 2>&1",
                           shell=True, env=env)
            fixed.append("Chrome")
        if tunnel.poll() is not None:
            print("⚠️  Tunnel died → restarting...")
            tunnel = start_tunnel()
            fixed.append("tunnel")
        if fixed:
            print(f"🔄 Fixed: {', '.join(fixed)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Stopped.")
