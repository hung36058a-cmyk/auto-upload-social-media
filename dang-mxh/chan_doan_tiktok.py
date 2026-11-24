# -*- coding: utf-8 -*-
r"""CHAN DOAN: moi file dang nhap TikTok dang o tai khoan nao + danh sach bai trong TikTok Studio.
Chi DOC, khong dang gi, khong ghi de file dang nhap. Ket qua: chan-doan\<ten>.json + .png
Chay: <repo>\.venv\Scripts\python.exe chan_doan_tiktok.py [ten ...]"""
import asyncio, json, os, sys, traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / "cau-hinh.json").read_text(encoding="utf-8-sig"))
repo = Path(cfg["repo"])
os.chdir(repo)
sys.path.insert(0, str(repo))
from playwright.async_api import async_playwright
from conf import LOCAL_CHROME_PATH

OUT = HERE / "chan-doan"
OUT.mkdir(exist_ok=True)
KEYS = ("item_list", "creator/manage", "account/info", "user/detail", "project/post", "creator/item", "content/list")


async def one(p, name):
    res = {"cookie": name, "api": [], "xhr": []}
    browser = await p.chromium.launch(headless=False, executable_path=LOCAL_CHROME_PATH)
    try:
        ctx = await browser.new_context(storage_state=str(repo / "cookies" / "tk_uploader" / f"{name}.json"),
                                        viewport={"width": 1400, "height": 1000})
        page = await ctx.new_page()

        async def on_resp(r):
            u = r.url
            try:
                if r.request.resource_type in ("xhr", "fetch"):
                    res["xhr"].append(u[:200])
                if any(k in u for k in KEYS):
                    res["api"].append({"url": u[:300], "status": r.status, "body": (await r.text())[:30000]})
            except Exception:
                pass

        page.on("response", on_resp)
        await page.goto("https://www.tiktok.com/tiktokstudio/content", wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(15000)
        res["url"] = page.url
        res["acc"] = await page.evaluate("""async()=>{try{const r=await fetch('https://www.tiktok.com/passport/web/account/info/?aid=1459',{credentials:'include'});return await r.text()}catch(e){return 'ERR '+e}}""")
        res["text"] = (await page.inner_text("body"))[:8000]
        res["links"] = await page.evaluate("()=>[...document.querySelectorAll('a[href*=\"/video/\"]')].map(a=>a.href).slice(0,40)")
        await page.screenshot(path=str(OUT / f"{name}.png"))
    except Exception:
        res["loi"] = traceback.format_exc()
    finally:
        await browser.close()
    (OUT / f"{name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


async def main():
    names = sys.argv[1:] or sorted(f.stem for f in (repo / "cookies" / "tk_uploader").glob("*.json"))
    (OUT / "xong.txt").unlink(missing_ok=True)
    async with async_playwright() as p:
        for n in names:
            await one(p, n)
    (OUT / "xong.txt").write_text("xong", encoding="utf-8")


asyncio.run(main())
