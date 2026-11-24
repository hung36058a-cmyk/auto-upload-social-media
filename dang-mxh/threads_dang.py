# -*- coding: utf-8 -*-
r"""DANG VIDEO LEN THREADS (threads.com) BANG CHROME - dung chung cho dang_mxh.py / dang_nhap_lai.py
File dang nhap: social-auto-upload\cookies\threads_<cookie>.json (storage_state cua Chrome).

Lenh tay (chay bang .venv cua social-auto-upload):
  python threads_dang.py whoami <cookie>                 in 'tai_khoan: <ten>' (0 = ok, 1 = het han, 2 = khong ro)
  python threads_dang.py upload <cookie> <video> <txt> <ten@ can> <file danh dau da bam>
  python threads_dang.py chan-doan <cookie> [video]      KHONG dang: mo trang, thu mo khung soan bai (va gan video neu co),
                                                         chup man hinh + luu HTML vao dang-mxh\chan-doan\threads-*.png/html
Dau ra cho may doc: 'tai_khoan: x' · 'link: https://...' · 'LOI_DANG: MA: chi tiet'
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = "https://www.threads.com/"
LOGIN = "https://www.threads.com/login"
GIOI_HAN_KY_TU = 500

RX_SOAN = re.compile(r"^(What's new\?|What’s new\?|Start a thread|有什麼新鮮事？?|有什么新鲜事？?|Có gì mới\?)", re.I)
RX_TAO = re.compile(r"^(Create|建立|创建|Tạo)$", re.I)
RX_POST = re.compile(r"^(Post|發佈|发布|發布|Đăng)$", re.I)
RX_DANG_NHAP = re.compile(r"^(Log in|登入|登录|Đăng nhập)$", re.I)


def ra(s: str) -> None:
    print(s, flush=True)


def doc_caption(txt: str) -> str:
    raw = Path(txt).read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp950", "cp1258"):
        try:
            return raw.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace").strip()


def lam_caption(text: str, cuoi: str = "") -> str:
    """Threads: toi da 500 ky tu; BO het hashtag (go '#' tren Threads bat bang chon chu de, de gay ket/chon nham)."""
    than = re.sub(r"[ \t]*#[^\s#]+", "", text)
    than = "\n".join(l.rstrip() for l in than.splitlines())
    than = re.sub(r"\n{3,}", "\n\n", than).strip()
    cuoi = (cuoi or "").strip()
    cho = GIOI_HAN_KY_TU - (len(cuoi) + 2 if cuoi else 0)
    if len(than) > cho:
        than = than[:cho - 1].rstrip() + "…"
    return than + (("\n\n" + cuoi) if cuoi else "")


async def mo_trinh_duyet(p, cookie_file: Path | None, headless: bool):
    browser = await p.chromium.launch(channel="chrome", headless=headless, args=["--lang=en-US"])
    kw = {"locale": "en-US", "viewport": {"width": 1280, "height": 900}}
    if cookie_file and cookie_file.exists():
        kw["storage_state"] = str(cookie_file)
    ctx = await browser.new_context(**kw)
    page = await ctx.new_page()
    page.set_default_timeout(30_000)
    return browser, ctx, page


async def ten_dang_nhap(page) -> str | None:
    """Ten @ cua tai khoan dang dang nhap (doc tu link 'Profile' o thanh ben trai). None = chua dang nhap / chua thay."""
    return await page.evaluate(r"""() => {
      const ok = h => /^\/@[A-Za-z0-9_.]+\/?$/.test(h || '');
      const pick = a => (a.getAttribute('href') || '').replace(/^\/@/, '').replace(/\/$/, '');
      // 1) link ho so trong thanh dieu huong: co icon svg (aria-label Profile / 個人檔案 ...) va khong co anh dai dien nguoi khac
      const nav = [...document.querySelectorAll('a[href^="/@"]')].filter(a => ok(a.getAttribute('href')));
      for (const a of nav) {
        const lab = (a.getAttribute('aria-label') || '') + ' ' + [...a.querySelectorAll('svg[aria-label]')].map(s => s.getAttribute('aria-label')).join(' ')
                    + ' ' + [...a.querySelectorAll('svg title')].map(t => t.textContent).join(' ');
        if (/profile|個人檔案|个人主页|trang cá nhân/i.test(lab)) return pick(a);
      }
      for (const a of nav) {
        if (a.closest('nav') && a.querySelector('svg') && !a.innerText.trim()) return pick(a);
      }
      return null;
    }""")


async def co_phien(ctx) -> bool:
    """Da dang nhap Threads chua (theo cookie sessionid cua threads.com/threads.net)."""
    return any(c["name"] == "sessionid" and c.get("value") and "threads" in c.get("domain", "")
               for c in await ctx.cookies())


async def tim_ten(page, want: str = "") -> str | None:
    """Ten @ dang dang nhap: link Profile o thanh ben; khong thay thi do trong du lieu trang co dung ten can khong."""
    u = await ten_dang_nhap(page)
    if u:
        return u
    if want and await co_phien(page.context):
        html = await page.content()
        if re.search(r'"username"\s*:\s*"' + re.escape(want) + '"', html):
            return want
    return None


async def ghi_chan_doan(page, ten: str) -> None:
    try:
        d = HERE / "chan-doan"
        d.mkdir(exist_ok=True)
        await page.screenshot(path=str(d / f"threads-{ten}.png"))
        (d / f"threads-{ten}.html").write_text(await page.content(), encoding="utf-8")
    except Exception:
        pass


async def la_chua_dang_nhap(page) -> bool:
    if "/login" in page.url:
        return True
    btn = page.get_by_role("link", name=RX_DANG_NHAP).or_(page.get_by_role("button", name=RX_DANG_NHAP))
    return await btn.count() > 0 and not await ten_dang_nhap(page)


async def doi_ten(page, giay: int = 45, want: str = "") -> str | None:
    han = time.time() + giay
    while time.time() < han:
        u = await tim_ten(page, want)
        if u:
            return u
        if await la_chua_dang_nhap(page) and time.time() > han - giay + 15:
            return None
        await asyncio.sleep(1.5)
    return None


async def luu_phien(ctx, cookie_file: Path) -> None:
    tmp = cookie_file.with_suffix(".json.tmp")
    await ctx.storage_state(path=str(tmp))
    os.replace(tmp, cookie_file)


# ------------------------------------------------------------------ whoami
async def whoami(cookie_file: Path, want: str = "") -> int:
    if not cookie_file.exists():
        ra("THREADS_HET_HAN: chua co file dang nhap")
        return 1
    from patchright.async_api import async_playwright
    async with async_playwright() as p:
        browser, ctx, page = await mo_trinh_duyet(p, cookie_file, headless=True)
        try:
            await page.goto(HOME, wait_until="domcontentloaded", timeout=120_000)
            user = await doi_ten(page, want=want)
            if not user:
                await ghi_chan_doan(page, "whoami")
                if not await co_phien(ctx) or await la_chua_dang_nhap(page):
                    ra("THREADS_HET_HAN")
                    return 1
                ra("THREADS_KHONG_RO: khong doc duoc ten tai khoan")
                return 2
            await luu_phien(ctx, cookie_file)
            ra(f"tai_khoan: {user}")
            return 0
        finally:
            await browser.close()


# ------------------------------------------------------------------ dang bai
RX_HUY = re.compile(r"^(Cancel|取消|Hủy)$")


async def dem_hop_thoai(page) -> dict:
    return {"dialog": await page.locator('[role="dialog"]').count(),
            "o_soan": await page.locator('[role="dialog"] [contenteditable="true"]').count(),
            "o_soan_trang": await page.locator('[contenteditable="true"]').count()}


async def mo_khung_soan(page):
    """Bam 'What's new?' -> cho hop thoai (laptop cham: toi 60 giay, kiem bang dem phan tu). Tra ve locator hop thoai."""
    dlg = page.locator('[role="dialog"]').last
    loi = []
    for lan in range(2):
        try:
            if not await page.locator('[role="dialog"] [contenteditable="true"]').count():
                nut = page.get_by_text(RX_SOAN).first
                if not await nut.count():
                    nut = page.get_by_role("img", name=re.compile(r"^(New thread|新串文|Thread mới)$")).first
                await nut.click(timeout=30_000)
            han = time.time() + 60
            while time.time() < han:
                if await page.locator('[role="dialog"] [contenteditable="true"]').count():
                    await asyncio.sleep(2)
                    return dlg
                await asyncio.sleep(1)
            raise RuntimeError(f"het 60s, dem: {await dem_hop_thoai(page)}")
        except Exception as e:
            loi.append(str(e).splitlines()[0][:120])
            await page.goto(HOME, wait_until="domcontentloaded", timeout=120_000)
            await asyncio.sleep(8)
    raise RuntimeError("KHONG_MO_DUOC_KHUNG_SOAN: " + " | ".join(loi)[:300])


