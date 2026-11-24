# -*- coding: utf-8 -*-
"""Do dung chung cho cac bot MXH (thong bao Gmail, kiem 2 gio, lich dang).
Moi duong dan may dang nam O DAY: doi thu muc may dang thi chi sua file nay."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

TZ = dt.timezone(dt.timedelta(hours=8))                       # gio Dai Loan
GOC = Path(__file__).resolve().parents[2]                     # goc repo (E:\01_YouTube\00_Dung-chung)
DANG_MXH = GOC / "dang-mxh"                                   # may tu dang
STATUS = DANG_MXH / "trang-thai-mxh.json"                     # may dang ghi 10 phut/lan
SO_GHI = DANG_MXH / "du-lieu.json"                            # so ghi may dang (CHI DOC)
CAU_HINH = DANG_MXH / "cau-hinh.json"                         # danh sach tai khoan = nguon duy nhat
KIEM_TRA = GOC / "kiem-tra-mxh" / "kiem_tra_mxh.py"
YTDATA = Path(r"E:\08_AI-chung\phan-tich-mxh\ytdata")           # token YouTube cua repo phan tich (ngoai repo nay)
THONG_SO = GOC / "he-thong-mxh" / "kiem-2-gio" / "du-lieu" / "thong-so.json"
DRIVE = Path(r"G:\My Drive\MXH - Trang thai")

# Tai khoan nguoi dung DANG TAY (may van bat nhung khong co video): khong bao "het video / bo lo" (giong kiem_dong_bo.TAM_DUNG_TAY)
DANG_TAY = {"tiktok_econlazypack"}

TEN_MANG = {"tiktok": "TikTok", "instagram": "Instagram", "threads": "Threads",
            "facebook": "Fanpage Facebook", "youtube": "YouTube"}


def now() -> dt.datetime:
    return dt.datetime.now(TZ).replace(microsecond=0)


def parse_t(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        t = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=TZ)


def doc_json(p: Path, mac_dinh=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return mac_dinh


def ghi_json(p: Path, data) -> None:
    """Ghi qua file tam roi doi ten: mat dien giua chung khong lam hong file."""
    p.parent.mkdir(parents=True, exist_ok=True)
    tam = p.with_name(p.name + ".tam")
    tam.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tam, p)


def ma_tk(acc: dict) -> str:
    """Cung cach dat ma cua dang_mxh.py: <mang>_<cookie>."""
    return f"{acc['mang']}_{acc['cookie']}"


def tai_khoan_bat() -> dict:
    """{ma: khoi cau hinh} cac tai khoan dang BAT. Them kenh moi vao cau-hinh.json la tu co ở moi bot."""
    cfg = doc_json(CAU_HINH, {}) or {}
    return {ma_tk(a): a for a in cfg.get("tai_khoan", []) if a.get("bat") and a.get("mang") and a.get("cookie")}


def chay_an_toan(ten: str, ham, thu_muc: Path) -> None:
    """Chay bang pythonw (khong cua so): loi -> ghi loi-chay.log + Gmail toi da 1 thu/ngay, khong chet im."""
    try:
        ham()
    except Exception:  # noqa: BLE001
        import traceback
        thu_muc.mkdir(parents=True, exist_ok=True)
        log = thu_muc / "loi-chay.log"
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\n{now().isoformat()} {ten}\n{traceback.format_exc()}")
        dau = thu_muc / f"loi-chay-da-bao-{now():%Y%m%d}"
        if not dau.exists():
            dau.touch()
            import gmail
            gmail.gui(f"[MXH] BOT {ten} BỊ LỖI", f"Bot {ten} chạy lỗi, có thể đang không báo/kiểm gì.\n"
                      f"Xem {log}\nMở Claude Code trong thư mục quan-ly-he-thong, dán thư này.\n\n{traceback.format_exc()[-1500:]}")


def ten_tk(ma: str, acc: dict | None = None) -> str:
    acc = acc or {}
    mang = acc.get("mang") or ma.split("_")[0]
    return f"{acc.get('kenh') or ma.split('_', 1)[-1]} · {TEN_MANG.get(mang, mang)}"
