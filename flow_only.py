#!/usr/bin/env python3
"""Flow bypass only - run AFTER vnc_all.py is running.
Connects to Chrome via CDP and installs the country-block bypass.
"""
import asyncio, json, sys
from urllib.parse import urlparse

TAG = "wrb.fr"
RPCID = "cPZSdc"
FLAG_INDEX = 30
MIN_LEN = 32
FLOW_PATH = "/_/AiSandboxAngularFrontend/data/batchexecute"

def patch_body(text):
    lines = text.split("\n")
    count = 0
    for i, line in enumerate(lines):
        if not line.startswith("[["):
            continue
        try:
            arr = json.loads(line)
        except Exception:
            continue
        changed = False
        for chunk in arr:
            if not isinstance(chunk, list):
                continue
            if len(chunk) < 3:
                continue
            if chunk[0] != TAG or chunk[1] != RPCID:
                continue
            try:
                payload = json.loads(chunk[2])
            except Exception:
                continue
            if not isinstance(payload, list) or len(payload) < MIN_LEN:
                continue
            if payload[FLAG_INDEX] is not None and not isinstance(payload[FLAG_INDEX], bool):
                continue
            payload[FLAG_INDEX] = True
            chunk[2] = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
            changed = True
            count += 1
        if changed:
            new_line = json.dumps(arr, separators=(",", ":"), ensure_ascii=False)
            old_line = line[:-1] if line.endswith("\r") else line
            prev_len = int(lines[i - 1].strip())
            ob = len(old_line.encode("utf-8"))
            oc = len(old_line)
            if prev_len - ob in (0, 1, 2):
                ne, base = len(new_line.encode("utf-8")), ob
            elif prev_len - oc in (0, 1, 2):
                ne, base = len(new_line), oc
            else:
                continue
            lines[i - 1] = str(prev_len + (ne - base))
            lines[i] = new_line
    return "\n".join(lines), count

async def main():
    from playwright.async_api import async_playwright
    print("🔌 Connecting to Chrome...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222", timeout=20000)
        print("✅ Connected!", flush=True)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        async def handle_route(route):
            u = urlparse(route.request.url)
            if u.hostname == "flow.google.com" and u.path == FLOW_PATH and RPCID in (u.query or ""):
                try:
                    resp = await route.fetch()
                    body = await resp.text()
                    new_body, n = patch_body(body)
                    if n > 0:
                        print(f"🛡️  Patched! ({n})", flush=True)
                        await route.fulfill(response=resp, body=new_body)
                    else:
                        await route.continue_()
                except Exception:
                    await route.continue_()
            else:
                await route.continue_()

        await context.route("**/*", handle_route)
        print("🛡️  Bypass ACTIVE", flush=True)
        print("👉 VNC ထဲက Chrome မှာ flow.google.com ကို Refresh နှိပ်!", flush=True)
        print("   (ဒီ cell ကို မရပ်နဲ့)", flush=True)
        while True:
            await asyncio.sleep(60)

asyncio.run(main())
