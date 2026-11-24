# -*- coding: utf-8 -*-
"""
TU DANG MXH THEO KHUNG GIO + GHI TRANG THAI CHO BANG THEO DOI
-------------------------------------------------------------
Windows Task Scheduler chay file nay 10 phut/lan (cai bang CAI_LICH_TU_DANG.bat).
Moi lan chay:
  1. Doc cau-hinh.json (danh sach tai khoan + khung gio) va du-lieu.json (so ghi).
  2. Kiem dang nhap: con han khong + DANG O TAI KHOAN NAO (so voi "username" da ghim).
  3. Toi khung gio thi lay video dau tien trong cho-dang cua tai khoan do va dang.
  4. Ghi ket qua vao du-lieu.json TRUOC, roi moi chuyen video sang da-dang (hoac loi + file .loi.txt).
  5. Ghi trang-thai-mxh.json (ca o day lan trong Google Drive) cho bang theo doi doc.

3 LUAT KHONG DUOC PHA:
  - Sai kenh:   tai khoan co ghim "username" chi duoc dang khi dang nhap dung ten do.
  - Bao sai:    chi ghi "da dang" khi mang xa hoi tra ve bang chung (id / link bai).
  - Dang trung: da bam nut dang ma chua ro ket qua thi KHONG tu dang lai mu quang.

Lenh tay (cho Claude / nguoi ranh may):
  python dang_mxh.py              chay 1 luot nhu lich
  python dang_mxh.py --chi-ghi    chi quet + ghi trang thai, khong dang gi
  python dang_mxh.py --kiem-tra   kiem tra dang nhap tat ca tai khoan ngay
  python dang_mxh.py --ghim       hoi roi ghim ten @ cho tai khoan chua ghim (XAC_NHAN_TAI_KHOAN.bat)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import traceback
import urllib.request
import datetime as dt
from pathlib import Path

PHIEN_BAN = "1.7"   # 18/11/2026: QUY TAC KHUNG IG - kiem/sua file bang ffmpeg, chon khung Original, chup xem truoc, kiem reel sau dang
# (1.6)   # 18/11/2026: Threads xen ke 3 bai video / 3 bai chu (<ten>.chu.txt)
# (1.5)   # 17/11/2026: them Threads (threads_dang.py)
# (1.4)   # 16/11/2026: video hen gio rieng (<ten>.gio.txt) - vd short cat dang cung gio video dai; khong chiem khung_gio.
# (1.3)   # 15/11/2026 toi: TikTok da bam Post ma chua thay bai -> cho 30 phut + chi kiem, khong tai len lai ngay
HERE = Path(__file__).resolve().parent
CFG_FILE = HERE / "cau-hinh.json"
DATA_FILE = HERE / "du-lieu.json"          # so ghi: khung nao da xu ly + lich su + dang nhap
DATA_BAK = HERE / "du-lieu.luu.json"       # ban luu tu dong (ban tot gan nhat)
STATUS_FILE = HERE / "trang-thai-mxh.json"
LOG_FILE = HERE / "nhat-ky.log"
LOCK_FILE = HERE / ".dang-chay.lock"
VIEC_FILE = HERE / "chay-1-lan.json"       # viec bao tri chay 1 lan (xem chay_viec_cho)
VIEC_DUOC = {"chan_doan_tiktok.py", "thu_tiktok.py", "thu_tai_len_tiktok.py", "thu_instagram.py", "xem_lich_windows.py", "an_bai_tiktok.py", "threads_dang.py", "cai_ffmpeg.py", "thu_dang_ig.py"}
VIDEO_EXT = {".mp4", ".mov"}
THUMB_EXT = [".jpg", ".jpeg", ".png"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0.0.0 Safari/537.36")
KHOA_TOI_DA_GIO = 6               # khoa cu hon muc nay coi nhu luot truoc da treo
DN_CHAN = {                       # trang thai dang nhap KHONG duoc dang (giu nguyen hang cho, sua xong tu dang lai)
    "chua_dang_nhap": "Chưa đăng nhập tài khoản → máy không đăng (bấm DANG_NHAP_LAI.bat)",
    "sai_tai_khoan": "Đăng nhập SAI tài khoản → máy không đăng (bấm DANG_NHAP_LAI.bat)",
    "het_han": "Đăng nhập hết hạn → máy không đăng (bấm DANG_NHAP_LAI.bat)",
}
DICH_LOI = {                      # ma loi cua may dang TikTok -> cau de hieu tren bang
    "KHONG_XAC_NHAN": "Đã bấm Post nhưng TikTok chưa hiện bài mới. Máy KHÔNG tải lên lại ngay: kiểm lại mỗi 10 phút, đủ 30 phút vẫn không có bài mới đăng lại.",
    "CHUA_THAY_BAI": "Đã bấm Post, TikTok vẫn chưa hiện bài. Máy đang kiểm lại mỗi 10 phút (chưa tải lên lại).",
    "KHONG_DOC_DUOC_DS_BAI": "Không đọc được danh sách bài của TikTok nên chưa đăng (tránh đăng trùng).",
    "SAI_TAI_KHOAN": "Đăng nhập SAI tài khoản → máy không đăng",
    "HET_HAN_DANG_NHAP": "TikTok không cho biết đang đăng nhập tài khoản nào (hết hạn?) → máy không đăng",
}
TEN_THU_MUC = {"da-dang": "da-dang", "loi": "loi"}


# ---------------------------------------------------------------- tien ich
def now() -> dt.datetime:
    return dt.datetime.now().replace(microsecond=0)


def iso(t: dt.datetime | None) -> str | None:
    """Gio may (Dai Loan) kem mui gio, vd 2026-11-14T12:00:00+08:00"""
    return t.astimezone().isoformat() if t else None


def parse_t(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s).replace(tzinfo=None)


def log(msg: str) -> None:
    line = f"[{now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        old = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-800:] if LOG_FILE.exists() else []
        LOG_FILE.write_text("\n".join(old + [line]) + "\n", encoding="utf-8")
    except Exception:
        pass


def read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(p: Path, data) -> None:
    """Ghi tron ven (file tam roi doi ten). File dang bi chuong trinh khac mo -> thu lai vai lan."""
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    for i in range(6):
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if i == 5:
                raise
            time.sleep(0.5)


def luu(data: dict) -> bool:
    """Ghi du-lieu.json. False = khong ghi duoc (da ghi nhat ky) -> noi goi tu quyet dinh co dang tiep khong."""
    try:
        write_json(DATA_FILE, data)
        return True
    except Exception as e:
        log(f"KHONG GHI DUOC du-lieu.json: {type(e).__name__}: {e}")
        return False


def load_cfg() -> dict:
    try:
        cfg = json.loads(CFG_FILE.read_text(encoding="utf-8-sig"))
        if not isinstance(cfg, dict) or not isinstance(cfg.get("tai_khoan"), list) or not cfg.get("repo"):
            raise ValueError("thieu 'tai_khoan' hoac 'repo'")
    except Exception as e:
        raise SystemExit(f"cau-hinh.json bị hỏng hoặc sai định dạng ({type(e).__name__}: {e}) → máy không đăng gì. Nhờ Claude sửa file này.")
    cfg.setdefault("cua_so_phut", 120)
    cfg.setdefault("cho_video_phut", 30)
    cfg.setdefault("kiem_tra_dang_nhap_moi_gio", 12)
    cfg.setdefault("so_lan_thu_lai", 2)
    cfg.setdefault("cho_xac_nhan_phut", 30)      # TikTok: da bam Post ma chua thay bai -> cho + kiem lai bay nhieu phut roi moi tai len lai
    cfg.setdefault("thoi_gian_toi_da_phut", 20)
    return cfg


def tai_khoan_hop_le(cfg: dict, sys_errors: list) -> list[dict]:
    """Gan 'ma' cho tung tai khoan, bo qua (co bao) khoi nao thieu thong tin. Tra ve cac tai khoan dang bat."""
    out = []
    for i, acc in enumerate(cfg["tai_khoan"]):
        if not isinstance(acc, dict) or not all(acc.get(k) for k in ("mang", "cookie", "thu_muc")):
            sys_errors.append(f"cau-hinh.json: tài khoản thứ {i + 1} thiếu mang/cookie/thu_muc → bỏ qua. Nhờ Claude sửa.")
            continue
        acc["ma"] = f"{acc['mang']}_{acc['cookie']}"
        if acc.get("bat", True):
            if acc["mang"] not in POSTERS:
                sys_errors.append(f"cau-hinh.json: {acc['ma']} dùng mạng '{acc['mang']}' máy chưa hỗ trợ → bỏ qua.")
                continue
            out.append(acc)
    return out


def load_data() -> tuple[dict | None, str | None]:
    """Doc du-lieu.json. Hong -> dung ban luu tu dong. Ca hai hong -> (None, ly do): luot nay KHONG dang
    (mat so ghi ma van dang thi se dang trung)."""
    mau = {"da_xu_ly": {}, "lich_su": [], "dang_nhap": {}, "thu": {}, "dang_do": {}, "cho_don": {}}
    if not DATA_FILE.exists() and not DATA_BAK.exists():
        return mau, None                      # lan chay dau tien
    ghi_chu = None
    for f in (DATA_FILE, DATA_BAK):
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
            if not isinstance(d, dict):
                raise ValueError("khong phai doi tuong JSON")
        except Exception as e:
            if f is DATA_FILE:
                ghi_chu = f"{type(e).__name__}: {e}"
            continue
        for k, v in mau.items():
            if not isinstance(d.get(k), type(v)):
                d[k] = v
        for k, v in list(d["thu"].items()):   # ban cu: so lan thu la 1 con so
            if not isinstance(v, dict):
                d["thu"][k] = {"n": int(v or 0), "tu": iso(now())}
        if f is DATA_BAK:
            hong = None
            if DATA_FILE.exists():
                hong = HERE / f"du-lieu.hong-{now():%Y%m%d-%H%M%S}.json"
                try:
                    os.replace(DATA_FILE, hong)
                except Exception:
                    hong = None
            log(f"du-lieu.json khong doc duoc ({ghi_chu}) -> dung ban luu {DATA_BAK.name}" + (f"; file hong giu o {hong.name}" if hong else ""))
            return d, "du-lieu.json bị hỏng → máy đã tự dùng bản lưu gần nhất (file hỏng được giữ lại). Nhờ Claude kiểm tra."
        try:                                  # ban tot -> cap nhat ban luu
            tmp = DATA_BAK.with_suffix(".json.tmp")
            shutil.copyfile(DATA_FILE, tmp)
            os.replace(tmp, DATA_BAK)
        except Exception:
            pass
        return d, None
    log(f"du-lieu.json va ban luu deu khong doc duoc ({ghi_chu}) -> luot nay KHONG dang")
    return None, "du-lieu.json (sổ ghi) và bản lưu đều hỏng → máy tạm KHÔNG đăng để khỏi đăng trùng. Nhờ Claude sửa."


def repo_paths(cfg):
    repo = Path(cfg["repo"])
    py = repo / ".venv" / "Scripts" / "python.exe"
    sau = repo / ".venv" / "Scripts" / "sau.exe"
    return repo, py, sau


def read_caption(txt: Path) -> str:
    """Caption UTF-8 (Notepad luu 'Unicode' = UTF-16 co BOM cung doc duoc). Ma hoa khac -> UnicodeError."""
    raw = txt.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16").strip()
    return raw.decode("utf-8-sig").strip()


def ghim(acc: dict) -> str:
    """Ten @ da ghim trong cau-hinh.json ('' = chua ghim)."""
    return str(acc.get("username") or "").strip().lstrip("@")


def cung_ten(a: str | None, b: str | None) -> bool:
    return bool(a) and bool(b) and a.strip().lstrip("@").lower() == b.strip().lstrip("@").lower()


def tail(text: str, n: int = 6) -> str:
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return " | ".join(lines[-n:])[-600:] or "Không rõ lỗi"


# ---------------------------------------------------------------- hang cho
def on_dinh(f: Path) -> bool:
    """Video da chep xong chua: co noi dung va khong con bi ghi trong 2 phut gan day."""
    try:
        st = f.stat()
        return st.st_size > 0 and time.time() - st.st_mtime >= 120
    except OSError:
        return False


def scan_queue(acc: dict, bo: set | frozenset = frozenset()) -> dict:
    """Doc thu muc cho-dang: video nao du (co caption doc duoc), cai nao thieu. 'bo' = ten video da dang dang cho don."""
    out = {"ready": [], "thieu_caption": [], "thieu_video": [], "caption_loi": [], "hen_gio": [], "gio_loi": []}
    q = Path(acc["thu_muc"]) / "cho-dang"
    try:
        q.mkdir(parents=True, exist_ok=True)
        files = [f for f in q.iterdir() if f.is_file()]
    except OSError as e:
        out["loi"] = f"{type(e).__name__}: {e}"
        return out
    vids = {f.stem: f for f in files if f.suffix.lower() in VIDEO_EXT}
    txts = {f.stem: f for f in files if f.suffix.lower() == ".txt" and not f.name.endswith((".loi.txt", ".gio.txt", ".chu.txt"))}
    gios = {f.name[:-len(".gio.txt")]: f for f in files if f.name.endswith(".gio.txt")}
    for stem in sorted(vids):
        v = vids[stem]
        if v.name in bo:
            continue
        if not on_dinh(v):
            continue                 # vua chep vao / dang chep: luot sau tinh
        txt = txts.get(stem)
        if not txt:
            out["thieu_caption"].append(v.name)
            continue
        try:
            cap = read_caption(txt)
        except (UnicodeError, OSError):
            out["caption_loi"].append(v.name)
            continue
        if not cap:
            out["thieu_caption"].append(v.name)
            continue
        thumb = next((q / f"{stem}{e}" for e in THUMB_EXT if (q / f"{stem}{e}").exists()), None)
        if stem in gios:
            # video hen gio rieng: KHONG vao hang khung_gio thuong
            try:
                g = dt.datetime.strptime(gios[stem].read_text(encoding="utf-8-sig").strip()[:16], "%Y-%m-%d %H:%M")
            except (ValueError, OSError, UnicodeError):
                out["gio_loi"].append(v.name)
                continue
            out["hen_gio"].append({"video": v, "txt": txt, "thumb": thumb, "caption": cap, "gio": g, "gio_file": gios[stem]})
            continue
        out["ready"].append({"video": v, "txt": txt, "thumb": thumb, "caption": cap})
    out["thieu_video"] = [txts[s].name for s in sorted(txts) if s not in vids]
    if acc.get("mang") == "threads":
        # bai CHI CO CHU (khong video): <ten>.chu.txt
        for f in sorted(x for x in files if x.name.endswith(".chu.txt")):
            if f.name in bo or not on_dinh(f):
                continue
            try:
                cap = read_caption(f)
            except (UnicodeError, OSError):
                out["caption_loi"].append(f.name)
                continue
            if cap:
                out["ready"].append({"video": f, "txt": f, "thumb": None, "caption": cap, "chi_chu": True})
        out["ready"].sort(key=lambda it: it["video"].name)
    return out


LUOT_DOI_KIEU = 3   # Threads: moi 3 bai thi doi kieu (video <-> chi chu)


def la_bai_chu(ten: str) -> bool:
    return str(ten or "").endswith(".chu.txt")


def chon_bai_threads(data: dict, acc: dict, ready: list) -> dict:
    """Threads xen ke: dem cac bai da dang gan nhat cung kieu; du LUOT_DOI_KIEU thi doi kieu.
    Kieu can dang ma het hang cho thi dang kieu con lai (khong bo lo khung gio)."""
    ds = [la_bai_chu(h.get("file")) for h in data["lich_su"] if h.get("tk") == acc["ma"] and h.get("kq") == "ok"]
    if not ds:
        muon_chu = False
    else:
        n = 0
        for x in ds:
            if x != ds[0]:
                break
            n += 1
        muon_chu = ds[0] if n < LUOT_DOI_KIEU else not ds[0]
    for it in ready:
        if bool(it.get("chi_chu")) == muon_chu:
            return it
    return ready[0]


def chuyen_file(data: dict, acc: dict, names: list[str], dich: str, prefix: str) -> None:
    """Chuyen file khoi cho-dang sang da-dang / loi. File dang bi khoa -> ghi vao 'cho_don', luot sau chuyen tiep
    (trong luc do scan_queue bo qua video nay nen KHONG bi dang lai)."""
    q = Path(acc["thu_muc"]) / "cho-dang"
    dst_dir = Path(acc["thu_muc"]) / TEN_THU_MUC[dich]
    ton = data["cho_don"].setdefault(acc["ma"], {})
    for name in names:
        src = q / name
        try:
            if src.exists():
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst = dst_dir / f"{prefix}{name}"
                i = 2
                while dst.exists():
                    dst = dst_dir / f"{prefix}{src.stem}_{i}{src.suffix}"
                    i += 1
                shutil.move(str(src), str(dst))
            ton.pop(name, None)
        except Exception as e:
            if name not in ton:
                log(f"{acc['ma']}: chua chuyen duoc {name} sang {dich} ({type(e).__name__}) -> luot sau chuyen tiep, khong dang lai")
            ton[name] = [dich, prefix]
    if not ton:
        data["cho_don"].pop(acc["ma"], None)


def don_file_ton(data: dict, acc: dict) -> None:
    ton = dict(data["cho_don"].get(acc["ma"], {}))
    for name, (dich, prefix) in ton.items():
        chuyen_file(data, acc, [name], dich, prefix)


def video_cho_don(data: dict, acc: dict) -> frozenset:
    return frozenset(n for n in data["cho_don"].get(acc["ma"], {}) if Path(n).suffix.lower() in VIDEO_EXT or la_bai_chu(n))


# ---------------------------------------------------------------- dang bai
def run_cmd(args: list[str], cwd: Path, timeout_min: int) -> tuple[int, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    cham_khoa()
    try:
        p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout_min * 60, env=env)
        return p.returncode, (p.stdout or "") + "\n" + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"Quá {timeout_min} phút chưa xong → dừng lại"
    except OSError as e:
        return 127, f"Không chạy được {Path(args[0]).name}: {e}"
    finally:
        cham_khoa()


def dau_da_bam(cookie: str) -> Path:
    """File danh dau 'may da bam nut Post' cua 1 tai khoan TikTok (ghi ngay truoc khi bam)."""
    return HERE / f".tiktok-da-bam-{cookie}.txt"


def post_tiktok(cfg, acc, item, rec) -> dict:
    """Thanh cong CHI KHI may dang tra ve id bai that tim thay trong danh sach Posts cua dung tai khoan.
    rec["chi_kiem"] = True: chi kiem bai da len chua (luot truoc da bam Post), KHONG tai len."""
    repo, py, _ = repo_paths(cfg)
    want = ghim(acc)
    chi_kiem = bool(rec.pop("chi_kiem", False))
    dau = dau_da_bam(acc["cookie"])
    if not chi_kiem:
        try:
            dau.unlink(missing_ok=True)
        except OSError:
            pass
    tu_luc = str(int(parse_t(rec["tu"]).timestamp())) if rec.get("tu") else ""
    args = [str(py), str(Path(__file__).resolve()), "--tiktok-one", acc["cookie"],
            str(item["video"]), str(item["txt"]), str(item["thumb"] or ""), want, tu_luc, "1" if chi_kiem else ""]
    code, out = run_cmd(args, repo, cfg["thoi_gian_toi_da_phut"])
    m = re.search(r"video_id:\s*([0-9]{8,})", out)
    u = re.search(r"tai_khoan:\s*([A-Za-z0-9_.]+)", out)
    that = u.group(1) if u and u.group(1) != "None" else None
    if code == 0 and m and want and that and not cung_ten(that, want):
        code, out = 1, f"LOI_DANG: SAI_TAI_KHOAN: bai len @{that}, can @{want}"     # khong the xay ra, de phong
    if code == 0 and m:
        vid = m.group(1)
        ten = that or want
        res = {"ok": True, "id": vid, "tai_khoan": that,
               "link": f"https://www.tiktok.com/@{ten}/video/{vid}" if ten else None}
        tr = re.search(r"bai_trung:\s*([0-9,]+)", out)
        if tr:
            res["canh_bao"] = (f"CÓ THỂ ĐĂNG TRÙNG: TikTok có {len(tr.group(1).split(','))} bài mới cùng caption "
                               f"(id {tr.group(1)}). Mở TikTok kiểm tra và xóa bớt 1 bài.")
        return res
    e = re.search(r"LOI_DANG:\s*(.+)", out)
    loi = e.group(1).strip()[:400] if e else (tail(out) if code != 0 else "KHONG_XAC_NHAN: khong co id bai")
    res = {"ok": False, "loi": loi, "tai_khoan": that}
    ma_loi = loi.split(":", 1)[0].strip()
    if ma_loi == "CHUA_THAY_BAI":
        res["cho_xn"] = True                 # luot chi-kiem: van chua thay bai
    elif not chi_kiem and dau.exists():
        res["da_bam"] = True                 # da bam Post (ke ca Chrome sap / qua gio sau do) ma khong co bang chung
        if ma_loi not in DICH_LOI:
            res["loi"] = loi = DICH_LOI["KHONG_XAC_NHAN"] + f" (lỗi kèm theo: {loi[:120]})"
    if ma_loi in DICH_LOI:
        res["loi"] = DICH_LOI[ma_loi] + (f" (đang ở @{that}, cần @{want})" if ma_loi == "SAI_TAI_KHOAN" and that and want else "")
    if ma_loi == "SAI_TAI_KHOAN":
        res["dang_nhap"] = "sai_tai_khoan"
    elif ma_loi == "HET_HAN_DANG_NHAP":
        res["dang_nhap"] = "het_han"
    return res


def ig_res_file(acc) -> Path:
    return HERE / f".ig-ket-qua-{acc['cookie']}.json"


def doc_ket_qua_ig(acc, code: int | None = None, out: str = "") -> dict:
    """Doc file ket qua cua `sau instagram upload-video --result`. Khoa that cua file nay:
    status = not_submitted | submission_unknown | processing | published; username, user_id;
    khi xong: content_id, post_id, post_url; khi loi: stage, error."""
    r = read_json(ig_res_file(acc), {})
    if not isinstance(r, dict):
        r = {}
    st, user = r.get("status"), r.get("username")
    want = ghim(acc)
    if st == "published" and r.get("post_url"):
        # da len that (ke ca khi buoc luu phien sau do bi loi va lenh thoat ma 1)
        res = {"ok": True, "link": r["post_url"], "id": r.get("content_id") or r.get("post_id"), "tai_khoan": user}
        if want and user and not cung_ten(user, want):
            res["sai_kenh"] = f"ĐĂNG NHẦM KÊNH: bài đã lên Instagram @{user}, trong khi kênh cần là @{want}. Mở link để xóa bài, rồi bấm DANG_NHAP_LAI.bat."
        if r.get("khung_loi"):     # QUY TAC IG buoc 3: reel sau dang bi cat / vien den -> bao do, KHONG tu xoa bai
            anh = (r.get("anh") or {}).get("5-sau-dang", "")
            res["canh_bao"] = (f"KHUNG IG SAI: {r['khung_loi']}. Máy KHÔNG xoá bài — chủ kênh tự xoá rồi đăng lại. "
                               + (f"Ảnh chụp: {anh}" if anh else ""))
        return res
    if st in ("submission_unknown", "processing"):
        return {"ok": False, "chua_ro": True, "tai_khoan": user,
                "loi": "Đã bấm Chia sẻ nhưng Instagram không trả lời rõ là bài đã lên hay chưa. Máy KHÔNG đăng lại để khỏi trùng. "
                       "Mở Instagram xem: đã có bài thì không cần làm gì; chưa có thì nhờ Claude đưa video về lại hàng chờ."}
    loi = str(r.get("error") or "").strip() or (tail(out) if code not in (None, 0) else "")
    res = {"ok": False, "tai_khoan": user,
           "loi": (f"[{r['stage']}] " if r.get("stage") else "") + (loi or "Instagram không trả về kết quả (không có bằng chứng bài đã lên)")}
    if r.get("stage") == "identity" or "未登录" in loi:
        res["dang_nhap"] = "het_han"
    return res


# ---------------------------------------------------------------- QUY TAC KHUNG IG (chu kenh chot 18/11/2026)
FFMPEG = HERE / "ffmpeg.exe"          # cai bang cai_ffmpeg.py (imageio-ffmpeg)
LOC_9_16 = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1"


def thong_tin_video(video: Path) -> dict:
    """Doc kich thuoc / ma hoa / do dai bang `ffmpeg -i` (laptop khong co ffprobe)."""
    r = subprocess.run([str(FFMPEG), "-hide_banner", "-i", str(video)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    info = {"tho": r.stderr[-1500:]}
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    if m:
        info["giay"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    for dong in r.stderr.splitlines():
        if "Video:" in dong and "vcodec" not in info:
            v = re.search(r"Video:\s*(\w+)", dong)
            k = re.search(r",\s*(\d{2,5})x(\d{2,5})", dong)
            sar = re.search(r"SAR (\d+):(\d+)", dong)
            info["vcodec"] = v[1] if v else None
            if k:
                info["w"], info["h"] = int(k[1]), int(k[2])
            info["sar_1_1"] = (not sar) or sar[1] == sar[2]
            info["xoay"] = bool(re.search(r"rotat(?:e|ion of)\s*:?\s*-?(?:90|270)", r.stderr))
        elif "Audio:" in dong and "acodec" not in info:
            a = re.search(r"Audio:\s*(\w+)", dong)
            info["acodec"] = a[1] if a else None
    return info


def kiem_video_ig(video: Path, tam: Path) -> tuple[Path | None, str | None]:
    """Buoc 1: video phai 1080x1920 (9:16), H.264, AAC, < 90 giay. Sai ti le -> thu nho + nen den (KHONG crop).
    Tra (file de dang, None) hoac (None, loi)."""
    if not FFMPEG.exists():
        return None, "Laptop chưa có ffmpeg nên chưa kiểm được khung video → chưa đăng (nhờ Claude chạy cai_ffmpeg.py)"
    i = thong_tin_video(video)
    if "giay" not in i or "vcodec" not in i:
        return None, "ffmpeg không đọc được video (file hỏng?) → không đăng"
    if i["giay"] >= 90:
        return None, f"Video dài {i['giay']:.0f} giây; Reel phải dưới 90 giây → không đăng (máy không tự cắt bớt)"
    dung = (i.get("vcodec") == "h264" and (i.get("w"), i.get("h")) == (1080, 1920) and i.get("sar_1_1")
            and i.get("acodec") == "aac" and not i.get("xoay"))
    if dung:
        return video, None
    tam.mkdir(parents=True, exist_ok=True)
    out = tam / f"{video.stem}.ig.mp4"
    r = subprocess.run([str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-vf", LOC_9_16,
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    j = thong_tin_video(out) if out.exists() else {}
    if r.returncode != 0 or (j.get("w"), j.get("h"), j.get("vcodec")) != (1080, 1920, "h264"):
        return None, f"Video sai khung ({i.get('w')}x{i.get('h')} {i.get('vcodec')}/{i.get('acodec')}) và đổi sang 1080x1920 bị lỗi: {(r.stderr or '')[-200:]}"
    log(f"  khung IG: {video.name} {i.get('w')}x{i.get('h')} {i.get('vcodec')}/{i.get('acodec')} -> thu nho + nen den 1080x1920 ({out.name})")
    return out, None


def lay_bia_ig(video: Path, tam: Path) -> Path | None:
    """Khong co <ten>.jpg -> lay khung hinh o GIUA video lam anh bia."""
    try:
        giay = thong_tin_video(video).get("giay") or 2
        tam.mkdir(parents=True, exist_ok=True)
        out = tam / f"{video.stem}.bia.jpg"
        subprocess.run([str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{giay / 2:.2f}", "-i", str(video),
                        "-frames:v", "1", "-q:v", "2", str(out)], capture_output=True, timeout=120)
        return out if out.exists() and out.stat().st_size > 0 else None
    except Exception as e:
        log(f"  khong lay duoc anh bia: {e}")
        return None


def post_instagram(cfg, acc, item, rec) -> dict:
    """Thanh cong CHI KHI file ket qua ghi status=published kem link bai. Da bam Chia se ma chua ro -> 'chua_ro', khong dang lai."""
    repo, _, sau = repo_paths(cfg)
    first, _, rest = item["caption"].partition("\n")
    res_file = ig_res_file(acc)
    res_file.unlink(missing_ok=True)
    tam = Path(acc["thu_muc"]) / "tam-ig"
    video, loi = kiem_video_ig(Path(item["video"]), tam)          # QUY TAC IG buoc 1
    if loi:
        return {"ok": False, "loi": f"[kiem file] {loi}"}
    thumb = item["thumb"] or lay_bia_ig(video, tam)
    args = [str(sau), "instagram", "upload-video", "--account", acc["cookie"],
            "--file", str(video), "--title", first.strip(), "--desc", rest.strip(),
            "--result", str(res_file)]
    if thumb:
        args += ["--thumbnail", str(thumb)]
    if acc.get("an_trinh_duyet"):
        args.append("--headless")
    try:
        code, out = run_cmd(args, repo, cfg["thoi_gian_toi_da_phut"])
    finally:
        for f in (video, thumb):                                  # chi xoa file tam may tu tao
            if f and Path(f).parent == tam:
                Path(f).unlink(missing_ok=True)
    return doc_ket_qua_ig(acc, code, out)


def post_youtube(cfg, acc, item, rec) -> dict:
    """`sau youtube upload-video` khong tra ve link/id -> khong co bang chung -> khong bao 'da dang' (ghi 'chua ro')."""
    repo, _, sau = repo_paths(cfg)
    first, _, rest = item["caption"].partition("\n")
    tags = ",".join(t.lstrip("#") for t in rest.split() if t.startswith("#"))
    args = [str(sau), "youtube", "upload-video", "--account", acc["cookie"],
            "--file", str(item["video"]), "--title", first.strip()[:100], "--desc", rest.strip(),
            "--visibility", acc.get("che_do", "public")]
    if tags:
        args += ["--tags", tags]
    if item["thumb"]:
        args += ["--thumbnail", str(item["thumb"])]
    if acc.get("an_trinh_duyet"):
        args.append("--headless")
    code, out = run_cmd(args, repo, cfg["thoi_gian_toi_da_phut"])
    if code == 0:
        return {"ok": False, "chua_ro": True,
                "loi": "Máy đã gửi video lên YouTube nhưng YouTube không trả link để kiểm chứng. Mở YouTube Studio xem bài đã lên chưa."}
    return {"ok": False, "loi": tail(out)}


def dau_threads(cookie: str) -> Path:
    """File danh dau 'may da bam nut Post' cua 1 tai khoan Threads."""
    return HERE / f".threads-da-bam-{cookie}.txt"


def post_threads(cfg, acc, item, rec) -> dict:
    """Thanh cong CHI KHI threads_dang.py tra ve link bai that. Da bam Post ma khong thay bai -> 'chua_ro', khong dang lai."""
    repo, py, _ = repo_paths(cfg)
    dau = dau_threads(acc["cookie"])
    dau.unlink(missing_ok=True)
    args = [str(py), str(HERE / "threads_dang.py"), "upload", acc["cookie"],
            "" if item.get("chi_chu") else str(item["video"]), str(item["txt"]), ghim(acc), str(dau), str(acc.get("cuoi_bai") or "")]
    code, out = run_cmd(args, repo, cfg["thoi_gian_toi_da_phut"])
    u = re.search(r"tai_khoan:\s*([A-Za-z0-9_.]+)", out)
    that = u.group(1) if u else None
    m = re.search(r"link:\s*(https://\S+)", out)
    if code == 0 and m:
        return {"ok": True, "link": m.group(1), "id": m.group(1).rstrip("/").rsplit("/", 1)[-1], "tai_khoan": that}
    e = re.search(r"LOI_DANG:\s*(.+)", out)
    loi = e.group(1).strip()[:400] if e else tail(out)
    if "DA_BAM_POST" in out or dau.exists():
        return {"ok": False, "chua_ro": True, "tai_khoan": that,
                "loi": "Đã bấm Post trên Threads nhưng chưa thấy bài mới trên trang cá nhân. Máy KHÔNG đăng lại để khỏi trùng. "
                       "Mở Threads xem: đã có bài thì không cần làm gì; chưa có thì nhờ Claude đưa video về lại hàng chờ. "
                       f"(chi tiết: {loi[:150]})"}
    res = {"ok": False, "loi": loi, "tai_khoan": that}
    ma_loi = loi.split(":", 1)[0].strip()
    if ma_loi == "SAI_TAI_KHOAN":
        res["dang_nhap"] = "sai_tai_khoan"
    elif ma_loi == "HET_HAN_DANG_NHAP":
        res["dang_nhap"] = "het_han"
    return res


# ---------------------------------------------------------------- FACEBOOK (them 21/11/2026)
# Dang Reels len Fanpage qua `sau facebook-page upload-video` (Meta Business Suite). Ghim Fanpage bang "page" (ten trang
# dung tung chu) + "page_id" (asset_id trong Business Suite). Video lay tu hang cho TikTok da dang ("chep_tu").
def fb_res_file(acc) -> Path:
    return HERE / f".fb-ket-qua-{acc['cookie']}.json"


def doc_ket_qua_fb(acc, code: int | None = None, out: str = "") -> dict:
    """Ket qua `--result`: status = not_submitted | submission_unknown (da bam Dang, chua ro) | processing (Meta da nhan
    Reel, hop thoai hoan tat da hien) | published | scheduled; page_id, page_name; content_id neu co."""
    r = read_json(fb_res_file(acc), {})
    if not isinstance(r, dict):
        r = {}
    st = r.get("status")
    trang = r.get("page_name")
    if st in ("processing", "published"):
        pid = str(r.get("page_id") or "")
        link = f"https://business.facebook.com/latest/posts/published_posts?asset_id={pid}" if pid else None
        res = {"ok": True, "link": link, "id": r.get("content_id") or None, "tai_khoan": trang}
        want = str(acc.get("page_id") or "")
        if want and pid and pid != want:
            res["sai_kenh"] = (f"ĐĂNG NHẦM TRANG: bài đã lên Fanpage '{trang}' (id {pid}), trang cần là '{acc.get('page')}' (id {want}). "
                               "Mở Business Suite xoá bài, rồi nhờ Claude kiểm tra.")
        return res
    if st == "submission_unknown":
        return {"ok": False, "chua_ro": True, "tai_khoan": trang,
                "loi": "Đã bấm Đăng trên Facebook nhưng Meta không trả lời rõ bài đã lên chưa. Máy KHÔNG đăng lại để khỏi trùng. "
                       "Mở Fanpage (mục Reels) xem: đã có bài thì thôi; chưa có thì nhờ Claude đưa video về lại hàng chờ."}
    loi = tail(out) if code not in (None, 0) else ""
    res = {"ok": False, "tai_khoan": trang, "loi": loi or "Facebook không trả về kết quả (chưa bấm Đăng, không có bằng chứng bài đã lên)"}
    if "登录态" in out or "login" in loi.lower():
        res["dang_nhap"] = "het_han"
    elif "未找到指定发布主体" in out:
        res["dang_nhap"] = "sai_tai_khoan"
        res["loi"] = f"Tài khoản Facebook đang đăng nhập không quản lý Fanpage '{acc.get('page')}'. Bấm DANG_NHAP_LAI_FACEBOOK.bat."
    return res


def post_facebook(cfg, acc, item, rec) -> dict:
    """Thanh cong CHI KHI Meta xac nhan da nhan Reel (status processing/published). Da bam Dang ma chua ro -> 'chua_ro'."""
    if not acc.get("page"):
        return {"ok": False, "loi": "cau-hinh.json: tài khoản Facebook thiếu 'page' (tên Fanpage) → không đăng để khỏi đăng nhầm trang."}
    repo, _, sau = repo_paths(cfg)
    first, _, rest = item["caption"].partition("\n")
    res_file = fb_res_file(acc)
    res_file.unlink(missing_ok=True)
    args = [str(sau), "facebook-page", "upload-video", "--account", acc["cookie"],
            "--file", str(item["video"]), f"--title={first.strip()[:250]}", f"--desc={rest.strip()}",
            f"--page={acc['page']}", "--result", str(res_file)]       # dang --x=... : caption bat dau bang '-' khong lam hong lenh
    if str(acc.get("page_id") or "").isdigit():   # 22/11: mo thang dung Fanpage (khong thi Business Suite mo trang dung gan nhat)
        args.append(f"--page-id={acc['page_id']}")
    if acc.get("an_trinh_duyet"):
        args.append("--headless")
    code, out = run_cmd(args, repo, cfg["thoi_gian_toi_da_phut"])
    return doc_ket_qua_fb(acc, code, out)


def chep_tu_nguon(data: dict, acc: dict) -> None:
    """Facebook: chep video tai khoan nguon (vd TikTok) DA DANG sau moc 'chep_tu_luc' vao cho-dang cua Facebook.
    Moi video chi chep 1 lan (so 'da_chep'). Gio dang lay tu tien to ten file 'YYYY-MM-DD_HHMM_' do chuyen_file dat."""
    nguon = acc.get("chep_tu")
    if not nguon:
        return
    try:
        moc = dt.datetime.strptime(str(acc.get("chep_tu_luc", ""))[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        log(f"{acc['ma']}: thieu/sai 'chep_tu_luc' -> khong chep video (tranh chep ca kho cu)")
        return
    src = Path(nguon) / "da-dang"
    dst = Path(acc["thu_muc"]) / "cho-dang"
    da = data.setdefault("da_chep", {}).setdefault(acc["ma"], [])
    try:
        vids = sorted(f for f in src.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXT)
    except OSError:
        return
    for v in vids:
        m = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})_", v.name)
        if not m or v.name in da:
            continue
        if dt.datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}", "%Y-%m-%d %H:%M") < moc:
            continue
        txt = v.with_suffix(".txt")
        if not txt.exists():
            continue
        try:
            dst.mkdir(parents=True, exist_ok=True)
            for f in [txt] + [v.with_suffix(e) for e in THUMB_EXT if v.with_suffix(e).exists()] + [v]:   # video chep cuoi
                tmp = dst / (f.name + ".dang-chep")
                shutil.copyfile(f, tmp)
                os.replace(tmp, dst / f.name)
            da.append(v.name)        # KHONG cat bot danh sach: cat la video cu (van con trong da-dang) bi chep + dang lai
            luu(data)
            log(f"{acc['ma']}: chep {v.name} tu {Path(nguon).name} vao hang cho")
        except Exception as e:
            log(f"{acc['ma']}: chua chep duoc {v.name} ({type(e).__name__}: {e}) -> luot sau thu lai")


POSTERS = {"tiktok": post_tiktok, "instagram": post_instagram, "youtube": post_youtube, "threads": post_threads,
           "facebook": post_facebook}


# ---------------------------------------------------------------- dang nhap
def cookie_file(cfg, acc) -> Path:
    repo = Path(cfg["repo"])
    if acc["mang"] == "tiktok":
        return repo / "cookies" / "tk_uploader" / f"{acc['cookie']}.json"
    if acc["mang"] == "facebook":
        return repo / "cookies" / f"facebook-page_{acc['cookie']}.json"
    return repo / "cookies" / f"{acc['mang']}_{acc['cookie']}.json"


def check_login(cfg, acc) -> tuple[str, str | None]:
    """(trang thai, ten @ that). Trang thai: 'ok' | 'het_han' | 'chua_dang_nhap' | 'sai_tai_khoan' | 'khong_ro'."""
    if not cookie_file(cfg, acc).exists():
        return "chua_dang_nhap", None
    repo, py, _ = repo_paths(cfg)
    user = None
    if acc["mang"] == "tiktok":
        # hoi thang TikTok: con dang nhap khong + dang o tai khoan nao (khong mo trinh duyet)
        st, user = tiktok_whoami(cfg, acc["cookie"])
    elif acc["mang"] == "instagram":
        # mo Instagram bang Chrome an, CHI DOC: con dang nhap khong + ten tai khoan (khong dung `sau instagram check`
        # vi lenh do tra ma 1 cho ca mat mang lan het han)
        code, out = run_cmd([str(py), str(Path(__file__).resolve()), "--ig-whoami", acc["cookie"]], repo, 5)
        u = re.search(r"tai_khoan:\s*([A-Za-z0-9_.]+)", out)
        user = u.group(1) if u else None
        st = "ok" if code == 0 and user else "het_han" if code == 1 and "IG_HET_HAN" in out else "khong_ro"
    elif acc["mang"] == "threads":
        code, out = run_cmd([str(py), str(HERE / "threads_dang.py"), "whoami", acc["cookie"], ghim(acc)], repo, 5)
        u = re.search(r"tai_khoan:\s*([A-Za-z0-9_.]+)", out)
        user = u.group(1) if u else None
        st = "ok" if code == 0 and user else "het_han" if code == 1 else "khong_ro"
    elif acc["mang"] == "facebook":
        # mo Business Suite bang Chrome an, CHI DOC: con dang nhap khong. Dung trang nao thi kiem luc dang (ghim 'page').
        code, out = run_cmd([str(repo_paths(cfg)[2]), "facebook-page", "check", "--account", acc["cookie"]], repo, 5)
        st = "ok" if code == 0 and "valid" in out and "invalid" not in out else "het_han" if code == 1 and "invalid" in out else "khong_ro"
        user = acc.get("page") if st == "ok" else None
    elif acc["mang"] == "youtube":
        # Kiem bang han cookie Google (khong mo Chrome an: Google hay chan -> bao sai "het han")
        try:
            cs = json.loads(cookie_file(cfg, acc).read_text(encoding="utf-8")).get("cookies", [])
        except Exception:
            return "het_han", None
        now_ts = time.time()
        live = [c for c in cs if c.get("name") in ("__Secure-3PSID", "SID", "LOGIN_INFO")
                and "youtube.com" in c.get("domain", "")
                and (c.get("expires", -1) == -1 or c.get("expires", 0) > now_ts + 3600)]
        st = "ok" if live else "het_han"
    else:
        st = "khong_ro"
    if st == "ok" and ghim(acc) and user and not cung_ten(user, ghim(acc)):
        st = "sai_tai_khoan"
    return st, user


def tiktok_whoami(cfg, cookie: str) -> tuple[str, str | None]:
    """Hoi TikTok file dang nhap nay la tai khoan nao. ('ok', ten@) | ('het_han', None) | ('khong_ro', None)"""
    f = Path(cfg["repo"]) / "cookies" / "tk_uploader" / f"{cookie}.json"
    try:
        cookies = json.loads(f.read_text(encoding="utf-8")).get("cookies", [])
    except Exception:
        return "het_han", None
    now_ts = time.time()
    sess = [c for c in cookies if c.get("name") == "sessionid" and "tiktok.com" in c.get("domain", "")]
    if not sess or not (sess[0].get("expires", -1) == -1 or sess[0].get("expires", 0) > now_ts + 3600):
        return "het_han", None
    try:
        hdr = {"Cookie": "; ".join(f"{c['name']}={c['value']}" for c in cookies
                                   if c.get("domain", "").endswith("tiktok.com")),
               "User-Agent": UA, "Referer": "https://www.tiktok.com/", "Accept": "application/json"}
        req = urllib.request.Request("https://www.tiktok.com/passport/web/account/info/?aid=1459", headers=hdr)
        with urllib.request.urlopen(req, timeout=20) as r:
            j = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return "khong_ro", None      # khong hoi duoc (mat mang / TikTok chan) -> luc dang se kiem lai trong Chrome
    d = j.get("data") or {}
    if j.get("message") == "success" and d.get("username"):
        return "ok", d["username"]
    if j.get("message") == "error":
        return "het_han", None       # chan nham thi cung chi la KHONG dang; moi luot hoi lai nen tu het
    return "khong_ro", None


def dn_record(acc, res: str, t, user: str | None) -> dict:
    """Ban ghi dang nhap: trang thai + ten @ that (neu biet) + ten @ da ghim."""
    rec = {"trang_thai": res, "luc": iso(t)}
    if user:
        rec["tai_khoan_that"] = user
    if ghim(acc):
        rec["can"] = ghim(acc)
    return rec


def kiem_dang_nhap(cfg, data, acc, t, force: bool, post_enabled: bool) -> None:
    ma = acc["ma"]
    st = data["dang_nhap"].get(ma, {})
    cf = cookie_file(cfg, acc)
    if not cf.exists():
        if st.get("trang_thai") != "chua_dang_nhap":
            log(f"Dang nhap {ma}: chua_dang_nhap")
        data["dang_nhap"][ma] = dn_record(acc, "chua_dang_nhap", t, None)
        return
    last = parse_t(st["luc"]) if st.get("luc") else None
    # vua dang nhap lai / vua dang xong (file dang nhap moi hon lan kiem cuoi) -> kiem ngay
    moi = last is not None and cf.stat().st_mtime > last.timestamp()
    doi_ghim = (st.get("can") or "") != ghim(acc)
    chua_on = st.get("trang_thai") != "ok" or not st.get("tai_khoan_that")
    if acc["mang"] == "tiktok":       # hoi qua mang, re -> chua on thi hoi lai moi luot
        lai = chua_on or doi_ghim
    elif acc["mang"] in ("instagram", "threads", "facebook"):  # phai mo Chrome an -> chua on thi 30 phut hoi lai 1 lan
        lai = doi_ghim or (chua_on and (last is None or t - last >= dt.timedelta(minutes=30)))
    else:
        lai = False
    if acc["mang"] == "facebook" and st.get("trang_thai") == "sai_tai_khoan" and not moi and not force:
        # Facebook: kiem dang nhap khong biet dang o trang nao -> khong duoc tu xoa canh bao "dang nham trang".
        # Chi mo khoa khi dang nhap lai (file dang nhap moi hon) hoac kiem bang tay (force).
        return
    due = (force or last is None or moi or lai
           or (t - last) > dt.timedelta(hours=cfg["kiem_tra_dang_nhap_moi_gio"]))
    if not (due and (post_enabled or force)):
        return
    res, user = check_login(cfg, acc)
    if res == "khong_ro" and not user and not moi and not doi_ghim:
        user = st.get("tai_khoan_that")          # khong hoi duoc: file dang nhap chua doi nen ten cu van dung
    cu = (st.get("trang_thai"), st.get("tai_khoan_that"))
    data["dang_nhap"][ma] = dn_record(acc, res, t, user)
    if (res, user) != cu or force:
        log(f"Dang nhap {ma}: {res}" + (f" (@{user})" if user else "") + (f" - can @{ghim(acc)}" if res == "sai_tai_khoan" else ""))


def ly_do_chan(acc, dn: dict) -> str | None:
    """Vi sao tai khoan nay CHUA duoc dang (None = duoc dang)."""
    tt = dn.get("trang_thai")
    if tt in DN_CHAN:
        ly_do = DN_CHAN[tt]
        if tt == "sai_tai_khoan" and dn.get("tai_khoan_that") and dn.get("can"):
            ly_do += f" — đang ở @{dn['tai_khoan_that']}, cần @{dn['can']}"
        return ly_do
    want = ghim(acc)
    if want and acc["mang"] in ("instagram", "threads") and not (tt in ("ok", "khong_ro") and cung_ten(dn.get("tai_khoan_that"), want)):
        # Instagram: may dang khong tu so ten kenh nhu TikTok -> phai biet chac dang o dung kenh moi dang
        return f"Chưa kiểm được {'Threads' if acc['mang'] == 'threads' else 'Instagram'} đang đăng nhập tài khoản nào (cần @{want}) → chưa đăng, máy tự kiểm lại"
    return None


# ---------------------------------------------------------------- lich
def slots_on(acc, day: dt.date, bao_loi: bool = False) -> list[dt.datetime]:
    out = []
    for s in acc.get("khung_gio") or []:
        try:
            h, m = map(int, str(s).split(":"))
            out.append(dt.datetime.combine(day, dt.time(h, m)))
        except Exception:
            if bao_loi:
                log(f"Khung gio sai dinh dang '{s}' o tai khoan {acc['ma']}")
    return sorted(out)


def khoa_khung(s: dt.datetime) -> str:
    return s.strftime("%Y-%m-%d %H:%M")


def trung_khung_cu(done: dict, s: dt.datetime, cur_keys: set) -> bool:
    """Vua doi gio: khung moi nam sat (<= 60 phut) mot khung cu da chay that -> coi nhu da xong, khong dang them."""
    for k, d in done.items():
        if k in cur_keys or d.get("tam") or k[:10] != s.strftime("%Y-%m-%d"):
            continue
        try:
            if abs((dt.datetime.strptime(k, "%Y-%m-%d %H:%M") - s).total_seconds()) <= 3600:
                return True
        except ValueError:
            continue
    return False


def khung_hien_tai(acc, t: dt.datetime) -> set:
    return {khoa_khung(s) for d in (-1, 0, 1) for s in slots_on(acc, t.date() + dt.timedelta(days=d))}


# ---------------------------------------------------------------- dang 1 tai khoan
def ap_dung(cfg, data, acc, key: str, tep: list[str], caption: str, res: dict) -> None:
    """Ghi ket qua 1 lan dang. THU TU BAT BUOC: ghi so (du-lieu.json) truoc, chuyen file sau.
    tep = ten cac file trong cho-dang (video dung dau)."""
    ma = acc["ma"]
    done = data["da_xu_ly"].setdefault(ma, {})
    tries_key = f"{ma}|{tep[0]}" if acc.get("dang_ngay") else f"{ma}|{key}"
    rec = data["thu"].get(tries_key) or {"n": 1, "tu": iso(now())}
    t = now()
    entry = {"tk": ma, "khung": key, "luc": iso(t), "file": tep[0], "caption": caption.splitlines()[0][:120] if caption else ""}
    if res.get("tai_khoan"):
        entry["tai_khoan"] = res["tai_khoan"]
    chuyen = None          # (thu muc dich, tien to ten file)
    ghi_chu_loi = None     # noi dung file .loi.txt
    if res.get("ok"):
        entry.update(kq="ok", link=res.get("link"), id=res.get("id"))
        done[key] = {"kq": "ok", "luc": entry["luc"], "file": tep[0], "link": res.get("link")}
        if res.get("canh_bao"):       # da dang, nhung co dieu chu may can xem (bang hien do)
            entry["loi"] = done[key]["loi"] = res["canh_bao"]
        if res.get("sai_kenh"):       # bai da len nhung nham kenh: ghi la da dang (de khong dang lai) + bao do
            entry["loi"] = done[key]["loi"] = res["sai_kenh"]
            data["dang_nhap"][ma] = dn_record(acc, "sai_tai_khoan", t, res.get("tai_khoan"))
        else:                         # ten @ doc ngay trong phien vua dang -> la bang chung moi nhat
            data["dang_nhap"][ma] = dn_record(acc, "ok", now(), res.get("tai_khoan") or data["dang_nhap"].get(ma, {}).get("tai_khoan_that"))
        data["thu"].pop(tries_key, None)
        chuyen = ("da-dang", f"{t:%Y-%m-%d_%H%M}_")
        log(f"  -> OK {res.get('link') or res.get('id') or ''}" + (f" (@{res['tai_khoan']})" if res.get("tai_khoan") else "")
            + (" !!! NHAM KENH" if res.get("sai_kenh") else ""))
    elif res.get("chua_ro"):
        # da bam nut dang nhung khong co bang chung: KHONG thu lai (tranh dang trung), dua video ra khoi hang cho
        entry.update(kq="chua_ro", loi=res["loi"])
        done[key] = {"kq": "chua_ro", "luc": entry["luc"], "file": tep[0], "loi": res["loi"]}
        data["thu"].pop(tries_key, None)
        chuyen = ("loi", "")
        ghi_chu_loi = f"{entry['luc']}\nCHƯA RÕ ĐÃ ĐĂNG HAY CHƯA\n{res['loi']}\n"
        log(f"  -> CHUA RO: {res['loi']}")
    else:
        loi = res.get("loi") or "Không rõ lỗi"
        entry.update(kq="loi", loi=loi)
        log(f"  -> LOI: {loi}")
        loi_dn = res.get("dang_nhap")
        if loi_dn:
            rec["dn"] = rec.get("dn", 0) + 1
        if res.get("da_bam") or res.get("cho_xn"):
            # TikTok: da bam Post ma chua thay bai -> KHONG tai len lai ngay (tranh dang trung). Giu video trong hang cho,
            # cac luot sau chi KIEM (khong tai); du cho_xac_nhan_phut ke tu luc bam moi duoc tai len lai.
            if res.get("da_bam"):
                rec["cho_xn"] = entry["luc"]
            data["thu"][tries_key] = rec
            if not acc.get("dang_ngay"):
                done[key] = {"kq": "loi", "luc": entry["luc"], "file": tep[0], "loi": loi, "tam": True}
        elif loi_dn and rec["dn"] <= 3:
            # may dang bao sai tai khoan / het han: giu nguyen hang cho, khong tinh la 1 lan thu (toi da 3 lan)
            data["dang_nhap"][ma] = dn_record(acc, loi_dn, t, res.get("tai_khoan"))
            rec["n"] = max(0, rec.get("n", 1) - 1)
            data["thu"][tries_key] = rec
            if not acc.get("dang_ngay"):
                done[key] = {"kq": "loi", "luc": entry["luc"], "file": tep[0], "loi": loi, "tam": True, "chan": True}
        elif rec.get("n", 1) >= cfg["so_lan_thu_lai"]:
            done[key] = {"kq": "loi", "luc": entry["luc"], "file": tep[0], "loi": loi}
            data["thu"].pop(tries_key, None)
            chuyen = ("loi", "")
            ghi_chu_loi = f"{entry['luc']}\n{loi}\n\nSửa xong thì nhờ Claude đưa video + .txt về lại cho-dang.\n"
        else:
            if not acc.get("dang_ngay"):
                done[key] = {"kq": "loi", "luc": entry["luc"], "file": tep[0], "loi": loi, "tam": True}
            if not loi_dn:
                data["dang_nhap"].setdefault(ma, {})["luc"] = None      # luot sau kiem lai dang nhap
    data["dang_do"].pop(ma, None)
    if not res.get("cho_xn"):                 # luot chi-kiem chua thay bai: khong ghi them dong lich su (10 phut 1 dong la rac)
        data["lich_su"].insert(0, entry)
    data["lich_su"] = data["lich_su"][:300]
    da_ghi = luu(data)
    if chuyen:
        if ghi_chu_loi:
            try:
                d = Path(acc["thu_muc"]) / "loi"
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{Path(tep[0]).stem}.loi.txt").write_text(ghi_chu_loi, encoding="utf-8")
            except Exception as e:
                log(f"  khong ghi duoc file .loi.txt: {e}")
        chuyen_file(data, acc, tep, chuyen[0], chuyen[1])
        da_ghi = luu(data) and da_ghi
    if da_ghi and acc["mang"] == "instagram":
        ig_res_file(acc).unlink(missing_ok=True)     # chi xoa bang chung khi so da ghi xong
    if da_ghi and acc["mang"] == "facebook":
        fb_res_file(acc).unlink(missing_ok=True)


def phuc_hoi(cfg, data, acc) -> None:
    """Luot truoc bi tat giua chung (mat dien, may ngu, bi dong) khi dang dang do 1 video -> xu ly not truoc khi dang tiep."""
    ma = acc["ma"]
    dd = data["dang_do"].get(ma)
    if not dd:
        return
    tep = [n for n in (dd.get("tep") or [dd.get("file")]) if n]
    log(f"{ma}: luot truoc dung giua chung khi dang {dd.get('file')} -> kiem lai")
    if acc["mang"] == "instagram" and tep:
        res = doc_ket_qua_ig(acc)
        if res.get("ok") or res.get("chua_ro"):
            ap_dung(cfg, data, acc, dd.get("khung") or khoa_khung(now()), tep, dd.get("caption") or "", res)
            return
    if acc["mang"] == "facebook" and tep:
        res = doc_ket_qua_fb(acc)
        if res.get("ok") or res.get("chua_ro"):
            ap_dung(cfg, data, acc, dd.get("khung") or khoa_khung(now()), tep, dd.get("caption") or "", res)
            return
    if acc["mang"] == "threads" and tep and dau_threads(acc["cookie"]).exists():
        ap_dung(cfg, data, acc, dd.get("khung") or khoa_khung(now()), tep, dd.get("caption") or "", {"ok": False, "chua_ro": True,
                "loi": "Máy bị tắt ngay sau khi bấm Post trên Threads. Mở Threads xem bài đã lên chưa; chưa có thì nhờ Claude đưa video về lại hàng chờ."})
        return
    # TikTok: lan thu sau tu tim bai da len (theo gio bat dau thu) truoc khi dang. Mang khac: chua bam nut dang -> thu lai binh thuong.
    if acc["mang"] == "tiktok" and dd.get("file") and dau_da_bam(acc["cookie"]).exists():
        # may tat SAU khi da bam Post: coi nhu "co the da dang" -> cho + kiem lai, khong tai len lai ngay
        tk = f"{ma}|{dd['file']}" if acc.get("dang_ngay") else f"{ma}|{dd.get('khung')}"
        r = data["thu"].setdefault(tk, {"n": 1, "tu": dd.get("luc") or iso(now())})
        r.setdefault("cho_xn", dd.get("luc") or iso(now()))
    data["dang_do"].pop(ma, None)
    luu(data)


def dang_1_video(cfg, data, acc, t: dt.datetime, key: str, item: dict, d: dict, sys_errors: list) -> bool:
    """Dang 1 video (item tu scan_queue) cho khung 'key'. Tra False neu phai dung ca luot (khong ghi duoc so)."""
    ma = acc["ma"]
    done = data["da_xu_ly"].setdefault(ma, {})
    ly_do = ly_do_chan(acc, data["dang_nhap"].get(ma, {}))
    if ly_do:
        # KHONG dang, KHONG dung video: giu nguyen hang cho; sua dang nhap xong (trong cua so) la tu dang
        if not acc.get("dang_ngay"):
            if d.get("loi") != ly_do:
                log(f"{ma} {key}: {ly_do}")
            done[key] = {"kq": "loi", "luc": iso(t), "file": item["video"].name, "loi": ly_do, "tam": True, "chan": True}
        return True
    tries_key = f"{ma}|{item['video'].name}" if acc.get("dang_ngay") else f"{ma}|{key}"
    rec = data["thu"].setdefault(tries_key, {"n": 0, "tu": iso(now())})
    tep = list(dict.fromkeys(f.name for f in (item["video"], item["txt"], item["thumb"], item.get("gio_file")) if f))
    chi_kiem = False
    if acc["mang"] == "tiktok" and rec.get("cho_xn"):
        # luot truoc da bam Post ma chua thay bai
        if t - parse_t(rec["cho_xn"]) < dt.timedelta(minutes=cfg["cho_xac_nhan_phut"]):
            chi_kiem = True                       # chua du thoi gian cho: chi kiem, KHONG tai len
        elif rec.get("n", 0) >= cfg["so_lan_thu_lai"]:
            # da tai len du so lan, lan nao cung bam Post ma TikTok khong hien bai -> dung han, khong tai nua
            rec.pop("cho_xn", None)
            ap_dung(cfg, data, acc, key, tep, item["caption"], {"ok": False, "chua_ro": True, "loi": (
                f"Đã bấm Post {rec.get('n', 0)} lần nhưng sau {cfg['cho_xac_nhan_phut']} phút TikTok vẫn không hiện bài. "
                "Mở TikTok xem bài có lên không; chưa có thì nhờ Claude đưa video về lại hàng chờ.")})
            return True
        else:
            rec.pop("cho_xn", None)               # da cho du, bai khong len -> duoc tai len lai (lan ke)
    if chi_kiem:
        rec["chi_kiem"] = True
    else:
        rec["n"] = rec.get("n", 0) + 1
    data["dang_do"][ma] = {"khung": key, "file": item["video"].name, "tep": tep, "luc": iso(now()),
                           "caption": item["caption"].splitlines()[0][:120]}
    if not luu(data):
        # khong ghi duoc so thi khong dang: dang ma khong ghi lai duoc la se dang trung
        rec["n"] -= 1
        data["dang_do"].pop(ma, None)
        sys_errors.append("Không ghi được du-lieu.json (file đang bị chương trình khác mở?) → lượt này máy không đăng.")
        return False
    log(f"{ma} {key}: " + (f"kiem lai bai da bam Post {item['video'].name} (chua tai len lai)" if chi_kiem
                           else f"dang {item['video'].name} (lan {rec['n']})"))
    try:
        res = POSTERS[acc["mang"]](cfg, acc, item, rec)
    except Exception as e:
        res = {"ok": False, "loi": f"{type(e).__name__}: {e}"}
    ap_dung(cfg, data, acc, key, tep, item["caption"], res)
    return True


def dang_tai_khoan(cfg, data, acc, t: dt.datetime, sys_errors: list) -> None:
    ma = acc["ma"]
    done = data["da_xu_ly"].setdefault(ma, {})
    window = dt.timedelta(minutes=cfg["cua_so_phut"])
    grace = min(window, dt.timedelta(minutes=cfg["cho_video_phut"]))
    don_file_ton(data, acc)
    phuc_hoi(cfg, data, acc)
    if acc["mang"] == "facebook":
        chep_tu_nguon(data, acc)
    if acc.get("dang_ngay"):
        # co video la dang (moi luot 1 video, cach nhau >= cach_toi_thieu_phut)
        gap = dt.timedelta(minutes=acc.get("cach_toi_thieu_phut", 30))
        last = max((parse_t(v["luc"]) for v in done.values() if v.get("kq") == "ok" and v.get("luc")), default=None)
        co = scan_queue(acc, video_cho_don(data, acc))["ready"]
        due = [t] if co and (last is None or t - last >= gap) else []
    else:
        cur = khung_hien_tai(acc, t)
        due = []
        for ngay in (t.date() - dt.timedelta(days=1), t.date()):      # ca hom qua: khung sat nua dem van con cua so
            for s in slots_on(acc, ngay, bao_loi=ngay == t.date()):
                d = done.get(khoa_khung(s))
                if s <= t < s + window and (not d or d.get("tam")) and not trung_khung_cu(done, s, cur):
                    due.append(s)
    for s in due:
        key = khoa_khung(s)
        d = done.get(key) or {}
        q = scan_queue(acc, video_cho_don(data, acc))
        if not q["ready"]:
            # chua co video: cho them 'cho_video_phut' (video chep muon van kip), qua thi bo khung nay
            con_cho = t < s + grace and not d
            if d.get("kq") == "het_video" and t < s + grace:
                continue
            if not d or d.get("kq") == "het_video":
                done[key] = {"kq": "het_video", "luc": iso(t)}
                if con_cho:
                    done[key]["tam"] = True
                    log(f"{ma} {key}: hang cho trong -> cho video them {cfg['cho_video_phut']} phut")
                else:
                    log(f"{ma} {key}: hang cho trong -> bo lo khung nay")
            continue
        if d.get("kq") == "het_video" and t >= s + grace:
            done[key] = {"kq": "het_video", "luc": iso(t)}       # video den qua muon -> de danh cho khung sau
            log(f"{ma} {key}: video den sau {cfg['cho_video_phut']} phut -> de danh cho khung sau")
            continue
        item = chon_bai_threads(data, acc, q["ready"]) if acc["mang"] == "threads" else q["ready"][0]
        if dang_1_video(cfg, data, acc, t, key, item, d, sys_errors) is False:
            return
    # ---- video hen gio rieng (<ten>.gio.txt): dang dung gio ghi trong file, khong dung khung_gio
    if not acc.get("dang_ngay"):
        for item in scan_queue(acc, video_cho_don(data, acc)).get("hen_gio", []):
            g = item["gio"]
            if not (g <= t < g + window):
                continue
            key = f"{khoa_khung(g)} hen {item['video'].name}"
            d = done.get(key) or {}
            if d and not d.get("tam"):
                continue
            if dang_1_video(cfg, data, acc, t, key, item, d, sys_errors) is False:
                return


# ---------------------------------------------------------------- 1 luot chay
def run_once(post_enabled=True, force_check=False) -> None:
    cfg = load_cfg()
    sys_errors: list[str] = []
    t = now()
    accounts = tai_khoan_hop_le(cfg, sys_errors)
    data, ghi_chu = load_data()
    if ghi_chu:
        sys_errors.append(ghi_chu)
    khong_so = data is None
    if khong_so:                       # so ghi hong ca 2 ban: chi bao loi, khong dang, khong ghi de
        data = {"da_xu_ly": {}, "lich_su": [], "dang_nhap": {}, "thu": {}, "dang_do": {}, "cho_don": {}}
        post_enabled = False
    lech = t.astimezone().utcoffset()
    if lech != dt.timedelta(hours=8):
        sys_errors.append("Giờ của laptop không phải giờ Đài Loan (UTC+8) → các khung giờ sẽ lệch. Chỉnh lại múi giờ Windows.")

    try:
        # 1) dang nhap
        for acc in accounts:
            try:
                kiem_dang_nhap(cfg, data, acc, t, force_check and not khong_so, post_enabled)
            except Exception as e:
                sys_errors.append(f"Kiểm tra đăng nhập {acc['ma']}: {type(e).__name__}: {e}")
                log(f"LOI kiem dang nhap {acc['ma']}:\n{traceback.format_exc()}")

        # ghi trang thai ngay (bang theo doi khong phai cho dang xong moi thay ket qua dang nhap)
        if not khong_so:
            luu(data)
        try:
            write_status(cfg, data, accounts, sys_errors, cuoi=False)
        except Exception as e:
            log(f"Khong ghi duoc trang thai som: {e}")

        # 2) dang theo khung gio: loi cua 1 tai khoan khong duoc chan tai khoan khac
        if post_enabled:
            for acc in accounts:
                try:
                    dang_tai_khoan(cfg, data, acc, t, sys_errors)
                except Exception as e:
                    sys_errors.append(f"{acc['ma']}: lỗi khi đăng — {type(e).__name__}: {e}")
                    log(f"LOI khi dang {acc['ma']}:\n{traceback.format_exc()}")

        # don du lieu cu
        cutoff = (t - dt.timedelta(days=14)).strftime("%Y-%m-%d")
        for ma in data["da_xu_ly"]:
            data["da_xu_ly"][ma] = {k: v for k, v in data["da_xu_ly"][ma].items() if k[:10] >= cutoff}
        han = t - dt.timedelta(days=3)
        data["thu"] = {k: v for k, v in data["thu"].items()
                       if not (isinstance(v, dict) and v.get("tu") and parse_t(v["tu"]) < han)}
    finally:
        # du co chuyen gi cung phai ghi so + ghi trang thai (khong thi bang bao sai "laptop tat")
        if not khong_so and not luu(data):
            sys_errors.append("Không ghi được du-lieu.json (file đang bị chương trình khác mở?). Nhờ Claude kiểm tra.")
        write_status(cfg, data, accounts, sys_errors, cuoi=not khong_so)


# ---------------------------------------------------------------- trang thai
def the_tai_khoan(cfg, data, acc, t: dt.datetime) -> dict:
    window = dt.timedelta(minutes=cfg["cua_so_phut"])
    grace = min(window, dt.timedelta(minutes=cfg["cho_video_phut"]))
    hom_nay = t.strftime("%Y-%m-%d")
    done = data["da_xu_ly"].get(acc["ma"], {})
    q = scan_queue(acc, video_cho_don(data, acc))
    ten_tt = {"ok": "da_dang", "het_video": "het_video", "loi": "loi", "chua_ro": "chua_ro"}

    def dong(gio, st, d):
        return {"gio": gio, "trang_thai": st, "file": (d or {}).get("file"), "link": (d or {}).get("link"),
                "loi": (d or {}).get("loi")}

    today = []
    if acc.get("dang_ngay"):
        keys = sorted(k for k in done if k[:10] == hom_nay)
        da_len = {done[k].get("file") for k in keys if done[k].get("kq") == "ok"}
        for key in keys:
            d = done[key]
            if d.get("kq") == "loi" and d.get("file") in da_len:
                continue          # lan thu loi nhung sau do video nay da dang duoc -> khong bao do nua
            today.append(dong(key[11:16], ten_tt.get(d["kq"], d["kq"]), d))
        slots = []
    else:
        slots = slots_on(acc, t.date())
        cur = khung_hien_tai(acc, t)
        # khung cu (truoc khi doi gio) hom nay van hien de khong mat lich su
        for key in sorted(k for k in done if k[:10] == hom_nay and k not in cur and not done[k].get("tam")):
            today.append(dong(key[11:16], ten_tt.get(done[key]["kq"], done[key]["kq"]), done[key]))
    i_video = 0               # video san sang ke tiep chua gan cho khung nao
    for s in slots:
        key = khoa_khung(s)
        d = done.get(key)
        trong = s <= t < s + window
        if (not d or d.get("tam")) and trung_khung_cu(done, s, cur):
            continue          # khung moi trung voi khung cu da chay hom nay -> khong hien 2 lan
        if d and not (d.get("tam") and trong):
            st = ten_tt.get(d["kq"], d["kq"])
        elif d:               # ban ghi tam trong cua so: may con xu ly tiep
            st = ("cho_video" if t < s + grace else "het_video") if d["kq"] == "het_video" else "bi_chan" if d.get("chan") else "thu_lai"
        elif t < s:
            st = "sap_toi"
        elif trong:
            st = "dang_xu_ly"
        else:
            st = "bo_lo"      # khong co luot chay nao trong cua so: may tat / ngu luc do
        row = dong(s.strftime("%H:%M"), st, d)
        if st in ("dang_xu_ly", "cho_video", "bi_chan", "thu_lai"):
            row["du_kien"] = q["ready"][i_video]["video"].name if i_video < len(q["ready"]) else None
            i_video += 1
        today.append(row)
    today.sort(key=lambda x: x["gio"])
    upcoming = [s for d in range(0, 8) for s in slots_on(acc, t.date() + dt.timedelta(days=d))
                if t < s <= t + dt.timedelta(days=7)]
    lich = []
    if acc.get("dang_ngay") and q["ready"]:
        lich.append({"luc": None, "file": q["ready"][0]["video"].name})
    for i, s in enumerate(upcoming[:28]):
        it = q["ready"][i_video + i] if i_video + i < len(q["ready"]) else None
        lich.append({"luc": iso(s), "file": it["video"].name if it else None})
        if s.date() == t.date():
            for row in today:
                if row["gio"] == s.strftime("%H:%M") and row["trang_thai"] == "sap_toi":
                    row["du_kien"] = it["video"].name if it else None
    n_slots = max(1, len(acc.get("khung_gio") or []))
    last_ok = next((h for h in data["lich_su"] if h.get("tk") == acc["ma"] and h.get("kq") == "ok"), None)
    loi_dir = Path(acc["thu_muc"]) / "loi"
    return {
        "ma": acc["ma"], "mang": acc["mang"], "ten": acc.get("ten_hien_thi") or acc["cookie"],
        "kenh": acc.get("kenh", ""), "khung_gio": acc.get("khung_gio") or [], "dang_ngay": bool(acc.get("dang_ngay")),
        "cach_phut": acc.get("cach_toi_thieu_phut", 30) if acc.get("dang_ngay") else None,
        "username": ghim(acc) or None,
        "hom_nay": today, "lich_toi": lich,
        "hang_cho": {
            "san_sang": len(q["ready"]),
            "ds": [{"file": r["video"].name, "caption": r["caption"].splitlines()[0][:100],
                    "anh_bia": bool(r["thumb"])} for r in q["ready"][:10]],
            "thieu_caption": q["thieu_caption"], "thieu_video": q["thieu_video"],
            "caption_loi": q["caption_loi"],
            "hen_gio": [{"file": r["video"].name, "gio": iso(r["gio"])} for r in q.get("hen_gio", [])],
            "gio_loi": q.get("gio_loi", []),
            "cho_don": sorted(video_cho_don(data, acc)),
            "du_ngay": round(len(q["ready"]) / n_slots, 1),
        },
        "loi_cho_sua": sorted(f.name for f in loi_dir.glob("*.loi.txt")) if loi_dir.exists() else [],
        "dang_nhap": data["dang_nhap"].get(acc["ma"], {"trang_thai": "chua_kiem_tra"}),
        "lan_dang_cuoi": last_ok,
    }


def write_status(cfg, data, accounts, sys_errors, cuoi: bool = True) -> None:
    t = now()
    out_acc = []
    loi = list(sys_errors)
    for acc in accounts:
        try:
            out_acc.append(the_tai_khoan(cfg, data, acc, t))
        except Exception as e:      # 1 tai khoan loi khong duoc lam mat ca bang
            loi.append(f"{acc['ma']}: không đọc được trạng thái — {type(e).__name__}: {e}")
            log(f"LOI ghi trang thai {acc['ma']}:\n{traceback.format_exc()}")
    status = {
        "phien_ban": PHIEN_BAN, "cap_nhat_luc": iso(t), "ngay": t.strftime("%Y-%m-%d"), "may": socket.gethostname(),
        "chu_ky_phut": cfg.get("chu_ky_phut", 10), "cua_so_phut": cfg["cua_so_phut"],
        "thu_muc_drive": cfg.get("thu_muc_drive"), "tai_khoan": out_acc,
        "lich_su": data["lich_su"][:40], "loi_he_thong": loi,
    }
    write_json(STATUS_FILE, status)
    drive_dir = cfg.get("thu_muc_drive")
    if drive_dir:
        mat = None
        try:
            if Path(drive_dir).exists():
                # ghi de thang len file cu (khong doi ten file tam): Google Drive giu nguyen ID file -> bang doc on dinh
                shutil.copyfile(STATUS_FILE, Path(drive_dir) / STATUS_FILE.name)
            else:
                mat = f"Khong thay thu muc Drive {drive_dir} (Google Drive cho may tinh chua mo?) -> bang theo doi khong duoc cap nhat"
        except Exception as e:
            mat = f"Khong chep duoc len Drive: {e}"
        if cuoi:                     # chi ghi nhat ky khi tinh trang doi (khong ghi 2 dong moi luot)
            if mat and data.get("drive_mat") != mat:
                log(mat)
            elif not mat and data.get("drive_mat"):
                log("Da chep lai duoc trang thai len Drive")
            if (mat or None) != data.get("drive_mat"):
                data["drive_mat"] = mat
                luu(data)


def bao_loi_he_thong(msg: str) -> None:
    """Khong chay duoc luot nao (vd cau-hinh.json hong): van bao len bang thay vi de bang tuong 'laptop tat'."""
    log("LOI HE THONG: " + msg)
    try:
        st = read_json(STATUS_FILE, None)
        if not isinstance(st, dict) or not isinstance(st.get("tai_khoan"), list):
            st = {"phien_ban": PHIEN_BAN, "may": socket.gethostname(), "tai_khoan": [], "lich_su": []}
        st["cap_nhat_luc"] = iso(now())
        st["ngay"] = now().strftime("%Y-%m-%d")
        st["loi_he_thong"] = [msg]
        write_json(STATUS_FILE, st)
        cfg = read_json(CFG_FILE, None)
        drive_dir = (cfg.get("thu_muc_drive") if isinstance(cfg, dict) else None) or st.get("thu_muc_drive")
        if drive_dir and Path(drive_dir).exists():
            shutil.copyfile(STATUS_FILE, Path(drive_dir) / STATUS_FILE.name)
    except Exception as e:
        log(f"Khong bao duoc loi he thong len bang: {e}")


# ---------------------------------------------------------------- khoa 1 luot
def pid_song(pid: int) -> bool:
    """Tien trinh `pid` con chay va la python (PID co the bi Windows cap lai cho chuong trinh khac)."""
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except OSError:
            return True
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        k.OpenProcess.restype = wintypes.HANDLE
        h = k.OpenProcess(0x1000, False, pid)            # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = wintypes.DWORD()
            if not k.GetExitCodeProcess(wintypes.HANDLE(h), ctypes.byref(code)) or code.value != 259:
                return False
            buf = ctypes.create_unicode_buffer(1024)
            n = wintypes.DWORD(1024)
            if k.QueryFullProcessImageNameW(wintypes.HANDLE(h), 0, buf, ctypes.byref(n)):
                return "python" in buf.value.lower()
            return True
        finally:
            k.CloseHandle(wintypes.HANDLE(h))
    except Exception:
        return True          # khong kiem duoc -> coi nhu con song (an toan: khong chay chong)


def may_bat_luc() -> float:
    """Thoi diem Windows khoi dong (0 = khong biet)."""
    try:
        import ctypes
        ctypes.windll.kernel32.GetTickCount64.restype = ctypes.c_ulonglong
        return time.time() - ctypes.windll.kernel32.GetTickCount64() / 1000.0
    except Exception:
        return 0.0


def khoa_cu() -> bool:
    """Khoa cua luot truoc da het hieu luc? (luot do da tat, hoac khoa co tu truoc khi may khoi dong lai, hoac treo qua lau)"""
    try:
        st = LOCK_FILE.stat()
        pid = int((LOCK_FILE.read_text().split() or ["0"])[0])
    except FileNotFoundError:
        return True
    except Exception:
        return time.time() - LOCK_FILE.stat().st_mtime > 120       # file khoa dang ghi do / rac
    if time.time() - st.st_mtime > KHOA_TOI_DA_GIO * 3600:
        return True
    if st.st_mtime < may_bat_luc() - 60:
        return True
    return not pid_song(pid)


def giu_khoa() -> bool:
    for _ in range(2):
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {now():%Y-%m-%dT%H:%M:%S}".encode())
            os.close(fd)
            return True
        except FileExistsError:
            if not khoa_cu():
                return False
            try:
                LOCK_FILE.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                return False
    return False


def cham_khoa() -> None:
    """Bao 'luot nay con song' (doi gio sua file khoa) truoc/sau moi buoc dai."""
    try:
        if LOCK_FILE.exists():
            os.utime(LOCK_FILE, None)
    except OSError:
        pass


# ---------------------------------------------------------------- che do noi bo
def tiktok_one(cookie: str, video: str, txt: str, thumb: str, username: str = "", tu_luc: str = "", chi_kiem: str = "") -> int:
    cfg = load_cfg()
    repo = Path(cfg["repo"])
    os.chdir(repo)
    sys.path.insert(0, str(repo))
    import asyncio
    from uploader.tk_uploader.main_chrome import TiktokVideo
    acct = repo / "cookies" / "tk_uploader" / f"{cookie}.json"
    caption = read_caption(Path(txt))
    app = TiktokVideo(caption, Path(video), [], 0, str(acct), Path(thumb) if thumb else None)
    app.headless = bool(cfg.get("tiktok_an_trinh_duyet", False))  # mac dinh hien Chrome: TikTok hay chan che do an
    app.expected_username = username or None   # sai tai khoan -> main_chrome tu dung, khong dang
    app.tu_luc = float(tu_luc) if tu_luc else time.time()   # chi coi la "bai nay" neu duoc tao tu lan thu dau tien tro di
    app.chi_kiem = bool(chi_kiem)
    dau = dau_da_bam(cookie)
    app.khi_bam_post = lambda: dau.write_text(iso(now()) or "", encoding="utf-8")
    try:
        asyncio.run(app.main())
    except Exception as e:
        msg = (str(e).strip().splitlines() or [""])[0][:300]
        print(f"LOI_DANG: {msg if isinstance(e, RuntimeError) else type(e).__name__ + ': ' + msg}", flush=True)
        return 1
    if not getattr(app, "video_id", None):
        print("LOI_DANG: KHONG_XAC_NHAN: khong co id bai tu TikTok", flush=True)
        return 1
    return 0


def tiktok_check(cookie: str) -> int:
    """Lenh tay: in ra file dang nhap nay dang o tai khoan TikTok nao. 0 = con dang nhap, 1 = het han."""
    st, user = tiktok_whoami(load_cfg(), cookie)
    print(f"{cookie}: {st}" + (f" (@{user})" if user else ""))
    return 1 if st == "het_han" else 0


def ig_whoami(cookie: str) -> int:
    """CHI DOC: mo Instagram bang Chrome an voi file dang nhap, in 'tai_khoan: <ten>'.
    Ma thoat: 0 = con dang nhap, 1 = het han (in IG_HET_HAN), 2 = khong ro (mat mang, Instagram doi giao dien...)."""
    cfg = load_cfg()
    repo = Path(cfg["repo"])
    os.chdir(repo)
    sys.path.insert(0, str(repo))
    import asyncio
    f = repo / "cookies" / f"instagram_{cookie}.json"

    async def chay():
        from patchright.async_api import async_playwright
        from uploader.meta_uploader.insgraph_uploader import main as ig
        async with async_playwright() as p:
            browser, _ctx, page = await ig._open_instagram_page(p, f, proxy=None, headless=True)
            try:
                if await ig._is_instagram_logged_out(page):
                    return None
                return (await ig.instagram_identity(page, f))["username"]
            finally:
                await browser.close()

    try:
        user = asyncio.run(chay())
    except Exception as e:
        msg = (str(e).strip().splitlines() or [""])[0][:200]
        if isinstance(e, RuntimeError) and ("未登录" in msg or "不匹配" in msg):
            print("IG_HET_HAN: " + msg, flush=True)
            return 1
        print(f"IG_KHONG_RO: {type(e).__name__}: {msg}", flush=True)
        return 2
    if not user:
        print("IG_HET_HAN", flush=True)
        return 1
    print(f"tai_khoan: {user}", flush=True)
    return 0


def ghim_tai_khoan() -> int:
    """XAC_NHAN_TAI_KHOAN.bat: voi moi tai khoan chua ghim ten @, hoi chu may 'dung kenh khong' roi ghi vao cau-hinh.json."""
    cfg = load_cfg()
    data = read_json(DATA_FILE, {})
    dn = data.get("dang_nhap", {}) if isinstance(data, dict) else {}
    raw = json.loads(CFG_FILE.read_text(encoding="utf-8-sig"))
    doi = 0
    for acc in raw["tai_khoan"]:
        if not isinstance(acc, dict) or not acc.get("bat", True) or acc.get("mang") not in ("tiktok", "instagram", "threads"):
            continue
        ma = f"{acc.get('mang')}_{acc.get('cookie')}"
        if str(acc.get("username") or "").strip():
            print(f"  {ma}: đã ghim @{acc['username']}")
            continue
        that = (dn.get(ma) or {}).get("tai_khoan_that")
        if not that:
            print(f"  {ma}: máy chưa biết đang đăng nhập tài khoản nào → bấm KIEM_TRA_DANG_NHAP.bat rồi chạy lại file này.")
            continue
        print(f"\n  {acc.get('mang').upper()} '{acc.get('ten_hien_thi') or acc.get('cookie')}' đang đăng nhập tài khoản:  @{that}")
        tl = input("  Đây có ĐÚNG là kênh bạn muốn máy đăng lên không?  Gõ C rồi Enter = đúng, ghim lại.  Enter = bỏ qua: ")
        if tl.strip().lower() in ("c", "co", "có", "y", "yes"):
            acc["username"] = that
            doi += 1
            print(f"  → Đã ghim @{that}. Từ giờ nếu đăng nhập sang tài khoản khác, máy sẽ KHÔNG đăng.")
    if doi:
        luu_cu = HERE / f"cau-hinh.truoc-ghim-{now():%Y%m%d-%H%M%S}.json"
        shutil.copyfile(CFG_FILE, luu_cu)
        write_json(CFG_FILE, raw)
        log(f"Ghim ten @ cho {doi} tai khoan (ban cu: {luu_cu.name})")
        print("\nĐã lưu. Bảng theo dõi sẽ cập nhật trong vòng 10 phút.")
    else:
        print("\nKhông có gì thay đổi.")
    return 0


def chay_viec_cho() -> None:
    """Viec bao tri chay 1 LAN khi khong ai ngoi truoc may: dat file chay-1-lan.json =
    [{"file": "thu_tiktok.py", "args": ["vietwan"]}]. Chi chay cac file .py co san trong thu muc nay
    (danh sach VIEC_DUOC). Ket qua: chan-doan\\viec-<so>-<ten>.log. File lenh bi doi ten truoc khi chay nen khong lap lai."""
    if not VIEC_FILE.exists():
        return
    viec = read_json(VIEC_FILE, None)
    try:
        os.replace(VIEC_FILE, VIEC_FILE.with_suffix(".json.xong"))
    except Exception:
        return
    if not isinstance(viec, list):
        log("Viec 1 lan: chay-1-lan.json sai dinh dang JSON -> bo qua (da doi ten thanh .xong)")
        return
    out_dir = HERE / "chan-doan"
    out_dir.mkdir(exist_ok=True)
    repo = Path(load_cfg()["repo"])
    for i, v in enumerate(viec[:6]):
        ten = str(v.get("file", "")) if isinstance(v, dict) else ""
        if ten not in VIEC_DUOC or not (HERE / ten).exists():
            log(f"Viec 1 lan: bo qua '{ten}' (khong nam trong danh sach cho phep)")
            continue
        args = [str(a) for a in (v.get("args") or [])][:6]
        log(f"Viec 1 lan: {ten} {' '.join(args)}")
        code, out = run_cmd([sys.executable, str(HERE / ten)] + args, repo, 10)
        try:
            (out_dir / f"viec-{i + 1}-{Path(ten).stem}.log").write_text(out, encoding="utf-8")
        except Exception:
            pass
        log(f"  -> xong (ma thoat {code})")


def main(argv: list[str]) -> int:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(errors="replace")
        except Exception:
            pass
    if argv[:1] == ["--tiktok-one"]:
        return tiktok_one(*argv[1:8])
    if argv[:1] == ["--tiktok-check"]:
        return tiktok_check(argv[1])
    if argv[:1] == ["--ig-whoami"]:
        return ig_whoami(argv[1])
    if argv[:1] == ["--ghim"]:
        return ghim_tai_khoan()
    if not giu_khoa():
        print("Máy đang chạy dở 1 lượt đăng → bỏ qua lượt này. Bảng theo dõi sẽ tự cập nhật trong khoảng 10 phút.")
        return 0
    try:
        run_once(post_enabled="--chi-ghi" not in argv, force_check="--kiem-tra" in argv)
        if "--chi-ghi" not in argv:
            chay_viec_cho()
    except SystemExit as e:
        bao_loi_he_thong(str(e.code))
        return 1
    except Exception:
        log("LOI HE THONG:\n" + traceback.format_exc())
        bao_loi_he_thong("Máy đăng gặp lỗi lạ, lượt này không chạy được. Nhờ Claude xem nhat-ky.log.")
        return 1
    finally:
        LOCK_FILE.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