O_SOAN = '[role="dialog"] [contenteditable="true"]'
NUT_POST = ('xpath=//div[@role="button"][normalize-space()="Post" or normalize-space()="發佈" '
            'or normalize-space()="发布" or normalize-space()="Đăng"]')   # .last = nut trong hop thoai (hop thoai nam cuoi trang)


async def go_caption(page, dlg, caption: str) -> None:
    o = page.locator(O_SOAN).first
    await o.click(timeout=20_000)
    dong = caption.split("\n")
    for i, l in enumerate(dong):
        if l:
            await page.keyboard.insert_text(l)
        if i < len(dong) - 1:
            await page.keyboard.press("Enter")
    await asyncio.sleep(1.5)
    if not await page.locator(O_SOAN).count():
        raise RuntimeError("KHUNG_SOAN_BI_DONG: hop thoai soan bai bi dong khi go caption")


async def gan_video(page, dlg, video: str) -> None:
    """Bam nut 'Attach media' trong hop thoai va chon file qua cua so chon file; khong duoc thi dat thang vao o input."""
    loi = []
    icon = page.locator('xpath=//*[@role="dialog"]//*[name()="svg"][./*[name()="title" and '
                        '(normalize-space()="Attach media" or normalize-space()="附加媒體" or normalize-space()="Đính kèm file phương tiện")]]').first
    if await icon.count():
        nut = icon.locator('xpath=ancestor::*[@role="button"][1]')
        bam = nut if await nut.count() else icon
        try:
            async with page.expect_file_chooser(timeout=20_000) as fc:
                await bam.click(timeout=15_000)
            await (await fc.value).set_files(video)
            return
        except Exception as e:
            loi.append("chooser: " + str(e).splitlines()[0][:100])
    else:
        loi.append("khong thay icon Attach media")
    try:
        await page.locator('[role="dialog"] input[type="file"], input[type="file"][accept*="video"]').first.set_input_files(video, timeout=20_000)
        return
    except Exception as e:
        loi.append("input: " + str(e).splitlines()[0][:100])
    raise RuntimeError("KHONG_GAN_DUOC_VIDEO: " + " | ".join(loi))


