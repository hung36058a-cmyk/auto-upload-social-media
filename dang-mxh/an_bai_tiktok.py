# -*- coding: utf-8 -*-
r"""AN 1 BAI TIKTOK (doi sang 'Only me'), KHONG XOA. Dung khi may dang nham kenh.
Chay: <repo>\.venv\Scripts\python.exe an_bai_tiktok.py <ten file dang nhap> <id bai> <vai chu dau caption de doi chieu>
Ket qua: chan-doan\an-bai.json + an-bai-*.png"""
import asyncio, json, os, re, sys, traceback
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
if len(sys.argv) < 4:
    sys.exit("Thieu tham so. Can: <ten file dang nhap> <id bai> <vai chu dau caption de doi chieu>")
cookie, item_id, dau = sys.argv[1], sys.argv[2].strip(), sys.argv[3].strip()
res = {"cookie": cookie, "item_id": item_id, "buoc": []}
items = {}
# Chot an toan: phai chi dung 1 bai (id la so) + co chu doi chieu that (chu rong se khop MOI bai) + file dang nhap co trong cau hinh
if not (item_id.isdigit() and len(item_id) >= 15 and len(dau) >= 4
        and any(a.get("mang") == "tiktok" and a.get("cookie") == cookie for a in cfg["tai_khoan"])):
    res["ket_qua"] = "DUNG: tham so khong hop le (id bai phai la so, chu doi chieu >= 4 ky tu, file dang nhap phai co trong cau-hinh.json) -> khong lam gi"
    (OUT / "an-bai.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(res["ket_qua"])
    sys.exit(2)

TIM = """(re)=>{const out=[];for(const el of document.querySelectorAll('span,div,li,button,p,label')){
  const t=(el.innerText||'').trim(); if(!t||t.length>40||!new RegExp(re,'i').test(t)) continue;
  if([...el.children].some(c=>(c.innerText||'').trim()===t)) continue;
  const r=el.getBoundingClientRect(); if(r.width<2||r.height<2) continue;
  out.push({t:t,x:r.x+r.width/2,y:r.y+r.height/2});} return out}"""


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, executable_path=LOCAL_CHROME_PATH)
        try:
            ctx = await browser.new_context(storage_state=str(repo / "cookies" / "tk_uploader" / f"{cookie}.json"),
                                            viewport={"width": 1400, "height": 1000})
            page = await ctx.new_page()

            async def on_resp(r):
                if "creator/manage/item_list" in r.url:
                    try:
                        for it in ((await r.json()).get("item_list") or []):
                            items[str(it.get("item_id"))] = it
                    except Exception:
                        pass

            page.on("response", on_resp)

            async def mo():
                await page.goto("https://www.tiktok.com/tiktokstudio/content", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(12000)

            def tt():
                it = items.get(item_id) or {}
                return {k: it.get(k) for k in ("desc", "visibility", "visibility_status", "status", "in_review", "create_time")}

            await mo()
            res["truoc"] = tt()
            if not dau or dau not in (res["truoc"].get("desc") or ""):
                res["ket_qua"] = "DUNG: khong thay bai / caption khong khop -> khong lam gi"
                return
            link = page.locator(f'a[href*="/video/{item_id}"]').first
            await link.scroll_into_view_if_needed()
            box = await link.bounding_box()
            cy = box["y"] + box["height"] / 2
            ds = [c for c in await page.evaluate(TIM, "^(Everyone|Friends|Followers)$") if abs(c["y"] - cy) < 60 and c["x"] > box["x"]]
            res["buoc"].append({"nut_privacy": ds})
            if not ds:
                res["ket_qua"] = "DUNG: khong thay nut Privacy cua dong nay"
                await page.screenshot(path=str(OUT / "an-bai-loi.png"))
                return
            await page.mouse.click(ds[0]["x"], ds[0]["y"])
            await page.wait_for_timeout(1500)
            await page.screenshot(path=str(OUT / "an-bai-1-menu.png"))
            lc = await page.evaluate(TIM, "^(Only me|Only you|Everyone|Friends|Followers|Private)$")
            res["buoc"].append({"lua_chon": lc})
            chon = [c for c in lc if re.match(r"^(Only me|Only you|Private)$", c["t"], re.I)]
            if not chon:
                res["ket_qua"] = "DUNG: khong thay lua chon 'Only me'"
                await page.keyboard.press("Escape")
                return
            await page.mouse.click(chon[0]["x"], chon[0]["y"])
            await page.wait_for_timeout(2000)
            await page.screenshot(path=str(OUT / "an-bai-2-sau-chon.png"))
            xn = await page.evaluate(TIM, "^(Confirm|Save|OK|Change|Yes|Continue)$")
            res["buoc"].append({"xac_nhan": xn})
            if xn:
                await page.mouse.click(xn[-1]["x"], xn[-1]["y"])
                await page.wait_for_timeout(2000)
            items.clear()
            await mo()
            res["sau"] = tt()
            await page.screenshot(path=str(OUT / "an-bai-3-xong.png"))
            res["ket_qua"] = "xong"
        except Exception:
            res["loi"] = traceback.format_exc()
        finally:
            await browser.close()


asyncio.run(main())
(OUT / "an-bai.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
