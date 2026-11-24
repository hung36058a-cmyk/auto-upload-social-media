# -*- coding: utf-8 -*-
"""
LICH DANG THEO THOI GIAN THAT: tao lich-dang.html (7 ngay qua + 7 ngay toi, moi mang moi kenh).
Chay tu dong cuoi moi luot thong_bao_mxh.py (10 phut/lan); trang tu tai lai moi 2 phut.
Nguon: trang-thai-mxh.json + du-lieu.json cua may dang (chi doc) + so lieu cua agent kiem 2 gio.
Ban chep: G:\\My Drive\\MXH - Trang thai\\lich-dang.html (mo tren may khac qua Drive).
"""
from __future__ import annotations

import datetime as dt
import html
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "chung"))
import mxh_chung as C  # noqa: E402

RA = HERE / "lich-dang.html"
NHAN = {"ok": ("Đã đăng", "ok"), "loi": ("Lỗi", "loi"), "chua_ro": ("Chưa rõ", "loi"), "bo_lo": ("Bỏ lỡ", "loi"),
        "het_video": ("Hết video", "loi"), "bi_chan": ("Bị chặn", "loi"), "sap_toi": ("Sắp đăng", "sap"),
        "dang_xu_ly": ("Đang đăng", "sap"), "thu_lai": ("Thử lại", "sap"), "cho_video": ("Chờ video", "sap"),
        "trong": ("Thiếu video", "loi")}


def so_lieu(s: dict | None) -> str:
    if not s:
        return ""
    phan = [f"{s[k]:,} {n}" for k, n in (("views", "xem"), ("likes", "tim"), ("comments", "bình luận"), ("shares", "chia sẻ"))
            if isinstance(s.get(k), int)]
    return " · ".join(phan) + (f" ({s['loi']})" if s.get("loi") else "")


def tao() -> Path:
    t = C.now()
    st = C.doc_json(C.STATUS, {}) or {}
    so = C.doc_json(C.SO_GHI, {}) or {}
    ts = C.doc_json(C.THONG_SO, {}) or {}
    tk = C.tai_khoan_bat()
    dong = []   # (luc, ten, trang_thai, file, link, so_lieu)
    tu, den = t - dt.timedelta(days=7), t + dt.timedelta(days=7)
    da_co = set()
    for h in so.get("lich_su", []):
        luc = C.parse_t(h.get("luc"))
        if luc and luc >= tu and h.get("kq") in ("ok", "loi", "chua_ro"):
            k = (h.get("tk"), h.get("file"), h.get("kq"))
            if k in da_co:
                continue            # 1 video loi nhieu lan thu -> 1 dong
            da_co.add(k)
            dong.append((luc, C.ten_tk(h["tk"], tk.get(h["tk"])), h["kq"], h.get("file"), h.get("link"),
                         so_lieu((ts.get("bai") or {}).get(h.get("link") or ""))))
    for a in st.get("tai_khoan", []):
        ten = C.ten_tk(a["ma"], tk.get(a["ma"]) or a)
        for r in a.get("hom_nay") or []:
            if r.get("trang_thai") in ("bo_lo", "het_video", "bi_chan", "dang_xu_ly", "thu_lai", "cho_video") and a["ma"] not in C.DANG_TAY:
                gio = dt.datetime.strptime(f"{st.get('ngay')} {r['gio']}", "%Y-%m-%d %H:%M").replace(tzinfo=C.TZ)
                dong.append((gio, ten, r["trang_thai"], r.get("du_kien") or r.get("file"), None, ""))
        for e in a.get("lich_toi") or []:
            luc = C.parse_t(e.get("luc")) or t
            if luc <= den and (e.get("file") or a["ma"] not in C.DANG_TAY):
                dong.append((luc, ten + ("" if e.get("luc") else " (lượt kế)"), "sap_toi" if e.get("file") else "trong",
                             e.get("file"), None, ""))
        for h in (a.get("hang_cho") or {}).get("hen_gio", []):
            luc = C.parse_t(h.get("gio"))
            if luc and luc > t:
                dong.append((luc, ten + " (hẹn giờ)", "sap_toi", h.get("file"), None, ""))
    for y in ts.get("youtube") or []:
        luc = C.parse_t(y.get("luc"))
        if luc and luc >= tu:
            dong.append((luc, f"{y.get('kenh')} · YouTube", "ok" if luc <= t else "sap_toi", y.get("tieu_de"), y.get("link"),
                         so_lieu(y)))
    dong.sort(key=lambda x: x[0])

    theo_ngay: dict[dt.date, list] = {}
    for d in dong:
        theo_ngay.setdefault(d[0].date(), []).append(d)
    def mo(lk):
        return f'<a href="{html.escape(lk)}" target="_blank">mở</a>' if lk else ""

    the = []
    for ngay in sorted(theo_ngay):
        hang = "".join(
            f"<tr class='{NHAN.get(s, (s, 'sap'))[1]}'><td>{l:%H:%M}</td><td>{html.escape(ten)}</td>"
            f"<td><b>{NHAN.get(s, (s, ''))[0]}</b></td><td>{html.escape(str(f or '—'))}</td>"
            f"<td>{html.escape(sl)}</td><td>{mo(lk)}</td></tr>"
            for l, ten, s, f, lk, sl in theo_ngay[ngay])
        tieu = "HÔM NAY · " if ngay == t.date() else ""
        the.append(f"<h2 id='{'homnay' if ngay == t.date() else ngay}'>{tieu}{ngay:%a %d/%m}</h2>"
                   f"<table><tr><th>Giờ</th><th>Kênh · Mạng</th><th>Trạng thái</th><th>Video</th><th>Số liệu</th><th></th></tr>{hang}</table>")
    trang = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta http-equiv="refresh" content="120">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Lịch đăng MXH</title><style>
body{{font:15px system-ui,sans-serif;margin:16px;background:#fafafa;color:#222}} table{{border-collapse:collapse;width:100%;background:#fff}}
td,th{{border-bottom:1px solid #eee;padding:6px 8px;text-align:left;vertical-align:top}} th{{background:#f0f0f0}}
tr.ok td:nth-child(3){{color:#137333}} tr.loi td:nth-child(3){{color:#c5221f}} tr.sap td:nth-child(3){{color:#1a5fb4}}
h2{{margin:22px 0 6px}} .tren{{color:#666}}</style></head><body>
<h1>Lịch đăng MXH</h1><p class="tren">Cập nhật {t:%d/%m %H:%M} · máy đăng ghi lúc {html.escape(str(st.get('cap_nhat_luc', '?')))}
· số liệu (agent 2 giờ) lúc {html.escape(str(ts.get('luc', 'chưa có')))} · <a href="#homnay">tới hôm nay</a></p>
{''.join(the) or '<p>Chưa có dữ liệu.</p>'}</body></html>"""
    RA.write_text(trang, encoding="utf-8")
    try:
        if C.DRIVE.exists():
            shutil.copyfile(RA, C.DRIVE / RA.name)
    except OSError:
        pass
    return RA


if __name__ == "__main__":
    print(tao())
