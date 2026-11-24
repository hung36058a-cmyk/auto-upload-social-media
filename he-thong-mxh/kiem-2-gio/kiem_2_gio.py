# -*- coding: utf-8 -*-
"""
AGENT KIEM TRA DOC LAP - 2 GIO/LAN (tac vu Claude "kiem-dang-mxh-2-gio" chay file nay roi tu phan tich). CHI DOC, khong dang/sua/xoa gi cua may dang.
Kiem moi bai da dang 7 ngay qua (lay tu so ghi may dang) + video YouTube moi (Apps Script dang, may dang khong thay):
  1. DUNG VI TRI: bai nam dung tai khoan da ghim (TikTok: doc trang cong khai, ten @ that; Threads: @ trong link;
     Instagram: tai khoan may dang xac nhan; Fanpage: asset_id trong link = page_id).
  2. THONG SO: TikTok (xem/tim/binh luan/chia se, trang cong khai), YouTube (API, token cua ytdata).
     Bai TikTok > 2 gio ma 0 luot xem -> CAN XEM (co the bi han che / dang xet duyet). Bai khong mo duoc -> LOI.
  3. TIEU CHI CHU KENH: chay agent kiem_tra_mxh.py (K, 1-7) che do khong luu; VI_PHAM moi -> bao.
  4. YouTube: video moi len -> Gmail "Da dang YouTube" (kem so lieu). Kenh YouTube moi: bam 2_them_kenh.bat la tu co.
Gmail CHI khi co van de MOI hoac YouTube moi dang (khong spam). Ket qua day du: du-lieu/bao-cao-moi-nhat.json,
so lieu cho lich dang: du-lieu/thong-so.json.

  python kiem_2_gio.py          chay that
  python kiem_2_gio.py --xem    in ket qua + thu se gui, khong gui, khong ghi so da bao
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "chung"))
import mxh_chung as C  # noqa: E402

DL = HERE / "du-lieu"
SO_DA_BAO = DL / "da-bao.json"
BAO_CAO = DL / "bao-cao-moi-nhat.json"
NGAY_KIEM = 7          # kiem dung vi tri bai 7 ngay qua
NGAY_SO_LIEU = 3       # chi doc lai so lieu TikTok bai 3 ngay qua (cu hon: giu so lan truoc)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0.0.0 Safari/537.36")


def _so(h: str, ten: str) -> int | None:
    m = re.search(r'"%s":"?(\d+)' % ten, h)
    return int(m.group(1)) if m else None


def tiktok(link: str) -> dict:
    """So lieu + ten @ that tu trang cong khai.
    {'chan': True} = TikTok tam chan doc (trang ngan) -> KHONG coi la loi bai; {'loi': ...} = bai khong con xem duoc."""
    h = ""
    for lan in range(2):
        try:
            req = urllib.request.Request(link, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except OSError as e:
            return {"chan": True, "loi": f"không mở được trang ({type(e).__name__})"}
        if len(h) > 50_000:
            break
        time.sleep(8)                       # trang ngan = trang chan may doc -> doi roi thu lai 1 lan
    if len(h) <= 50_000:
        return {"chan": True, "loi": "TikTok tạm chặn đọc số liệu"}
    m = re.search(r'"uniqueId":"([^"]+)"', h)
    out = {"views": _so(h, "playCount"), "likes": _so(h, "diggCount"), "comments": _so(h, "commentCount"),
           "shares": _so(h, "shareCount"), "tai_khoan": m.group(1) if m else None}
    if out["views"] is None:
        ma = re.search(r'"statusCode":(\d+)', h)
        if ma and ma.group(1) != "0":     # TikTok noi ro bai khong xem duoc (vd 10204 = khong tim thay)
            out["loi"] = f"bài không còn xem được (bị gỡ / riêng tư / chờ duyệt, mã TikTok {ma.group(1)})"
        else:                             # trang la, khong co so lieu, khong co ma loi -> coi nhu TikTok chan doc
            out.update(chan=True, loi="TikTok trả trang không có số liệu")
    return out


def kiem_bai(h: dict, acc: dict | None, t: dt.datetime) -> tuple[dict, list[tuple[str, str]]]:
    """(so lieu, [(muc, chu)]) cho 1 bai da dang."""
    ma, link = h.get("tk", ""), h.get("link") or ""
    mang = ma.split("_")[0]
    ten = C.ten_tk(ma, acc)
    van_de = []
    if acc is None:
        return {}, [("CAN_XEM", f"{ten}: tài khoản không còn bật trong cau-hinh.json, bỏ qua kiểm.")]
    can = (acc.get("username") or "").lstrip("@").lower()
    sl: dict = {}
    if mang == "tiktok":
        if can and f"/@{can}/" not in link.lower():
            van_de.append(("VI_PHAM", f"{ten}: link không thuộc @{can} → {link}"))
        luc = C.parse_t(h.get("luc"))
        if not link:
            sl = {"loi": "không có link"}
        elif luc and t - luc > dt.timedelta(days=NGAY_SO_LIEU):
            return {}, van_de                # bai cu: giu so lieu lan truoc, khong doc lai (TikTok chan neu doc nhieu)
        else:
            time.sleep(3)
            sl = tiktok(link)
        that = (sl.get("tai_khoan") or "").lower()
        if that and can and that != can:
            van_de.append(("VI_PHAM", f"{ten}: bài nằm ở @{that}, đúng ra phải ở @{can} → {link}"))
        if sl.get("loi") and not sl.get("chan"):
            van_de.append(("LOI", f"{ten}: {sl['loi']} → {link}"))
        if sl.get("views") == 0 and luc and t - luc > dt.timedelta(hours=2):
            van_de.append(("CAN_XEM", f"{ten}: 0 lượt xem dù đã đăng hơn 2 giờ (có thể bị hạn chế / đang xét duyệt) → {link}"))
    elif mang == "threads":
        if can and f"/@{can}/" not in link.lower():
            van_de.append(("VI_PHAM", f"{ten}: link Threads không thuộc @{can} → {link}"))
    elif mang == "instagram":
        if can and (h.get("tai_khoan") or "").lower() != can:
            van_de.append(("VI_PHAM", f"{ten}: đăng bằng @{h.get('tai_khoan')}, đúng ra @{can} → {link}"))
        if "/reel/" not in link and "/p/" not in link:
            van_de.append(("CAN_XEM", f"{ten}: link Instagram lạ, không chắc bài đã lên → {link or '(trống)'}"))
    elif mang == "facebook":
        pid = str(acc.get("page_id") or "")
        if pid and f"asset_id={pid}" not in link:
            van_de.append(("VI_PHAM", f"{ten}: bài không nằm ở Fanpage {acc.get('page')} (asset_id {pid}) → {link}"))
    return sl, van_de


def youtube(tu: dt.datetime) -> tuple[list[dict], list[tuple[str, str]]]:
    """Video YouTube moi (tu 'tu') cua moi kenh da noi trong ytdata/tokens."""
    try:
        sys.path.insert(0, str(C.YTDATA))
        import yt_fetch  # noqa: PLC0415  (dung lai ham dang nhap/refresh token cua ytdata)
        from googleapiclient.discovery import build  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        return [], [("LOI", f"YouTube: không nạp được thư viện ytdata ({type(e).__name__}) → chưa kiểm YouTube.")]
    ra, van_de = [], []
    for p in yt_fetch.list_channels():
        ten_kenh = Path(p).stem
        try:
            yt = build("youtube", "v3", credentials=yt_fetch.load_creds(p), cache_discovery=False)
            ch = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
            ten_kenh = ch["snippet"]["title"]
            ids = yt_fetch.recent_uploads(yt, ch["id"], tu.date())
            for i in range(0, len(ids), 50):
                r = yt.videos().list(part="snippet,statistics,status", id=",".join(ids[i:i + 50])).execute()
                for v in r.get("items", []):
                    s, sn, stt = v.get("statistics", {}), v["snippet"], v.get("status", {})
                    ra.append({"kenh": ten_kenh, "kenh_id": ch["id"], "id": v["id"], "tieu_de": sn["title"][:100],
                               "luc": sn["publishedAt"].replace("Z", "+00:00"), "link": f"https://youtu.be/{v['id']}",
                               "rieng_tu": stt.get("privacyStatus"), "hen_luc": stt.get("publishAt"),
                               "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                               "comments": int(s.get("commentCount", 0))})
                    if stt.get("madeForKids"):
                        van_de.append(("VI_PHAM", f"{ten_kenh} · YouTube: '{sn['title'][:60]}' đang bật 'dành cho trẻ em' (tiêu chí 3) → https://youtu.be/{v['id']}"))
        except Exception as e:  # noqa: BLE001  (1 kenh loi khong duoc chan kenh khac)
            van_de.append(("LOI", f"YouTube {ten_kenh}: không đọc được ({type(e).__name__}). "   # khong kem str(e): chu doi moi lan -> bao lap
                                  r"Token hết hạn → bấm đúp E:\08_AI-chung\phan-tich-mxh\ytdata\2_them_kenh.bat chọn lại kênh này."))
    return ra, van_de


def tieu_chi() -> list[tuple[str, str]]:
    """Agent kiem_tra_mxh.py (tieu chi chu kenh), khong luu so cua no -> khong anh huong lich kiem hang dem."""
    if not C.KIEM_TRA.exists():
        return [("LOI", f"Không thấy agent tiêu chí {C.KIEM_TRA}")]
    try:
        r = subprocess.run([sys.executable, "-X", "utf8", str(C.KIEM_TRA), "--khong-luu", "--khong-video"],
                           cwd=str(C.KIEM_TRA.parent), capture_output=True, text=True, encoding="utf-8", timeout=600,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        kq = json.loads(r.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        return [("LOI", f"Agent tiêu chí chạy lỗi ({type(e).__name__}).")]
    return [("VI_PHAM", f"[tiêu chí {k.get('tieu_chi')}] {k.get('noi')}: {k.get('chi_tiet')}")
            for k in kq.get("ket_qua", []) if k.get("muc") == "VI_PHAM"]


def chay(xem: bool = False, khong_thu: bool = False) -> dict:
    t = C.now()
    tu = t - dt.timedelta(days=NGAY_KIEM)
    tk = C.tai_khoan_bat()
    so_ghi = C.doc_json(C.SO_GHI, {}) or {}
    cu = (C.doc_json(C.THONG_SO, {}) or {}).get("bai") or {}
    bai, van_de = {}, []
    for h in so_ghi.get("lich_su", []):
        luc = C.parse_t(h.get("luc"))
        # Fanpage: link chung cho ca trang -> khoa theo file de khong gop moi bai thanh 1
        k = h.get("link") if h.get("link") and not str(h.get("tk")).startswith("facebook") else f"{h.get('tk')}|{h.get('file')}"
        if h.get("kq") != "ok" or not luc or luc < tu or k in bai:
            continue
        sl, vd = kiem_bai(h, tk.get(h.get("tk")), t)
        if (sl.get("chan") or not sl) and cu.get(k):
            sl = cu[k]                       # khong doc duoc lan nay -> giu so lan truoc
        else:
            sl = {**sl, "luc_do": t.isoformat()}
        bai[k] = {**sl, "tk": h.get("tk"), "luc_dang": h.get("luc")}
        van_de += vd
    yt, vd = youtube(tu)
    van_de += vd + tieu_chi()
    C.ghi_json(C.THONG_SO, {"luc": f"{t:%d/%m %H:%M}", "bai": bai, "youtube": yt})
    C.ghi_json(BAO_CAO, {"luc": t.isoformat(), "so_bai": len(bai), "youtube": len(yt), "van_de": van_de})

    so = C.doc_json(SO_DA_BAO, None)
    lan_dau = so is None
    so = so or {"da_bao": {}}
    khoa = lambda c: hashlib.md5(c.encode()).hexdigest()[:12]  # noqa: E731
    # khoa = md5 cua chu: moi chu van de phai CO DINH giua cac lan (khong chen gio/so dem) -> khong bao lap
    moi = [(m, c) for m, c in van_de if m != "CAN_XEM" or "0 lượt xem" in c]
    moi = [(m, c) for m, c in moi if khoa(c) not in so["da_bao"]]
    # YouTube moi dang (lan dau: chi ghi nho, khong gui ca lich su)
    yt_moi = [y for y in yt if y.get("rieng_tu") == "public" and f"yt|{y['id']}" not in so["da_bao"]]
    if lan_dau:
        yt_moi = []
    phan = []
    if moi:
        phan.append("❌ VẤN ĐỀ MỚI (kiểm độc lập 2 giờ/lần)\n" + "\n".join(f"- [{m}] {c}" for m, c in moi)
                    + "\n\nSửa: mở Claude Code, gõ /dang-mxh rồi dán thư này. Sửa xong bấm đúp "
                      r"E:\01_YouTube\00_Dung-chung\he-thong-mxh\DA_SUA_XONG.bat.")
    if yt_moi:
        phan.append("✅ ĐÃ ĐĂNG YOUTUBE\n" + "\n".join(
            f"- {y['kenh']}: {y['tieu_de']}\n   {y['link']} · {y['views']:,} xem · {y['likes']:,} thích" for y in yt_moi))
    if phan:
        tieu = "[MXH kiểm 2 giờ] " + " · ".join(x for x in (f"{len(moi)} vấn đề" if moi else "",
                                                              f"Đã đăng YouTube {len(yt_moi)}" if yt_moi else "") if x)
        noi = "\n\n".join(phan) + "\n\nLịch đăng + số liệu: E:\\01_YouTube\\00_Dung-chung\\he-thong-mxh\\lich\\lich-dang.html"
        if xem:
            print(tieu + "\n\n" + noi)
        elif not khong_thu:     # khong_thu: tac vu Claude tu gui 1 thu gop (kem nguyen nhan), script khong gui
            import gmail  # noqa: PLC0415
            gmail.gui(tieu, noi)
    if not xem:
        for _, c in moi:
            so["da_bao"][khoa(c)] = t.isoformat()
        for y in yt:
            if y.get("rieng_tu") == "public":
                so["da_bao"].setdefault(f"yt|{y['id']}", t.isoformat())
        han = t - dt.timedelta(days=NGAY_KIEM + 3)
        so["da_bao"] = {k: v for k, v in so["da_bao"].items() if (C.parse_t(v) or t) > han}
        C.ghi_json(SO_DA_BAO, so)
    kq = {"bai": len(bai), "youtube": len(yt), "van_de": len(van_de), "moi": len(moi), "yt_moi": len(yt_moi)}
    if khong_thu:
        kq["chi_tiet_moi"] = [f"[{m}] {c}" for m, c in moi]
        kq["youtube_moi"] = [f"{y['kenh']}: {y['tieu_de']} {y['link']} · {y['views']:,} xem · {y['likes']:,} thích" for y in yt_moi]
    return kq


if __name__ == "__main__":
    C.chay_an_toan("kiem_2_gio", lambda: print(json.dumps(
        chay("--xem" in sys.argv, "--khong-thu" in sys.argv), ensure_ascii=False)), DL)
