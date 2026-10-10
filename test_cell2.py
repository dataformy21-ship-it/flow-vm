# ============================================
# Cell 2: Patch + Test Flow — Run this AFTER signing in to Google in the VNC browser
# ============================================

import asyncio
from playwright.async_api import async_playwright

# The patch function (same logic as CFC Flow extension)
PATCH_JS = """
function modifyResponse(args){
var t=args.response,L=t.split("\\n"),c=0;
for(var i=0;i<L.length;i++){
var ln=L[i];if(ln.indexOf("[[")!==0)continue;
var a;try{a=JSON.parse(ln)}catch(e){continue}
var ch=false;
for(var j=0;j<a.length;j++){
var k=a[j];
if(!Array.isArray(k)||k.length<3||k[0]!=="wrb.fr"||k[1]!=="cPZSdc")continue;
var p;try{p=JSON.parse(k[2])}catch(e){continue}
if(!Array.isArray(p)||p.length<32)continue;
if(p[30]!==null&&typeof p[30]!=="boolean")continue;
p[30]=true;k[2]=JSON.stringify(p);ch=true;c++;
}
if(ch){
var nl=JSON.stringify(a),ol=ln[ln.length-1]==="\\r"?ln.slice(0,-1):ln;
var pl=parseInt(L[i-1].trim(),10);
var ob=new TextEncoder().encode(ol).length,nb=new TextEncoder().encode(nl).length;
if(pl-ob>=0&&pl-ob<=2){L[i-1]=String(pl+(nb-ob))}
else{var oc=ol.length,nc=nl.length;if(pl-oc>=0&&pl-oc<=2){L[i-1]=String(pl+(nc-oc))}}
L[i]=nl;
}
}
return c>0?L.join("\\n"):t;
}
"""

async def test_flow():
    async with async_playwright() as p:
        # Connect to the existing Chromium (launched in Cell 1)
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

        patched = {"count": 0}

        async def handle_route(route):
            # Only intercept the Flow config batchexecute
            req = route.request
            if "batchexecute" in req.url and "cPZSdc" in req.url:
                resp = await route.fetch()
                body = await resp.text()
                # Apply patch via JS evaluation
                # We do it in Python for reliability
                import json
                lines = body.split("\n")
                changed = 0
                for i, ln in enumerate(lines):
                    if not ln.startswith("[["):
                        continue
                    try:
                        a = json.loads(ln)
                    except:
                        continue
                    ch = False
                    for k in a:
                        if not isinstance(k, list) or len(k) < 3:
                            continue
                        if k[0] != "wrb.fr" or k[1] != "cPZSdc":
                            continue
                        try:
                            inner = json.loads(k[2])
                        except:
                            continue
                        if not isinstance(inner, list) or len(inner) < 32:
                            continue
                        if inner[30] is not None and not isinstance(inner[30], bool):
                            continue
                        inner[30] = True
                        k[2] = json.dumps(inner)
                        ch = True
                        changed += 1
                    if ch:
                        nl = json.dumps(a)
                        ol = ln[:-1] if ln.endswith("\r") else ln
                        try:
                            pl = int(lines[i-1].strip())
                        except:
                            pl = -1
                        ob = len(ol.encode('utf-8'))
                        nb = len(nl.encode('utf-8'))
                        if 0 <= pl - ob <= 2:
                            lines[i-1] = str(pl + (nb - ob))
                        else:
                            oc = len(ol); nc = len(nl)
                            if 0 <= pl - oc <= 2:
                                lines[i-1] = str(pl + (nc - oc))
                        lines[i] = nl
                if changed > 0:
                    patched["count"] += changed
                    new_body = "\n".join(lines)
                    await route.fulfill(
                        response=resp,
                        body=new_body,
                    )
                    print(f"🔧 Patched {changed} config(s)")
                else:
                    await route.continue_()
            else:
                await route.continue_()

        await context.route("**/*", handle_route)

        print("🌐 Navigating to flow.google.com...")
        await page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(10000)

        url = page.url
        print(f"📍 Final URL: {url}")
        print(f"🔧 Total patches applied: {patched['count']}")

        if "unsupported-country" in url:
            print("❌ STILL BLOCKED — region check not bypassed")
            # Take screenshot for debugging
            await page.screenshot(path="/tmp/flow_blocked.png")
            print("Screenshot saved to /tmp/flow_blocked.png")
        else:
            print("✅ FLOW LOADED! Not on unsupported-country page")
            await page.screenshot(path="/tmp/flow_loaded.png")
            print("Screenshot saved to /tmp/flow_loaded.png")
            # Get page title
            title = await page.title()
            print(f"📄 Page title: {title}")

        # Don't close the browser — user might want to interact
        # await browser.close()

import asyncio
asyncio.run(test_flow())
