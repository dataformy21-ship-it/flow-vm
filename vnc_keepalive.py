#!/usr/bin/env python3
"""VNC + Cloudflare tunnel + keep-alive. No password.
Run: !python3 /tmp/vnc_keepalive.py
Keep this cell running - it monitors and auto-restarts everything.
"""
import subprocess, time, os, re, sys, signal

VNC_DISPLAY = ":1"
VNC_PORT = 5901
WEB_PORT = 6080
CHROME_CDP = 9222

def sh(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""

def alive(pattern):
    return bool(sh(f"pgrep -f '{pattern}'"))

def start_xvnc():
    print("🖥️  Starting Xvnc (no password)...")
    # -SecurityTypes None = no password
    subprocess.Popen(
        f"Xvnc {VNC_DISPLAY} -geometry 1280x800 -depth 24 "
        f"-SecurityTypes None -AlwaysShared -rfbport {VNC_PORT} "
        f"> /tmp/xvnc.log 2>&1",
        shell=True)
    time.sleep(3)

def start_websockify():
    print("🔌 Starting websockify (no auth)...")
    novnc = "/usr/share/novnc/utils/novnc_proxy"
    if not os.path.exists(novnc):
        # find websockify
        ws = sh("which websockify") or sh("find / -name websockify -type f 2>/dev/null | head -1")
        if ws:
            subprocess.Popen(
                f"{ws} --web /usr/share/novnc/ {WEB_PORT} localhost:{VNC_PORT} "
                f"> /tmp/websockify.log 2>&1",
                shell=True)
        else:
            print("❌ websockify not found!")
            return
    else:
        subprocess.Popen(
            f"{novnc} --vnc localhost:{VNC_PORT} --listen {WEB_PORT} "
            f"> /tmp/websockify.log 2>&1",
            shell=True)
    time.sleep(3)

def start_chrome():
    print("🌐 Starting Chromium...")
    chrome = "/usr/bin/chromium-browser"
    if not os.path.exists(chrome):
        chrome = sh("which chromium || which chromium-browser || which google-chrome")
    if not chrome:
        print("❌ Chromium not found!")
        return
    env = os.environ.copy()
    env["DISPLAY"] = VNC_DISPLAY
    subprocess.Popen(
        f"{chrome} --no-sandbox --disable-dev-shm-usage "
        f"--remote-debugging-port={CHROME_CDP} "
        f"--user-data-dir=/tmp/chrome-profile "
        f"about:blank > /tmp/chrome.log 2>&1",
        shell=True, env=env)
    time.sleep(3)

def start_tunnel():
    print("🚀 Starting cloudflared tunnel...")
    if not os.path.exists("/usr/local/bin/cloudflared"):
        print("📥 Installing cloudflared...")
        sh("wget -q -O /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && dpkg -i /tmp/cloudflared.deb 2>&1 | tail -1", timeout=120)
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{WEB_PORT}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # wait for URL
    url = None
    start = time.time()
    while time.time() - start < 60:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.5)
            continue
        if "trycloudflare.com" in line:
            m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if m:
                url = m.group(0)
                break
    if url:
        print("")
        print("=" * 60)
        print(f"✅ VNC URL (NO PASSWORD):")
        print(f"   {url}/vnc.html")
        print(f"   Just click Connect - no password needed!")
        print("=" * 60)
        print("")
    else:
        print("⚠️  Tunnel URL not found yet, check /tmp/cloudflared.log")
    return proc

def check_local():
    code = sh(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 5 http://localhost:{WEB_PORT}/vnc.html")
    return code == "200"

def main():
    print("🔧 VNC Keep-Alive starting (no password mode)...")
    print("")

    # Kill old stuff
    sh("pkill -f websockify; pkill -f Xvnc; pkill -f novnc_proxy; pkill -f cloudflared")
    time.sleep(2)

    start_xvnc()
    start_websockify()
    start_chrome()
    tunnel_proc = start_tunnel()

    print("👀 Keep-alive monitor running... (do NOT stop this cell)")
    print("")

    check_interval = 30
    while True:
        time.sleep(check_interval)

        # Check each service
        restarted = []

        if not alive("Xvnc"):
            print("⚠️  Xvnc died → restarting...")
            start_xvnc()
            restarted.append("Xvnc")

        if not alive("websockify") and not alive("novnc_proxy"):
            print("⚠️  websockify died → restarting...")
            start_websockify()
            restarted.append("websockify")

        if not alive("chromium"):
            print("⚠️  Chromium died → restarting...")
            start_chrome()
            restarted.append("Chromium")

        if tunnel_proc.poll() is not None:
            print("⚠️  cloudflared died → restarting...")
            tunnel_proc = start_tunnel()
            restarted.append("tunnel")

        if not check_local():
            print("⚠️  Local VNC not responding → full restart...")
            sh("pkill -f websockify; pkill -f Xvnc; pkill -f novnc_proxy")
            time.sleep(2)
            start_xvnc()
            start_websockify()
            restarted.append("full-vnc")

        if restarted:
            print(f"🔄 Restarted: {', '.join(restarted)}")
        # else: silent, all good

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Keep-alive stopped.")
