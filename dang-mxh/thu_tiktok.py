# -*- coding: utf-8 -*-
r"""THU KHONG DANG: chay dung cac buoc kiem tra cua may dang TikTok trong Chrome that (dung tai khoan? doc duoc
danh sach Posts? tim dung bai? KHONG nhan nham bai cu?) ma KHONG tai video, KHONG bam Post, KHONG ghi de file dang nhap.
Ket qua: chan-doan\thu-<ten>.json
Chay: <repo>\.venv\Scripts\python.exe thu_tiktok.py <ten file dang nhap>"""
import asyncio, json, os, sys, time, traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / "cau-hinh.json").read_text(encoding="utf-8-sig"))
repo = Path(cfg["repo"])
os.chdir(repo)
sys.path.insert(0, str(repo))
from playwright.async_api import async_playwright
from uploader.tk_uploader.main_chrome import TiktokVideo, khop_caption

cookie = sys.argv[1]
acc = next((a for a in cfg["tai_khoan"] if a["mang"] == "tiktok" and a["cookie"] == cookie), {})
res = {"cookie": cookie, "can": acc.get("username"), "luc": time.strftime("%Y-%m-%d %H:%M:%S")}


async def main():
    acct = repo / "cookies" / "tk_uploader" / f"{cookie}.json"
    app = TiktokVideo("x", Path("x.mp4"), [], 0, str(acct))
    app.expected_username = acc.get("username")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, executable_path=app.local_executable_path)
        try:
            ctx = await browser.new_context(storage_state=str(acct))
            page = await ctx.new_page()
            page.on("response", app._nghe_ds_bai)
            await app.change_language(page)
            try:
                await app.kiem_tai_khoan(page)
                res["kiem_tai_khoan"] = "dung"
            except RuntimeError as e:
                res["kiem_tai_khoan"] = str(e)
            res["tai_khoan_that"] = app.account_username
            t0 = time.time()
            res["doc_duoc_ds"] = await app.tai_ds_bai(page)
            res["doc_ds_mat_giay"] = round(time.time() - t0, 1)
            res["so_phan_hoi_ds"] = app._so_lan_ds
            res["so_bai_doc_duoc"] = len(app._items)
            res["dong_ho_tiktok_lech_giay"] = round(app._lech, 1)
            app._ids_truoc, app._luc_chup = set(app._items), time.time()
            if app._items:
                moi = max(app._items.values(), key=lambda it: int(it.get("create_time") or 0))
                iid, ct = str(moi.get("item_id")), int(moi.get("create_time") or 0)
                res["bai_moi_nhat"] = {"id": iid, "desc": (moi.get("desc") or "")[:80], "create_time": ct,
                                       "visibility": moi.get("visibility"), "status": moi.get("status")}
                app.title = moi.get("desc") or ""
                res["khop_caption_chinh_no"] = khop_caption(app.title, moi.get("desc"))
                # 1) lan thu bat dau NGAY BAY GIO: bai cu (du cung caption) khong duoc nhan la "da dang"
                app.tu_luc = time.time()
                res["bai_cu_bi_nhan_nham"] = app.tim_bai()                       # phai la null
                # 2) lan thu bat dau truoc khi bai do duoc tao 1 phut: phai tim thay dung bai do
                app.tu_luc = ct - app._lech - 60
                res["tim_thay_khi_trong_cua_so"] = app.tim_bai() == iid          # phai la true
                # 3) sau khi bam Post: bai da co san trong danh sach chup truoc thi khong tinh
                res["bai_co_san_tinh_la_moi"] = app.tim_bai(chi_bai_moi=True)    # phai la null
                # 4) gia lap "bai nay vua xuat hien sau khi bam Post"
                app._ids_truoc.discard(iid)
                app._luc_chup = ct - app._lech - 30
                res["nhan_ra_bai_moi"] = app.tim_bai(chi_bai_moi=True) == iid    # phai la true
            app.title = "caption khong he ton tai 123456789 abcdefghijk"
            app.tu_luc = 0
            res["tim_caption_la"] = app.tim_bai()                                # phai la null
            # trang tai video: chi mo xem, KHONG chon file
            try:
                await page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(6000)
                await app.choose_base_locator(page)
                res["trang_upload"] = {
                    "url": page.url,
                    "co_nut_chon_video": await app.locator_base.locator('button:has-text("Select video")').count(),
                    "nut_post_data_e2e": await app.locator_base.locator('button[data-e2e="post_video_button"]').count(),
                    "nut_trong_button_group": await app.locator_base.locator('div.button-group button').count(),
                }
            except Exception as e:
                res["trang_upload"] = f"{type(e).__name__}: {str(e)[:200]}"
        except Exception:
            res["loi"] = traceback.format_exc()
        finally:
            await browser.close()


asyncio.run(main())
out = HERE / "chan-doan"
out.mkdir(exist_ok=True)
(out / f"thu-{cookie}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
