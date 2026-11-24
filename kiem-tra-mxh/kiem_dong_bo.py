# -*- coding: utf-8 -*-
"""
KIEM DONG BO KENH MXH - chay 2 GIO/LAN (tac vu Claude "kiem-dang-mxh-2-gio"), ban 1.0 (22/11/2026)
  (bao qua Gmail - he-thong-mxh/chung/gmail.py)

Kiem:
  1. Video da len 1 mang trong nhom kenh nhung mang khac (dang bat) chua len sau X gio  -> LECH
     (khong co trong hang cho mang do = skill quen bo vao; co trong hang cho = dang ket)
  2. Video skill da lam (04_econlazypack/Video/NN_*) > 2 gio ma chua vao hang cho nao
  3. File nam trong thu muc loi/
  4. Dang nhap khong "ok" (het han / sai tai khoan / khong kiem duoc)
  5. May dang khong chay (trang-thai-mxh.json cu hon 40 phut)
  6. Tai khoan dang theo khung gio ma hang cho rong (het video cho khung ke)
Tai khoan khong nhan video nao trong 4 ngay (vd TikTok econ dang tam dung) -> coi la tam dung, khong bao lech.

Chay:  python kiem_dong_bo.py [--khong-gui] [--in] [--khong-thu]
  --khong-thu: in van de moi dang JSON, luu so, KHONG gui thu (tac vu Claude kiem-dang-mxh-2-gio gui 1 thu gop)
Trang thai: kiem-tra-mxh/dong-bo-trang-thai.json ; bao cao moi nhat: kiem-tra-mxh/dong-bo-moi-nhat.json
Gui bao qua Gmail (he-thong-mxh/chung/gmail.py).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

TZ = dt.timezone(dt.timedelta(hours=8))
GOC = Path(r"E:\01_YouTube")
DANG = GOC / "00_Dung-chung" / "dang-mxh"
HERE = Path(__file__).resolve().parent
TRANG_THAI = HERE / "dong-bo-trang-thai.json"
MOI_NHAT = HERE / "dong-bo-moi-nhat.json"

# Nhom kenh: tai khoan nao phai co cung video. Gio = tre toi da (gio) sau lan dang dau tien trong nhom.
NHOM = {
    "經濟懶人包": {"instagram_ecolazypack": 14, "threads_econlazypack": 36,
                 "facebook_fb_econ": 3, "tiktok_econlazypack": 14},
    "Vietwan": {"tiktok_vietwan": 3, "facebook_fb_vietwan": 3},
}
TEN_MANG = {"instagram": "Instagram", "threads": "Threads", "facebook": "Facebook",
            "tiktok": "TikTok", "youtube": "YouTube"}
# Tai khoan chu kenh dang cho nghi (khong nhac "het video"). TikTok econ: tuan tam dung tu 17/11/2026.
TAM_DUNG_TAY = {"tiktok_econlazypack"}
NGAY_XET = 4         # chi xet video xuat hien trong 4 ngay gan nhat
VIDEO_EXT = {".mp4", ".mov"}
TIEN_TO = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{4}_")


def bay_gio() -> dt.datetime:
    return dt.datetime.now(TZ)


def doc_json(p: Path, md=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return md


def khoa(ten: str) -> str:
    """Ten goc cua video: bo tien to ngay-gio dang (co the lap), bo duoi."""
    s = ten
    while TIEN_TO.match(s):
        s = TIEN_TO.sub("", s, count=1)
    s = re.sub(r"\.(mp4|mov)$", "", s, flags=re.I)
    return s.lower()


def gio_tien_to(ten: str) -> dt.datetime | None:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})_", ten)
    if not m:
        return None
    y, mo, d, h, mi = map(int, m.groups())
    return dt.datetime(y, mo, d, h, mi, tzinfo=TZ)


def mtime(p: Path) -> dt.datetime:
    return dt.datetime.fromtimestamp(p.stat().st_mtime, TZ)


def ten_tk(ma: str) -> str:
    mang = ma.split("_", 1)[0]
    return f"{TEN_MANG.get(mang, mang)} ({ma.split('_', 1)[1]})"


def quet_tai_khoan(thu_muc: Path, tu: dt.datetime) -> dict:
    """{khoa: {'da_dang': datetime|None, 'cho': bool, 'loi': bool, 'thay': datetime}}"""
    kq: dict[str, dict] = {}
    for sub in ("da-dang", "cho-dang", "loi"):
        d = thu_muc / sub
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if not f.is_file() or f.suffix.lower() not in VIDEO_EXT:
                continue
            k = khoa(f.name)
            luc = (gio_tien_to(f.name) if sub == "da-dang" else None) or mtime(f)
            if sub in ("da-dang", "loi") and luc < tu:
                continue
            r = kq.setdefault(k, {"da_dang": None, "cho": False, "loi": False, "thay": luc})
            r["thay"] = min(r["thay"], luc)
            if sub == "da-dang":
                r["da_dang"] = luc if r["da_dang"] is None else min(r["da_dang"], luc)
            elif sub == "cho-dang":
                r["cho"] = True
            else:
                r["loi"] = True
    return kq


def kiem() -> tuple[list[dict], dict]:
    now = bay_gio()
    tu = now - dt.timedelta(days=NGAY_XET)
    cfg = doc_json(DANG / "cau-hinh.json", {}) or {}
    tt = doc_json(DANG / "trang-thai-mxh.json", {}) or {}
    vande: list[dict] = []

    def them(ma_vd: str, muc: str, chu: str):
        vande.append({"ma": ma_vd, "muc": muc, "chu": chu})

    tk_cfg = {}
    for t in cfg.get("tai_khoan", []):
        ma = t.get("ma") or f"{t.get('mang')}_{t.get('cookie')}"
        tk_cfg[ma] = t

    # 5. may dang con chay?
    cap = tt.get("cap_nhat_luc")
    try:
        cap_luc = dt.datetime.fromisoformat(cap) if cap else None
    except Exception:
        cap_luc = None
    if not cap_luc or (now - cap_luc).total_seconds() > 40 * 60:
        them("may_tat", "LOI", f"Máy tự đăng không chạy: cập nhật cuối {cap or 'không rõ'} (laptop tắt/ngủ hoặc task DangMXH mất).")

    # 4 + 6. dang nhap, hang cho rong
    for t in tt.get("tai_khoan", []):
        ma = t.get("ma")
        if not ma or not tk_cfg.get(ma, {}).get("bat", False):
            continue
        dn = (t.get("dang_nhap") or {}).get("trang_thai")
        if dn and dn != "ok":
            them(f"dang_nhap:{ma}", "LOI", f"{ten_tk(ma)}: đăng nhập '{dn}' → máy không đăng được. Bấm file DANG_NHAP_LAI tương ứng.")
        hc = t.get("hang_cho") or {}
        if ma in TAM_DUNG_TAY:
            continue
        if t.get("khung_gio") and not t.get("dang_ngay") and hc.get("san_sang", 0) == 0:
            them(f"het_video:{ma}:{now:%Y-%m-%d}", "NHAC", f"{ten_tk(ma)}: hàng chờ hết video, khung giờ kế sẽ bỏ trống.")

    # quet thu muc tung tai khoan
    du_lieu: dict[str, dict] = {}
    for ma, t in tk_cfg.items():
        if not t.get("bat", False) or not t.get("thu_muc"):
            continue
        du_lieu[ma] = quet_tai_khoan(Path(t["thu_muc"]), tu)
        # 3. file loi
        for k, r in du_lieu[ma].items():
            if r["loi"]:
                them(f"loi:{ma}:{k}", "LOI", f"{ten_tk(ma)}: video '{k}' nằm trong thư mục lỗi (đăng hỏng 2 lần).")

    # 1. lech dong bo trong nhom
    for nhom, ds in NHOM.items():
        bat = [m for m in ds if m in du_lieu]
        # tam dung = khong co video nao trong 4 ngay va khong phai tai khoan tu chep (Facebook)
        tam_dung = [m for m in bat if not du_lieu[m] and not tk_cfg[m].get("chep_tu")]
        dung = [m for m in bat if m not in tam_dung]
        nguon = {m: tk_cfg[m].get("chep_tu") for m in dung}
        bat_dau = {}
        for m in dung:
            try:
                bat_dau[m] = dt.datetime.fromisoformat(tk_cfg[m]["chep_tu_luc"]).replace(tzinfo=TZ) \
                    if tk_cfg[m].get("chep_tu_luc") else None
            except Exception:
                bat_dau[m] = None
        tat_ca = set()
        for m in dung:
            tat_ca |= set(du_lieu[m])
        for k in sorted(tat_ca):
            lan_dau = [du_lieu[m][k]["da_dang"] for m in dung if k in du_lieu[m] and du_lieu[m][k]["da_dang"]]
            if not lan_dau:
                continue
            dau = min(lan_dau)
            for m in dung:
                r = du_lieu[m].get(k)
                if r and r["da_dang"]:
                    continue
                if bat_dau.get(m) and dau < bat_dau[m]:
                    continue        # video dang truoc khi tai khoan nay bat dau nhan
                if nguon.get(m):    # tai khoan chep: chi tinh tu luc nguon dang
                    src = next((x for x in dung if tk_cfg[x].get("thu_muc", "").rstrip("/\\").lower()
                                == str(nguon[m]).rstrip("/\\").lower()), None)
                    if src:
                        rs = du_lieu[src].get(k)
                        if not rs or not rs["da_dang"]:
                            continue
                        dau = rs["da_dang"]
                tre = (now - dau).total_seconds() / 3600
                if tre < ds[m] or m in TAM_DUNG_TAY:      # tai khoan nguoi dung dang tay: khong bao lech
                    continue
                if r is None:
                    them(f"lech:{m}:{k}", "LECH", f"[{nhom}] '{k}' đã đăng từ {dau:%d/%m %H:%M} nhưng KHÔNG có trong hàng chờ {ten_tk(m)} (skill quên bỏ vào?).")
                elif not r["loi"]:
                    them(f"lech:{m}:{k}", "LECH", f"[{nhom}] '{k}' đã đăng từ {dau:%d/%m %H:%M} nhưng {ten_tk(m)} vẫn chưa đăng ({tre:.0f} giờ).")

    # 2. video skill lam ma chua vao hang cho (econ)
    vdir = GOC / "04_econlazypack" / "Video"
    if vdir.is_dir():
        moi_khoa = set()
        for m in du_lieu:
            moi_khoa |= set(du_lieu[m])
        for f in vdir.glob("*/*.mp4"):
            luc = mtime(f)
            if luc < tu or (now - luc).total_seconds() < 2 * 3600:
                continue
            slug = re.sub(r"^\d+_", "", f.parent.name).lower()
            if not any(slug and slug in k for k in moi_khoa):
                them(f"chua_vao:{slug}", "LECH", f"[經濟懶人包] Video '{f.parent.name}' làm lúc {luc:%d/%m %H:%M} nhưng chưa vào hàng chờ mạng nào.")

    tom = {m: {"tam_dung": not du_lieu[m]} for m in du_lieu}
    return vande, tom


def gui(chu: str) -> bool:
    """Bao qua Gmail (he-thong-mxh/chung/gmail.py). Thu vao hang cho truoc -> khong mat."""
    sys.path.insert(0, str(HERE.parent / "he-thong-mxh" / "chung"))
    import gmail
    gmail.gui("[MXH] Kiểm đồng bộ: " + (chu.strip().splitlines() or ["báo"])[0][:80], chu)
    return True


def main(argv: list[str]) -> int:
    khong_gui = "--khong-gui" in argv
    now = bay_gio()
    vande, tom = kiem()
    st = doc_json(TRANG_THAI, {}) or {}
    cu = st.get("dang_mo", {})
    hien = {v["ma"]: v for v in vande}
    moi = [v for m, v in hien.items() if m not in cu]
    het = [cu[m] for m in cu if m not in hien and not m.startswith("het_video:")]

    MOI_NHAT.write_text(json.dumps({"luc": now.isoformat(), "van_de": vande, "tai_khoan": tom},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    if "--in" in argv:
        print(json.dumps({"van_de": vande, "moi": [v["ma"] for v in moi], "het": [v["ma"] for v in het]},
                         ensure_ascii=False, indent=2))

    if "--khong-thu" in argv:   # tac vu Claude kiem-dang-mxh-2-gio: Claude gui 1 thu gop, script chi bao + luu so
        print(json.dumps({"moi": [v["chu"] for v in moi], "het": [v["chu"] for v in het]}, ensure_ascii=False))
    da_gui = True
    if (moi or het) and not khong_gui and "--khong-thu" not in argv:
        dong = [f"🔎 KIỂM ĐỒNG BỘ MXH {now:%d/%m %H:%M}"]
        bieu = {"LOI": "❌", "LECH": "⚠️", "NHAC": "ℹ️"}
        if moi:
            dong.append("\nVấn đề mới:")
            dong += [f"{bieu.get(v['muc'], '•')} {v['chu']}" for v in moi]
        if het:
            dong.append("\nĐã hết:")
            dong += [f"✅ {v['chu']}" for v in het]
        con = len(hien) - len(moi)
        if con:
            dong.append(f"\n(Còn {con} vấn đề cũ chưa xử lý.)")
        da_gui = gui("\n".join(dong))

    if khong_gui:
        return 0
    if da_gui:
        st["dang_mo"] = hien
    st["lan_cuoi"] = now.isoformat()
    TRANG_THAI.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
