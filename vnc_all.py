#!/usr/bin/env python3
"""ALL-IN-ONE: VNC + Cloudflare + Flow bypass + keep-alive.
No password. One cell, run once, keep running.

Run: !python3 /tmp/vnc_all.py
"""
import subprocess, time, os, re, sys, asyncio, json
from urllib.parse import urlparse

# ---- Flow patch spec (verified 2026-10-10) ----
TAG = "wrb.fr"
RPCID = "cPZSdc"
FLAG_INDEX = 30
MIN_LEN = 32
FLOW_ORIGIN = "https://flow.google.com"
FLOW_PATH = "/_/AiSandboxAngularFrontend/data/batchexecute"

def sh(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""

def sh_live(cmd, timeout=900):
    print(f"  $ {cmd[:70]}", flush=True)
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    try:
        for line in proc.stdout:
            line = line.strip()
            if line and ("Setting up" in line or "Unpacking" in line or "Get:" in line):
                print(f"    {line[:90]}", flush=True)
        proc.wait(timeout=timeout)
    except Exception as e:
        proc.kill()
    return proc.returncode == 0

def alive(pat):
    return bool(sh(f"pgrep -f '{pat}'"))

# ============ VNC SETUP ============
def install():
    print("📦 [1/5] apt update...", flush=True)
    sh_live("apt-get update -qq", 120)
    print("📦 [2/5] desktop + VNC...", flush=True)
    sh_live("DEBIAN_FRONTEND=noninteractive apt-get install -y xfce4 xfce4-terminal tigervnc-standalone-server websockify dbus-x11", 900)
    if not os.path.exists("/opt/novnc/vnc.html"):
        print("📦 [3/5] noVNC...", flush=True)
        sh_live("mkdir -p /opt/novnc && curl -sL https://github.com/novnc/noVNC/archive/refs/tags/v1.5.0.tar.gz | tar -xz -C /opt/novnc --strip-components=1", 120)
    if not sh("which google-chrome-stable"):
        print("📦 [4/5] Google Chrome...", flush=True)
        sh_live("wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && apt-get install -y ./google-chrome-stable_current_amd64.deb; rm -f google-chrome-stable_current_amd64.deb", 300)
    if not os.path.exists("/usr/local/bin/cloudflared"):
        print("📦 [5/5] cloudflared...", flush=True)
        sh_live("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared", 120)
    if not sh("pip show playwright 2>/dev/null | grep -i version"):
        print("📦 [6/6] playwright...", flush=True)
        sh_live("pip install -q playwright", 180)
    print("✅ Install done", flush=True)

def setup_vnc():
    print("🖥️  VNC setup (no password)...", flush=True)
    os.makedirs(os.path.expanduser("~/.vnc"), exist_ok=True)
    with open(os.path.expanduser("~/.vnc/xstartup"), "w") as f:
        f.write("#!/bin/sh\nunset SESSION_MANAGER\nunset DBUS_SESSION_BUS_ADDRESS\nexec startxfce4\n")
    os.chmod(os.path.expanduser("~/.vnc/xstartup"), 0o755)
    os.makedirs(os.path.expanduser("~/.config/autostart"), exist_ok=True)
    with open(os.path.expanduser("~/.config/autostart/chrome.desktop"), "w") as f:
        f.write("[Desktop Entry]\nType=Application\nName=Google Chrome\n"
                "Exec=google-chrome-stable --no-sandbox --disable-dev-shm-usage "
                "--remote-debugging-port=9222 --start-maximized\n")
    sh("vncserver -kill :1 2>/dev/null; pkill -f websockify 2>/dev/null; pkill -f 'cloudflared tunnel' 2>/dev/null")
    time.sleep(2)
    sh("vncserver :1 -geometry 1280x800 -depth 24 -SecurityTypes None 2>&1")
    time.sleep(3)
    subprocess.Popen("websockify --web=/opt/novnc 6080 localhost:5901 > /tmp/websockify.log 2>&1", shell=True)
    time.sleep(3)
    code = sh("curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:6080/vnc.html")
    print(f"   Local VNC: {code}", flush=True)
    return code == "200"

def start_tunnel():
    print("🚀 Cloudflare tunnel...", flush=True)
    proc = subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:6080"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = None
    start = time.time()
    while time.time() - start < 60:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.5); continue
        if "trycloudflare.com" in line:
            m = re.search(r'https://[a-zA-Z0-9.-]+\.trycloudflare\.com', line)
            if m:
                url = m.group(0); break
    if url:
        print("", flush=True)
        print("=" * 58, flush=True)
        print("✅ VNC URL (NO PASSWORD):", flush=True)
        print(f"   {url}/vnc.html", flush=True)
        print("   Click Connect — no password!", flush=True)
        print("=" * 58, flush=True)
        print("", flush=True)
    return proc, url

