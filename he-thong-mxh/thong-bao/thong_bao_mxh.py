# -*- coding: utf-8 -*-
"""
THONG BAO GMAIL CHO MOI LAN DANG MXH (chay 10 phut/lan, lich Windows "ThongBaoMXH")
CHI DOC trang-thai-mxh.json cua may dang (khong sua may dang). Moi lan chay gom het su kien thanh 1 thu:
  - SAP DANG : con <= 35 phut toi gio dang (chay 10 phut/lan -> thu toi truoc 25-35 phut).
               Tai khoan "dang ngay" (dang khi co video) khong co gio truoc -> bao "luot ke, trong ~10 phut".
  - DA DANG  : bai co bang chung (link) trong lich su; kem "Da sua: ..." neu truoc do tai khoan co loi.
  - LOI      : dang loi / chua ro / bo lo khung / het video / dang nhap hong / loi he thong / may dang khong chay.
Tai khoan lay tu cau-hinh.json cua may dang -> them kenh moi la tu duoc bao, khong sua file nay.

  python thong_bao_mxh.py            chay 1 luot (gui that)
  python thong_bao_mxh.py --xem      in thu se gui, KHONG gui, KHONG ghi so da bao
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "chung"))
import mxh_chung as C  # noqa: E402

DL = HERE / "du-lieu"
SO_DA_BAO = DL / "da-bao.json"
GHI_CHU_SUA = DL / "ghi-chu-sua.json"      # dang_bu.py ghi: {ma_tk | "*": ["da sua gi"]}
TRUOC_PHUT = 35
MAY_CHET_PHUT = 30
GIU_NGAY = 10
TRANG_THAI_LOI = {"bo_lo": "BỎ LỠ khung giờ (máy không chạy lúc đó)",
                  "het_video": "HẾT video trong hàng chờ nên không đăng",
                  "bi_chan": "Bị CHẶN (đăng nhập sai / hết hạn) nên không đăng"}
SUA_XONG = r"Sửa xong: bấm đúp E:\01_YouTube\00_Dung-chung\he-thong-mxh\DA_SUA_XONG.bat → máy đăng bù ngay và gửi thư 'Đã đăng' kèm chỗ đã sửa."


def cach_sua(mang: str, loi: str) -> str:
    l = (loi or "").lower()
    bat = {"facebook": "DANG_NHAP_LAI_FACEBOOK.bat", "threads": "DANG_NHAP_THREADS.bat"}.get(mang, "DANG_NHAP_LAI.bat")
    if "đăng nhập" in l or "dang_nhap" in l or "het_han" in l or "sai_tai_khoan" in l or "sai tài khoản" in l:
        return rf"Đăng nhập lại: bấm đúp E:\01_YouTube\00_Dung-chung\dang-mxh\{bat} (đúng tài khoản)."
    if "bỏ lỡ" in l or "bo_lo" in l:
        return "Laptop tắt/ngủ lúc tới giờ. Để laptop bật, cắm sạc, tắt chế độ ngủ."
    if "hết video" in l or "het_video" in l:
        return "Bỏ thêm video vào hàng chờ (gọi skill làm video của kênh)."
    if "chưa rõ" in l or "không đăng lại" in l or "chua_ro" in l:
        return "Mở app/web xem bài đã lên chưa. ĐÃ lên thì thôi; CHƯA lên thì nói với Claude /dang-mxh để trả video về hàng chờ."
    return "Mở Claude Code, gõ /dang-mxh rồi dán thư này để Claude tìm và sửa."


def khoa(*phan) -> str:
    return "|".join(str(p) for p in phan)


def gom_su_kien(st: dict, so: dict, t: dt.datetime, tk_bat: dict) -> tuple[list, list, list]:
    """Tra ve (loi, da_dang, sap_dang): moi muc (khoa, ma_tk, chu)."""
    loi, ok, sap = [], [], []
    bat_dau = C.parse_t(so["bat_dau"])
    cap_nhat = C.parse_t(st.get("cap_nhat_luc"))
    if not cap_nhat or t - cap_nhat > dt.timedelta(minutes=MAY_CHET_PHUT):
        loi.append((khoa("chet", st.get("cap_nhat_luc")), "*",
                    f"MÁY ĐĂNG KHÔNG CHẠY: trạng thái cập nhật lần cuối {st.get('cap_nhat_luc')}. "
                    r"Kiểm laptop; mất lịch thì bấm đúp E:\01_YouTube\00_Dung-chung\dang-mxh\CAI_LICH_TU_DANG.bat."))
    for e in st.get("loi_he_thong") or []:
        loi.append((khoa("he", hashlib.md5(e.encode()).hexdigest()[:10]), "*", f"Lỗi hệ thống máy đăng: {e}"))

    for a in st.get("tai_khoan", []):
        ma, mang = a["ma"], a.get("mang", "")
        ten = C.ten_tk(ma, tk_bat.get(ma) or a)
        dn = a.get("dang_nhap") or {}
        tt = dn.get("trang_thai")
        if tt and tt not in ("ok", "chua_kiem_tra", "khong_ro"):
            chu = f"{ten}: đăng nhập lỗi ({tt}" + (f", đang ở @{dn['tai_khoan_that']}, cần @{dn.get('can')}" if dn.get("tai_khoan_that") and tt == "sai_tai_khoan" else "") + ")"
            loi.append((khoa("dn", ma, tt, dn.get("tai_khoan_that")), ma, chu + "\n   → " + cach_sua(mang, "dang_nhap")))
        tay = ma in C.DANG_TAY
        for r in a.get("hom_nay") or []:
            if r.get("trang_thai") in TRANG_THAI_LOI and not tay:
                chu = f"{ten} khung {r['gio']} hôm nay: {TRANG_THAI_LOI[r['trang_thai']]}" + (f" — {r['loi']}" if r.get("loi") else "")
                loi.append((khoa("tt", ma, st.get("ngay"), r["gio"], r["trang_thai"]), ma,
                            chu + "\n   → " + cach_sua(mang, r["trang_thai"])))
        hen = [{"luc": h["gio"], "file": h["file"]} for h in (a.get("hang_cho") or {}).get("hen_gio", [])]
        for e in (a.get("lich_toi") or []) + hen:
            s = C.parse_t(e.get("luc"))
            if s is None:          # tai khoan dang ngay: co video la dang luot ke
                if e.get("file"):
                    sap.append((khoa("sap", ma, e["file"]), ma, f"{ten}: lượt kế (~10 phút nữa) — {e['file']}"))
                continue
            con = (s - t).total_seconds() / 60
            if 0 < con <= TRUOC_PHUT:
                if e.get("file"):
                    sap.append((khoa("sap", ma, e["luc"], e["file"]), ma, f"{ten}: {s:%H:%M} (còn {int(con)} phút) — {e['file']}"))
                elif not tay:
                    loi.append((khoa("trong", ma, e["luc"]), ma,
                                f"{ten}: {s:%H:%M} (còn {int(con)} phút) tới giờ đăng nhưng hàng chờ HẾT video\n   → " + cach_sua(mang, "het_video")))

    for h in st.get("lich_su") or []:
        luc = C.parse_t(h.get("luc"))
        if not luc or (bat_dau and luc < bat_dau):
            continue
        ma = h.get("tk", "")
        ten = C.ten_tk(ma, tk_bat.get(ma))
        cap = (h.get("caption") or "").splitlines()[0][:90] if h.get("caption") else ""
        if h.get("kq") == "ok" and h.get("loi"):      # len bai duoc nhung may tu canh bao (vd dang nham trang)
            loi.append((khoa("okloi", ma, h["luc"]), ma, f"{ten} lúc {luc:%d/%m %H:%M}: ĐÃ LÊN nhưng có cảnh báo — {h['loi'][:300]}"
                        f"\n   Link: {h.get('link') or '?'}\n   → " + cach_sua(ma.split('_')[0], h["loi"])))
        if h.get("kq") == "ok":
            ok.append((khoa("ok", ma, h["luc"]), ma,
                       f"{ten} lúc {luc:%d/%m %H:%M} — {h.get('file')}\n   Tài khoản: {h.get('tai_khoan') or '?'}\n   Link: {h.get('link') or '(không có)'}"
                       + (f"\n   Caption: {cap}" if cap else "")))
        elif h.get("kq") in ("loi", "chua_ro"):
            nhan = "CHƯA RÕ đã lên chưa (máy không đăng lại để khỏi trùng)" if h["kq"] == "chua_ro" else "ĐĂNG LỖI"
            loi.append((khoa("loi", ma, h.get("file"), h["kq"], h["luc"]), ma,
                        f"{ten} lúc {luc:%d/%m %H:%M}: {nhan} — {h.get('file')}\n   Lý do: {(h.get('loi') or '?')[:300]}\n   → "
                        + cach_sua(ma.split('_')[0], (h.get("loi") or "") + " " + h["kq"])))
    return loi, ok, sap


def soan_thu(loi, ok, sap, da_sua: dict) -> tuple[str, str]:
    phan = []
    if loi:
        phan.append("❌ LỖI / KHÔNG ĐĂNG\n" + "\n".join(f"- {c}" for _, _, c in loi) + "\n\n" + SUA_XONG)
    if ok:
        dong = []
        for _, ma, c in ok:
            sua = da_sua.get(ma) or []
            dong.append(f"- {c}" + ("\n   ĐÃ SỬA: " + "; ".join(sua) if sua else ""))
        phan.append("✅ ĐÃ ĐĂNG\n" + "\n".join(dong))
    if sap:
        phan.append("⏰ SẮP ĐĂNG\n" + "\n".join(f"- {c}" for _, _, c in sap))
    nhan = [f"LỖI {len(loi)}" if loi else "", f"Đã đăng {len(ok)}" if ok else "", f"Sắp đăng {len(sap)}" if sap else ""]
    tieu_de = "[MXH] " + " · ".join(x for x in nhan if x)
    if ok:
        tieu_de += " — " + ", ".join(dict.fromkeys(C.ten_tk(m) for _, m, _ in ok))
    return tieu_de, "\n\n".join(phan) + "\n\nLịch đăng: E:\\01_YouTube\\00_Dung-chung\\he-thong-mxh\\lich\\lich-dang.html"


def chay(xem: bool = False) -> int:
    """Khoa 1 ban: lich 10 phut va DA_SUA_XONG chay cung luc thi ban sau doi toi 2 phut, khong gui trung."""
    DL.mkdir(parents=True, exist_ok=True)
    khoa_file = DL / ".dang-chay"
    for _ in range(24):
        try:
            os.close(os.open(str(khoa_file), os.O_CREAT | os.O_EXCL))
            break
        except FileExistsError:
            if time.time() - khoa_file.stat().st_mtime > 600:     # khoa rac cua lan chay chet giua chung
                khoa_file.unlink(missing_ok=True)
            time.sleep(5)
    else:
        return 0
    try:
        return _chay(xem)
    finally:
        khoa_file.unlink(missing_ok=True)


def _chay(xem: bool) -> int:
    t = C.now()
    so = C.doc_json(SO_DA_BAO, None)
    lan_dau = so is None
    if lan_dau:   # lan dau: chi bao viec tu bay gio, khong gui ca lich su cu
        so = {"bat_dau": t.isoformat(), "da_bao": {}, "loi_mo": {}}
    st = C.doc_json(C.STATUS, None)
    tk_bat = C.tai_khoan_bat()
    if st is None:
        loi, ok, sap = [(khoa("khong_doc", t.date()), "*", f"Không đọc được {C.STATUS} (máy đăng chưa chạy hoặc file hỏng).")], [], []
    else:
        loi, ok, sap = gom_su_kien(st, so, t, tk_bat)
    da_bao = so["da_bao"]
    loi, ok, sap = ([x for x in ds if x[0] not in da_bao] for ds in (loi, ok, sap))

    # loi mo theo tai khoan -> khi tai khoan dang duoc lai thi ghi "da sua" vao thu Da dang
    ghi_chu = C.doc_json(GHI_CHU_SUA, {}) or {}
    da_sua = {}
    for _, ma, _ in ok:
        mo = so["loi_mo"].get(ma, []) + so["loi_mo"].get("*", [])
        tay = ghi_chu.get(ma, []) + ghi_chu.get("*", [])
        if mo or tay:
            da_sua[ma] = tay + [f"hết lỗi trước đó: {m}" for m in mo][:3]
    if not (loi or ok or sap):
        if not xem:
            C.ghi_json(SO_DA_BAO, so)
        return 0
    tieu_de, noi_dung = soan_thu(loi, ok, sap, da_sua)
    if xem:
        print(tieu_de + "\n\n" + noi_dung)
        return 0
    import gmail
    gmail.gui(tieu_de, noi_dung)           # da xep vao hop thu cho -> coi nhu da bao (gui bu neu loi mang)
    for k, _, _ in loi + ok + sap:
        da_bao[k] = t.isoformat()
    for k, ma, c in loi:
        so["loi_mo"][ma] = (so["loi_mo"].get(ma, []) + [c.split("\n")[0][:120]])[-5:]
    for ma in da_sua:
        so["loi_mo"].pop(ma, None)
        ghi_chu.pop(ma, None)
    if da_sua:
        so["loi_mo"].pop("*", None)
        ghi_chu.pop("*", None)
        C.ghi_json(GHI_CHU_SUA, ghi_chu)
    han = t - dt.timedelta(days=GIU_NGAY)
    so["da_bao"] = {k: v for k, v in da_bao.items() if (C.parse_t(v) or t) > han}
    C.ghi_json(SO_DA_BAO, so)
    return len(loi)


def _lich() -> None:
    sys.path.insert(0, str(HERE.parent / "lich"))
    import lich_dang
    lich_dang.tao()


if __name__ == "__main__":
    C.chay_an_toan("thong_bao_mxh", lambda: chay("--xem" in sys.argv), DL)
    C.chay_an_toan("lich_dang", _lich, DL)     # lich hong khong duoc chan thu bao
