# -*- coding: utf-8 -*-
r"""DANG NHAP LAI TIKTOK / INSTAGRAM / THREADS - CHI GIU KHI DUNG TAI KHOAN
Bam DANG_NHAP_LAI.bat. May tu tim tai khoan nao dang sai / het han / chua dang nhap roi mo Chrome cho tung cai:
  TikTok:    hien ma QR. Tren dien thoai mo app TikTok, CHUYEN SANG dung kenh (ten @ in o cua so den) roi quet.
             May tu kiem ten @: dung -> tu luu va dong; sai -> tu dang xuat de quet lai. Khong can bam Enter.
  Instagram: hien trang dang nhap. Dang nhap dung kenh; xong may tu dong cua so va kiem ten @.
             Sai kenh (khac ten da ghim) -> may KHONG giu file dang nhap do.
Tham so (khong bat buoc):  [--tiktok | --instagram]  [ten file dang nhap ...]
  vd  dang_nhap_lai.py --tiktok kinhte2   = dang nhap (lai) rieng tai khoan TikTok 'kinhte2', ke ca tai khoan moi chua co trong cau-hinh.json
"""
import asyncio, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dang_mxh as M

cfg = M.load_cfg()
repo = Path(cfg["repo"])
os.chdir(repo)
sys.path.insert(0, str(repo))

JS = """async()=>{try{const r=await fetch('https://www.tiktok.com/passport/web/account/info/?aid=1459',{credentials:'include'});const j=await r.json();return (j.data&&j.data.username)||''}catch(e){return ''}}"""
CHO_PHUT = 10
TEN_TT = {"ok": "đúng", "het_han": "HẾT HẠN", "chua_dang_nhap": "CHƯA ĐĂNG NHẬP", "sai_tai_khoan": "SAI TÀI KHOẢN",
          "khong_ro": "không kiểm được (mất mạng?)"}


def luu_ban_cu(f: Path, duoi: str = "") -> Path | None:
    """Chep file dang nhap hien co vao cookies\\...\\_luu truoc khi dung toi."""
    if not f.exists():
        return None
    luu = f.parent / "_luu"
    luu.mkdir(exist_ok=True)
    dich = luu / f"{f.stem}.{time.strftime('%Y%m%d-%H%M%S')}{duoi}.json"
    shutil.copyfile(f, dich)
    return dich