# ============ FLOW BYPASS ============
def patch_body(text):
    lines = text.split("\n"); count = 0
    for i, line in enumerate(lines):
        if not line.startswith("[["): continue
        try: arr = json.loads(line)
        except: continue
        changed = False
        for chunk in arr:
            if not isinstance(chunk, list):
                continue
            if len(chunk) < 3:
                continue
            if chunk[0] != TAG or chunk[1] != RPCID: continue
            try: payload = json.loads(chunk[2])
            except: continue
            if not isinstance(payload, list) or len(payload) < MIN_LEN: continue
            if payload[FLAG_INDEX] is not None and not isinstance(payload[FLAG_INDEX], bool): continue
            payload[FLAG_INDEX] = True
            chunk[2] = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
            changed = True; count += 1
        if changed:
            new_line = json.dumps(arr, separators=(",", ":"), ensure_ascii=False)
            old_line = line[:-1] if line.endswith("\r") else line
            prev_len = int(lines[i-1].strip())
            ob, oc = len(old_line.encode("utf-8")), len(old_line)
            if prev_len - ob in (0,1,2): ne, b = len(new_line.encode("utf-8")), ob
            elif prev_len - oc in (0,1,2): ne, b = len(new_line), oc
            else: continue
            lines[i-1] = str(prev_len + (ne - b)); lines[i] = new_line
    return "\n".join(lines), count

async def setup_flow_bypass():
    from playwright.async_api import async_playwright
    print("🛡️  Flow bypass setup...", flush=True)
    try:
        p = await async_playwright().start()
        browser = await p.chromium.connect_over_cdp("http://localhost:9222", timeout=20000)
    except Exception as e:
        print(f"   ⚠️  CDP connect failed ({e}), retry after Chrome starts", flush=True)
        return None, None
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = context.pages[0] if context.pages else await context.new_page()

    async def handle_route(route):
        req = route.request
        u = urlparse(req.url)
        if u.hostname == "flow.google.com" and u.path == FLOW_PATH and RPCID in (u.query or ""):
            try:
                resp = await route.fetch()
                body = await resp.text()
                new_body, n = patch_body(body)
                if n > 0:
                    print(f"   🛡️  Patched Flow config ({n})", flush=True)
                    await route.fulfill(response=resp, body=new_body)
                else:
                    await route.continue_()
            except Exception:
                await route.continue_()
        else:
            await route.continue_()

    await context.route("**/*", handle_route)
    print("   ✅ Bypass active", flush=True)
    try:
        await page.bring_to_front()
        await page.goto(FLOW_ORIGIN, wait_until="domcontentloaded", timeout=60000)
        print("   ✅ flow.google.com opened in VNC Chrome", flush=True)
    except Exception as e:
        print(f"   ⚠️  Flow page: {e}", flush=True)
    return p, browser

# ============ MAIN ============
async def main():
    print("🔧 ALL-IN-ONE starting...", flush=True)
    print("", flush=True)

    if not sh("which vncserver") or not os.path.exists("/opt/novnc/vnc.html"):
        install()
    else:
        print("✅ Software ready, skipping install", flush=True)
        if not sh("pip show playwright 2>/dev/null | grep -i version"):
            print("📦 playwright...", flush=True)
            sh_live("pip install -q playwright", 180)

    if not setup_vnc():
        print("❌ VNC failed!", flush=True); sys.exit(1)

    tunnel_proc, vnc_url = start_tunnel()

    # Wait for Chrome to be ready, then setup bypass
    print("⏳ Waiting for Chrome...", flush=True)
    for _ in range(10):
        if sh("curl -s --max-time 3 http://localhost:9222/json/version | grep -o 'Chrome'"):
            break
        time.sleep(3)

    pw, browser = await setup_flow_bypass()

    print("", flush=True)
    print("=" * 58, flush=True)
    print("🎉 ALL READY!", flush=True)
    print(f"   VNC: {vnc_url}/vnc.html  (no password)", flush=True)
    print("   → Open VNC → Chrome → flow.google.com → country block GONE", flush=True)
    print("   ⚠️  Do NOT stop this cell!", flush=True)
    print("=" * 58, flush=True)
    print("", flush=True)

    # Keep-alive loop - also retries bypass if it failed initially
    bypass_ok = pw is not None
    while True:
        await asyncio.sleep(30)
        fixed = []
        # Retry Flow bypass if not yet active
        if not bypass_ok:
            print("🔄 Retrying Flow bypass...", flush=True)
            pw2, browser2 = await setup_flow_bypass()
            if pw2 is not None:
                pw, browser = pw2, browser2
                bypass_ok = True
                print("✅ Flow bypass now ACTIVE!", flush=True)
        if not alive("Xtigervnc") and not alive("Xvnc"):
            sh("vncserver :1 -geometry 1280x800 -depth 24 -SecurityTypes None 2>&1")
            fixed.append("VNC")
        if not alive("websockify"):
            subprocess.Popen("websockify --web=/opt/novnc 6080 localhost:5901 > /tmp/websockify.log 2>&1", shell=True)
            fixed.append("websockify")
        if not alive("chrome"):
            env = os.environ.copy(); env["DISPLAY"] = ":1"
            subprocess.Popen("google-chrome-stable --no-sandbox --disable-dev-shm-usage --remote-debugging-port=9222 --start-maximized > /tmp/chrome.log 2>&1",
                           shell=True, env=env)
            fixed.append("Chrome")
            # re-setup bypass after chrome restart
            await asyncio.sleep(5)
            pw, browser = await setup_flow_bypass()
        if tunnel_proc.poll() is not None:
            tunnel_proc, vnc_url = start_tunnel()
            fixed.append("tunnel")
        if fixed:
            print(f"🔄 Auto-fixed: {', '.join(fixed)}", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Stopped.")