async def nut_post(dlg):
    return dlg.page.locator(NUT_POST).last


async def doi_nut_post_san_sang(dlg, phut: int = 15):
    han = time.time() + phut * 60
    while time.time() < han:
        b = await nut_post(dlg)
        if await b.count() and await b.get_attribute("aria-disabled") != "true" and await b.is_enabled():
            await asyncio.sleep(2)
            return b
        await asyncio.sleep(3)
    raise RuntimeError(f"VIDEO_CHUA_TAI_XONG: sau {phut} phut nut Post van chua bam duoc")


async def tim_bai_moi(page, user: str, tu_luc: float, doan: str, phut: int = 8) -> str | None:
    """Mo trang ca nhan, tim bai tao sau 'tu_luc' co chua doan dau caption. Tra link bai hoac None."""
    han = time.time() + phut * 60
    js = r"""([tu, doan]) => {
      const out = [];
      for (const t of document.querySelectorAll('time[datetime]')) {
        const ms = Date.parse(t.getAttribute('datetime'));
        if (!(ms >= tu)) continue;
        const a = t.closest('a[href*="/post/"]');
        if (!a) continue;
        let box = a; for (let i = 0; i < 12 && box.parentElement; i++) { box = box.parentElement; if ((box.innerText || '').includes(doan)) break; }
        if ((box.innerText || '').includes(doan)) out.push(a.href.split('?')[0]);
      }
      return out;
    }"""
    while time.time() < han:
        try:
            await page.goto(f"https://www.threads.com/@{user}", wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(6)
            links = await page.evaluate(js, [int((tu_luc - 120) * 1000), doan])
            if links:
                return links[0]
        except Exception:
            pass
        await asyncio.sleep(30)
    return None


async def upload(cookie_file: Path, video: str, txt: str, want: str, dau: str, headless: bool, cuoi: str = "") -> int:
    from patchright.async_api import async_playwright
    if not cookie_file.exists():
        ra("LOI_DANG: HET_HAN_DANG_NHAP: chua co file dang nhap Threads")
        return 1
    caption = lam_caption(doc_caption(txt), cuoi)
    doan = next((l.strip() for l in caption.splitlines() if l.strip()), "")[:18]
    async with async_playwright() as p:
        browser, ctx, page = await mo_trinh_duyet(p, cookie_file, headless=headless)
        try:
            await page.goto(HOME, wait_until="domcontentloaded", timeout=120_000)
            user = await doi_ten(page, want=want)
            if not user:
                await ghi_chan_doan(page, "upload-dang-nhap")
                ra("LOI_DANG: HET_HAN_DANG_NHAP: Threads khong cho biet dang dang nhap tai khoan nao")
                return 1
            ra(f"tai_khoan: {user}")
            if want and user.lower() != want.lower():
                ra(f"LOI_DANG: SAI_TAI_KHOAN: dang o @{user}, can @{want}")
                return 1
            await luu_phien(ctx, cookie_file)
            dlg = await mo_khung_soan(page)
            if video:                      # rong = bai chi co chu
                await gan_video(page, dlg, video)
            await go_caption(page, dlg, caption)
            await asyncio.sleep(10)
            tu_luc = time.time()
            # Nut Post bi mo (chua bam duoc) khi video dang tai len -> bam lai moi 10 giay cho toi khi hop thoai dong (toi da 15 phut)
            han = time.time() + 15 * 60
            while await page.locator(O_SOAN).count():
                if time.time() > han:
                    raise RuntimeError("VIDEO_CHUA_TAI_XONG: sau 15 phut bam Post van khong dang duoc")
                Path(dau).write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")
                try:
                    await (await nut_post(dlg)).click(timeout=10_000)
                except Exception:
                    pass
                await asyncio.sleep(10)
            ra("DA_BAM_POST")
            # Threads hien thong bao "Posted · View" khi xong; video lon co the mat vai phut
            link = None
            try:
                v = page.locator('xpath=//a[contains(@href,"/post/")][normalize-space()="View" or normalize-space()="查看" or normalize-space()="Xem"]').first
                await v.wait_for(state="visible", timeout=240_000)
                link = (await v.get_attribute("href") or "").split("?")[0]
                if link.startswith("/"):
                    link = "https://www.threads.com" + link
            except Exception:
                pass
            if not link:
                link = await tim_bai_moi(page, user, tu_luc, doan)
            try:
                await luu_phien(ctx, cookie_file)
            except Exception:
                pass
            if not link:
                ra("LOI_DANG: KHONG_XAC_NHAN: da bam Post nhung khong tim thay bai moi tren trang ca nhan")
                return 1
            ra(f"link: {link}")
            return 0
        except Exception as e:
            msg = (str(e).strip().splitlines() or [""])[0][:300]
            ra("LOI_DANG: " + (msg if isinstance(e, RuntimeError) else f"{type(e).__name__}: {msg}"))
            return 1
        finally:
            await browser.close()


# ------------------------------------------------------------------ chan doan (khong dang)
async def chan_doan(cookie_file: Path, video: str | None) -> int:
    from patchright.async_api import async_playwright
    out = HERE / "chan-doan"
    out.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser, ctx, page = await mo_trinh_duyet(p, cookie_file, headless=False)
        try:
            await page.goto(HOME, wait_until="domcontentloaded", timeout=120_000)
            await asyncio.sleep(8)
            ra(f"url: {page.url}")
            ra(f"tai_khoan: {await ten_dang_nhap(page)}")
            ra("links @: " + json.dumps(await page.evaluate("""() => [...document.querySelectorAll('a[href^="/@"]')].slice(0,15).map(a => [a.getAttribute('href'), a.getAttribute('aria-label'), [...a.querySelectorAll('svg[aria-label]')].map(s=>s.getAttribute('aria-label')).join('|'), !!a.closest('nav')])"""), ensure_ascii=False))
            await page.screenshot(path=str(out / "threads-1-trang-chu.png"))
            try:
                await page.get_by_text(RX_SOAN).first.click(timeout=20_000)
                await asyncio.sleep(15)
                ra(f"sau khi bam What's new (15s): {await dem_hop_thoai(page)}")
            except Exception as e:
                ra(f"bam What's new loi: {str(e)[:150]}")
            (out / "threads-1-trang-chu.html").write_text(await page.content(), encoding="utf-8")
            try:
                dlg = await mo_khung_soan(page)
                ra("khung_soan: OK")
                ra("file inputs: " + str(await dlg.locator('input[type="file"]').count()) + " / trang: " + str(await page.locator('input[type="file"]').count()))
                ra("svg titles: " + json.dumps(await dlg.locator("svg title").all_inner_texts(), ensure_ascii=False))
                (out / "threads-2a-hop-thoai.html").write_text(await page.content(), encoding="utf-8")
                if video:
                    await gan_video(page, dlg, video)
                    await go_caption(page, dlg, lam_caption("thu chan doan - KHONG DANG\n\n#test #abc"))
                    await asyncio.sleep(20)
                b = await nut_post(dlg)
                ra(f"nut_post: count={await b.count()} aria-disabled={await b.get_attribute('aria-disabled') if await b.count() else '-'}")
                ra(f"nut_post vi tri: {await b.bounding_box() if await b.count() else '-'}  (trong hop thoai: y > 500)")
                await page.screenshot(path=str(out / "threads-2-khung-soan.png"))
                (out / "threads-2-khung-soan.html").write_text(await page.content(), encoding="utf-8")
            except Exception as e:
                ra(f"khung_soan: LOI {e}")
                await page.screenshot(path=str(out / "threads-2-khung-soan.png"))
                (out / "threads-2-khung-soan.html").write_text(await page.content(), encoding="utf-8")
            return 0
        finally:
            await browser.close()


def main(argv: list[str]) -> int:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(errors="replace", encoding="utf-8")
        except Exception:
            pass
    sys.path.insert(0, str(HERE))
    import dang_mxh as M
    cfg = M.load_cfg()
    repo = Path(cfg["repo"])
    os.chdir(repo)
    lenh, cookie = argv[0], argv[1]
    cf = repo / "cookies" / f"threads_{cookie}.json"
    if lenh == "whoami":
        try:
            return asyncio.run(whoami(cf, argv[2] if len(argv) > 2 else ""))
        except Exception as e:
            ra(f"THREADS_KHONG_RO: {type(e).__name__}: {str(e)[:200]}")
            return 2
    if lenh == "upload":
        video, txt, want, dau = argv[2:6]
        cuoi = argv[6] if len(argv) > 6 else ""
        return asyncio.run(upload(cf, video, txt, want, dau, bool(cfg.get("threads_an_trinh_duyet", False)), cuoi))
    if lenh == "chan-doan":
        return asyncio.run(chan_doan(cf, argv[2] if len(argv) > 2 else None))
    ra("lenh khong ro")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