async def dang_nhap_tiktok(p, acc) -> bool:
    from utils.base_social_media import set_init_script
    cookie, want = acc["cookie"], M.ghim(acc)
    out = repo / "cookies" / "tk_uploader" / f"{cookie}.json"
    print("\n" + "=" * 66)
    print(f"  CẦN ĐĂNG NHẬP KÊNH TIKTOK:  @{want or '(chưa ghim tên @ — máy sẽ lưu tài khoản bạn quét)'}")
    print("  1) Điện thoại: mở app TikTok → CHUYỂN SANG đúng kênh này.")
    print("  2) Quét mã QR trên cửa sổ Chrome vừa mở (Hồ sơ > nút 3 gạch > Mã QR của tôi > Quét).")
    print(f"  Máy tự kiểm và tự lưu. Chờ tối đa {CHO_PHUT} phút.")
    print("=" * 66, flush=True)
    browser = await p.chromium.launch(headless=False, args=["--lang=en-GB"])
    try:
        ctx = await set_init_script(await browser.new_context())
        page = await ctx.new_page()
        await page.goto("https://www.tiktok.com/login/qrcode?lang=en")
        han = time.time() + CHO_PHUT * 60
        while time.time() < han:
            await asyncio.sleep(3)
            try:
                user = await page.evaluate(JS)
            except Exception:
                continue
            if not user:
                continue
            if want and not M.cung_ten(user, want):
                print(f"\n  !!! SAI KÊNH: vừa đăng nhập @{user}, nhưng cần @{want}.")
                print(f"      Trên điện thoại chuyển sang @{want} rồi quét lại mã QR mới.", flush=True)
                await ctx.clear_cookies()
                try:
                    await page.goto("https://www.tiktok.com/login/qrcode?lang=en")
                except Exception:
                    pass
                continue
            await asyncio.sleep(3)   # cho TikTok ghi xong cookie
            luu_ban_cu(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_suffix(".json.tmp")
            await ctx.storage_state(path=str(tmp))
            os.replace(tmp, out)
            print(f"\n  OK: đã lưu đăng nhập TikTok @{user} vào '{cookie}'.", flush=True)
            if not want:
                print("  (Tài khoản này CHƯA GHIM tên @ → xong thì bấm XAC_NHAN_TAI_KHOAN.bat để ghim.)", flush=True)
            return True
        print("\n  Hết giờ chờ, chưa đăng nhập được. Bấm lại file .bat để thử lại.", flush=True)
        return False
    finally:
        await browser.close()


def dang_nhap_instagram(acc) -> bool:
    """Mo `sau instagram login`. File dang nhap cu duoc cat vao _luu truoc; dang nhap xong ma sai kenh thi khong giu."""
    cookie, want = acc["cookie"], M.ghim(acc)
    f = repo / "cookies" / f"instagram_{cookie}.json"
    sau = repo / ".venv" / "Scripts" / "sau.exe"
    print("\n" + "=" * 66)
    print(f"  CẦN ĐĂNG NHẬP KÊNH INSTAGRAM:  @{want or '(chưa ghim tên @)'}")
    print("  Chrome sắp mở trang đăng nhập Instagram. Đăng nhập ĐÚNG kênh này (tối đa 15 phút).")
    print("  Đăng nhập xong không cần bấm gì: cửa sổ tự đóng, máy tự kiểm tên tài khoản.")
    print("=" * 66, flush=True)
    cu = luu_ban_cu(f)
    if cu:
        f.unlink()            # `sau` thay file cu con dung duoc la bo qua buoc dang nhap -> phai cat di (ban cu nam trong _luu)
    code = subprocess.call([str(sau), "instagram", "login", "--account", cookie], cwd=str(repo))
    if code != 0 or not f.exists():
        if cu and not f.exists():
            shutil.copyfile(cu, f)        # chua dang nhap duoc -> tra lai file cu nhu truoc
        print("\n  Chưa đăng nhập được Instagram. Bấm lại file .bat để thử lại.", flush=True)
        return False
    st, user = M.check_login(cfg, dict(acc, ma=f"instagram_{cookie}"))
    if want and user and not M.cung_ten(user, want):
        luu_ban_cu(f, ".sai-kenh")
        f.unlink()
        if cu:
            shutil.copyfile(cu, f)
        print(f"\n  !!! SAI KÊNH: vừa đăng nhập @{user}, nhưng cần @{want}. Máy KHÔNG giữ đăng nhập này.")
        print("      Bấm lại file .bat và đăng nhập đúng kênh.", flush=True)
        return False
    print(f"\n  OK: đã lưu đăng nhập Instagram" + (f" @{user}" if user else " (chưa đọc được tên tài khoản, máy sẽ tự kiểm lại)") + f" vào '{cookie}'.", flush=True)
    if not want:
        print("  (Tài khoản này CHƯA GHIM tên @ → xong thì bấm XAC_NHAN_TAI_KHOAN.bat để ghim.)", flush=True)
    return True


async def dang_nhap_threads(p, acc) -> bool:
    """Mo Chrome trang dang nhap Threads; dang nhap xong may tu doc ten @, dung kenh thi luu, sai thi khong giu."""
    import threads_dang as T
    cookie, want = acc["cookie"], M.ghim(acc)
    out = repo / "cookies" / f"threads_{cookie}.json"
    print("\n" + "=" * 66)
    print(f"  CẦN ĐĂNG NHẬP KÊNH THREADS:  @{want or '(chưa ghim tên @)'}")
    print("  Chrome sắp mở trang đăng nhập Threads. Bấm 'Tiếp tục bằng Instagram' hoặc gõ")
    print("  tên + mật khẩu Instagram của ĐÚNG kênh này. Xong không cần bấm gì, máy tự kiểm và lưu.")
    print(f"  Chờ tối đa {CHO_PHUT} phút.")
    print("=" * 66, flush=True)
    browser, ctx, page = await T.mo_trinh_duyet(p, None, headless=False)
    try:
        await page.goto(T.LOGIN, wait_until="domcontentloaded", timeout=120_000)
        han = time.time() + CHO_PHUT * 60
        while time.time() < han:
            await asyncio.sleep(3)
            try:
                if not await T.co_phien(ctx):
                    continue
            except Exception:
                continue
            print("\n  Đã thấy đăng nhập Threads, đang đọc tên tài khoản...", flush=True)
            await asyncio.sleep(5)
            user = None
            for _ in range(3):
                try:
                    if "/login" in page.url or "threads." not in page.url:
                        await page.goto(T.HOME, wait_until="domcontentloaded", timeout=60_000)
                    user = await T.doi_ten(page, 25, want)
                except Exception:
                    user = None
                if user:
                    break
                try:
                    await page.goto(T.HOME, wait_until="domcontentloaded", timeout=60_000)
                except Exception:
                    pass
            if user and want and not M.cung_ten(user, want):
                print(f"\n  !!! SAI KÊNH: vừa đăng nhập @{user}, nhưng cần @{want}. Máy KHÔNG lưu.")
                print("      Đăng nhập lại đúng kênh trên cửa sổ Chrome này.", flush=True)
                await ctx.clear_cookies()
                try:
                    await page.goto(T.LOGIN)
                except Exception:
                    pass
                continue
            luu_ban_cu(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            await T.luu_phien(ctx, out)
            if user:
                print(f"\n  OK: đã lưu đăng nhập Threads @{user} vào '{cookie}'.", flush=True)
            else:
                await T.ghi_chan_doan(page, "dang-nhap")
                print(f"\n  Đã lưu đăng nhập Threads vào '{cookie}', nhưng chưa đọc được tên @.")
                print("  Máy sẽ CHƯA đăng cho tới khi kiểm được đúng kênh. Báo Claude kiểm tra.", flush=True)
            return True
        print("\n  Hết giờ chờ, chưa đăng nhập được. Bấm lại file .bat để thử lại.", flush=True)
        return False
    finally:
        await browser.close()


async def main():
    args = sys.argv[1:]
    mang_chon = [m for m in ("tiktok", "instagram", "threads") if f"--{m}" in args] or ["tiktok", "instagram", "threads"]
    chon = [a for a in args if not a.startswith("--")]
    accs = [a for a in cfg["tai_khoan"] if isinstance(a, dict) and a.get("mang") in mang_chon and a.get("bat", True) and a.get("cookie")]
    for ten in chon:          # tai khoan moi chua co trong cau-hinh.json (goi tu 2_DANG_NHAP.bat)
        if not any(a["cookie"] == ten for a in accs) and len(mang_chon) == 1:
            accs.append({"mang": mang_chon[0], "cookie": ten, "_moi": True})
    todo = []
    print("Đang kiểm từng tài khoản (Instagram mất khoảng nửa phút)...", flush=True)
    for a in accs:
        if chon and a["cookie"] not in chon:
            continue
        a["ma"] = f"{a['mang']}_{a['cookie']}"
        st, user = ("chua_dang_nhap", None) if a.get("_moi") else M.check_login(cfg, a)
        print(f"  {a['mang']:<10}{a['cookie']:<16} cần @{M.ghim(a) or '?':<18} đang ở @{user or '-':<18} → {TEN_TT.get(st, st)}", flush=True)
        if a["cookie"] in chon or st in M.DN_CHAN:
            todo.append(a)
    if not todo:
        print("\nKhông có tài khoản nào cần đăng nhập lại. (Tài khoản 'không kiểm được' thường do mất mạng — thử lại sau.)")
        return
    tk = [a for a in todo if a["mang"] == "tiktok"]
    if tk:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            for a in tk:
                await dang_nhap_tiktok(p, a)
    for a in todo:
        if a["mang"] == "instagram":
            dang_nhap_instagram(a)
    th = [a for a in todo if a["mang"] == "threads"]
    if th:
        from patchright.async_api import async_playwright as apw
        async with apw() as p:
            for a in th:
                await dang_nhap_threads(p, a)
    moi = [a["cookie"] for a in todo if a.get("_moi")]
    if moi:
        print(f"\nTài khoản mới ({', '.join(moi)}): nhờ Claude thêm vào cau-hinh.json (kèm tên @) thì máy mới bắt đầu đăng.")
    print("\nĐang cập nhật bảng theo dõi...", flush=True)
    subprocess.run([sys.executable, str(HERE / "dang_mxh.py"), "--kiem-tra", "--chi-ghi"], cwd=str(repo))
    print("XONG. Video trong hàng chờ sẽ tự đăng ở khung giờ kế tiếp.")


asyncio.run(main())
