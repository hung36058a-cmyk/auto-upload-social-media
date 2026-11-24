# -*- coding: utf-8 -*-
"""
KIEM TRA DANG MXH - agent kiem tra DOC LAP (ban 1.1, 16/11/2026)
1.1: caption IG econlazypack duoc co dong nguon (chu kenh cho phep 16/11); .json con made_for_kids chi la GHI_CHU
     vi Apps Script da bo truong nay (VI PHAM khi ma Apps Script con selfDeclaredMadeForKids - agent kiem o buoc YouTube)
1.2: Content Credentials (C2PA) trong video: gom thanh 1 dong CAN_XEM moi lan kiem (ghi ai ky: Anthropic = Claude tu gan
     khi giao file). Agent KHONG go chu ky nguon goc nay. Noi dung goi C2PA khong tinh vao kiem ten cong cu (tieu chi 2).
1.3: chay MOI GIO (sau moi lan dang ~30-60 phut). Moi muc co "moi": true/false (so voi lan kiem truoc, luu "da_bao")
     de agent chi bao dien thoai khi co loi MOI. C2PA chi do Anthropic ky, khong co co AI -> GHI_CHU (chu kenh da biet).
     "tom_tat": bai moi / loi moi / video moi vao hang cho.
CHI DOC: khong dang, khong sua, khong xoa gi cua may dang. Chi ghi vao thu muc cua chinh no:
  00_Dung-chung/kiem-tra-mxh/  (bao-cao/, ban-da-kiem/, trang-thai-kiem.json)

Tieu chi cua chu kenh (16/11/2026):
  K  Dang DUNG kenh
  1  Khong tu gan nhan AI (ke ca metadata C2PA/IPTC trong file video lam mang xa hoi tu gan nhan)
  2  Caption / mo ta / tag / binh luan ghim / metadata KHONG nhac mo hinh AI, web AI, nguon anh (unsplash...)
  3  Muc "danh cho tre em / duoi 18" de TRONG, khong dung vao
  4  Location de TRONG
  5  Bao moi viec lam trai skill hoac khong co trong skill
  6  Khong them gi vao caption/mo ta ngoai mau cua skill

Cach chay:
  python3 kiem_tra_mxh.py                          tu tim thu muc 01_YouTube, kiem tu lan truoc (lan dau: 48 gio)
  python3 kiem_tra_mxh.py --goc <01_YouTube> --tu 2026-11-15T21:00:00+08:00 [--khong-luu]
  python3 kiem_tra_mxh.py --chu <file|thu muc> --kenh tso|cq|econ|vietwan   chi kiem chu (.json YouTube / .txt)
  python3 kiem_tra_mxh.py --mp4 <file.mp4>         chi kiem metadata 1 video
Ket qua: JSON ra man hinh (+ ghi kiem-tra-mxh/bao-cao/<ngay_gio>.json khi kiem laptop).
Muc: VI_PHAM (sai chac) | CAN_XEM (agent/nguoi phai xem lai) | GHI_CHU (thong tin).
"""
from __future__ import annotations

import datetime as dt
import difflib
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

PHIEN_BAN = "1.3"
TZ = dt.timezone(dt.timedelta(hours=8))

# ------------------------------------------------------------------ CHUAN (sua khi chu kenh doi co chu y)
# Nguon: project doc claude/he-thong-dang-mxh.md muc "LICH DANG CHUAN" (15/11/2026)
TAI_KHOAN_CHUAN = {
    "tiktok_vietwan": {"kenh": "vietwan",
                       "thu_muc": "02_Vietwan/dang-mxh/tiktok_vietwan", "dang_ngay": True, "cach_phut": 30},
    "tiktok_econlazypack": {"kenh": "econ",
                            "thu_muc": "04_econlazypack/dang-mxh/tiktok_econlazypack", "khung_gio": ["12:00", "20:00"]},
    "instagram_ecolazypack": {"kenh": "econ",
                              "thu_muc": "04_econlazypack/dang-mxh/instagram_ecolazypack", "khung_gio": ["12:00", "20:00"]},
}
# Ten @ chuan nam o file rieng tai-khoan-chuan.json (KHONG len GitHub): {"tiktok_vietwan": "<handle>", ...}
try:
    _TEN_CHUAN = json.loads((Path(__file__).with_name("tai-khoan-chuan.json")).read_text(encoding="utf-8"))
except (OSError, ValueError):
    _TEN_CHUAN = {}
for _ma, _c in TAI_KHOAN_CHUAN.items():
    _c["username"] = str(_TEN_CHUAN.get(_ma, "")).lstrip("@")
TAI_KHOAN_PHAI_TAT = {"youtube_econlazypack"}   # YouTube Short econlazypack di Drive + Apps Script, laptop TAT
CUA_SO_PHUT = 120                               # may dang bu toi da 120 phut sau khung gio

# File may dang ma agent theo doi (doi noi dung -> so ban truoc, bao phan doi)
FILE_THEO_DOI = [
    "00_Dung-chung/dang-mxh/dang_mxh.py",
    "00_Dung-chung/dang-mxh/cau-hinh.json",
    "00_Dung-chung/social-auto-upload/uploader/tk_uploader/main_chrome.py",
    "00_Dung-chung/social-auto-upload/uploader/meta_uploader/insgraph_uploader/main.py",
    "00_Dung-chung/social-auto-upload/sau_commands/instagram.py",
]

# ------------------------------------------------------------------ TU CAM (tieu chi 2)
_I = re.I
TU_CAM = [  # (regex, ten) - khop la VI_PHAM
    (r"(?<![\w.])[a-z0-9][a-z0-9-]*\.ai\b", "tên miền .ai"),
    (r"\bchat\s?gpt\b|\bgpt[-\s]?\d|\bopen\s?ai\b", "ChatGPT/OpenAI"),
    (r"\bclaude\b|\banthropic\b", "Claude"),
    (r"\bgemini\b|google\s?bard", "Gemini"),
    (r"\bcopilot\b", "Copilot"),
    (r"\bmidjourney\b", "Midjourney"),
    (r"\bdall[\s·-]?e\b", "DALL-E"),
    (r"\bstable\s?diffusion\b|\bsdxl\b", "Stable Diffusion"),
    (r"\bsora\b", "Sora"),
    (r"\bveo\s?\d(\.\d)?\b|\bgoogle\s?veo\b", "Veo"),
    (r"\bkling\b|可灵|可靈", "Kling"),
    (r"runway\s?ml\b|runway\s+gen", "Runway"),
    (r"\bpika\s?(labs|art)?\b|\bluma\s?(ai|labs|dream)\b|\bideogram\b|leonardo[\s.]?ai\b", "công cụ ảnh/video AI"),
    (r"nano\s?banana", "Nano Banana"),
    (r"\bimagen\s?\d?\b", "Imagen"),
    (r"google\s?flow|flow\.google|labs\.google", "Google Flow"),
    (r"eleven\s?labs", "ElevenLabs"),
    (r"\bvibi\b", "Vibi"),
    (r"\bfal\b", "fal"),
    (r"\bsuno\b|\budio\b", "nhạc AI"),
    (r"\bheygen\b|\bsynthesia\b|\bd-id\b", "avatar AI"),
    (r"hyper\s?frames", "HyperFrames"),
    (r"toon\s?flow", "Toonflow"),
    (r"notebook\s?lm|\bperplexity\b|\bgrok\b|deep\s?seek|\bqwen\b|\bkimi\b|豆包|文心一言|通义|通義|即梦|即夢|海螺AI", "AI khác"),
    (r"hugging\s?face|replicate\.com|\bcivitai\b", "kho mô hình AI"),
    (r"\bunsplash\b|\bpexels\b|\bpixabay\b|\bfreepik\b|\bshutterstock\b|getty\s?images|adobe\s?stock", "nguồn ảnh"),
    (r"\bai[\s-]?generated\b|\bgenerated\s+(by|with|using)\b|\bmade\s+(with|using)\b|\bcreated\s+(with|using)\b"
     r"|\bnarrated\s+by\b|\bvoiced?\s+by\b|\bvoice\s?over\s+by\b|\bimages?\s+by\b|\bphotos?\s+by\b", "ghi công công cụ/AI"),
    (r"AI\s?生成|AI\s?繪|AI\s?绘|AI\s?配音|AI\s?製作|AI\s?制作|AIGC|人工智慧生成|人工智能生成", "AI (chữ Trung)"),
    (r"tạo bằng AI|làm bằng AI|ảnh AI|giọng AI|video AI|bằng trí tuệ nhân tạo", "AI (chữ Việt)"),
]
TU_CAN_XEM = [  # khop la CAN_XEM (co the la nghia khac)
    (re.compile(r"(?<![A-Za-z0-9])A\.?I\.?(?![A-Za-z0-9])"), "chữ \"AI\" (có thể là chữ \"ai\" tiếng Việt viết hoa)"),
    (re.compile(r"人工智慧|人工智能|trí tuệ nhân tạo|artificial intelligence", _I), "nhắc tới AI"),
    (re.compile(r"\bflux\b", _I), "\"flux\" (tên công cụ Flux hay nghĩa thường?)"),
    (re.compile(r"\bcanva\b|\bcapcut\b", _I), "công cụ dựng có AI"),
]
TU_CAM_RE = [(re.compile(p, _I), t) for p, t in TU_CAM]

# Dau hieu nhan AI / metadata tao bang AI trong file video
C2PA_UUID = bytes.fromhex("d8fec3d61b0e483c92975828877ec481")
DAU_AI_FILE = [b"c2pa", b"jumb", b"jumd", b"trainedAlgorithmicMedia", b"compositeSynthetic",
               b"algorithmicMedia", b"DigitalSourceType", b"contentcredentials", b"SynthID"]

# Ma may dang: dong nao dung toi nhan AI / tre em / location
MA_CAM = [
    ("1", re.compile(r"ai[-_ ]?generated|aigc|ai[-_ ]?label|ai[-_ ]?info|content[-_ ]?disclos|disclose|synthetic|\bis_ai\b", _I),
     "đụng tới nhãn AI"),
    ("3", re.compile(r"made[-_ ]?for[-_ ]?kids|self[-_ ]?declared|\baudience\b|age[-_ ]?restrict|18\+|\bmature\b|\bkids?\b|trẻ em|兒童|儿童", _I),
     "đụng tới mục trẻ em / 18+"),
    ("4", re.compile(r"\blocation\b|recording[-_ ]?details|\bpoi\b|\bgeo(tag|location)?\b|vị trí|位置|地點|地点", _I),
     "đụng tới location"),
]
HOP_THOAI_NGUY = re.compile(r"\bAI\b|AI-generated|AIGC|\blabel|disclos|synthetic|location|位置|地點|audience|18\+|kids|兒童|nhãn", _I)
NUT_AN_TOAN = {"cancel", "not now", "later", "maybe later", "skip", "no thanks", "close", "got it", "ok", "post now",
               "post anyway", "continue", "confirm", "done", "取消", "稍後再說", "略過", "知道了", "hủy", "để sau", "bỏ qua",
               "đã hiểu", "立即發佈", "發佈", "繼續", "確定", "đăng ngay", "tiếp tục"}

NUT_TU_CHOI = {"cancel", "not now", "later", "maybe later", "skip", "no thanks", "close", "取消", "稍後再說", "略過",
               "hủy", "để sau", "bỏ qua"}

DONG_NGUON = re.compile(r"(資料|资料)?[來来]源\s*[:：]|^\s*[（(].*[來来]源")

VI_CHU = set("ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹáàãéèíìóòõúùýđ")
GIAN_THE = set("这们为说时会来发经济学业对过还没点让从开关头钱买卖东边问题间应该现实际产书长门车马见觉认语读写听话谁请给")


# ------------------------------------------------------------------ tien ich
def bay_gio() -> dt.datetime:
    return dt.datetime.now(TZ).replace(microsecond=0)


def doc_json(p: Path, mac_dinh=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:
        return mac_dinh


def doc_chu(p: Path) -> str:
    try:
        return Path(p).read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""


def md5(p: Path) -> str:
    try:
        return hashlib.md5(Path(p).read_bytes()).hexdigest()
    except Exception:
        return ""


def gio(s) -> dt.datetime | None:
    try:
        t = dt.datetime.fromisoformat(str(s))
        return t if t.tzinfo else t.replace(tzinfo=TZ)
    except Exception:
        return None


class KetQua:
    def __init__(self):
        self.ds = []

    def them(self, muc, tieu_chi, noi, chi_tiet, **them):
        d = {"muc": muc, "tieu_chi": str(tieu_chi), "noi": str(noi), "chi_tiet": chi_tiet}
        d.update({k: v for k, v in them.items() if v not in (None, "", [])})
        if d not in self.ds:
            self.ds.append(d)

    def dem(self):
        out = {"VI_PHAM": 0, "CAN_XEM": 0, "GHI_CHU": 0}
        for d in self.ds:
            out[d["muc"]] = out.get(d["muc"], 0) + 1
        return out


# ------------------------------------------------------------------ kiem chu (tieu chi 2)
def chuan_hoa(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")


def kiem_tu_cam(kq: KetQua, chu: str, noi: str, truong: str = "caption") -> None:
    s = chuan_hoa(chu)
    cam = [(ten, m.group(0)) for rx, ten in TU_CAM_RE for m in rx.finditer(s)]
    if cam:
        kq.them("VI_PHAM", 2, noi, f"{truong} có từ cấm: " + "; ".join(f"{t} (\"{g}\")" for t, g in cam),
                trich=s[:300].replace("\n", " ⏎ "))
    for rx, ten in TU_CAN_XEM:
        for m in rx.finditer(s):
            kq.them("CAN_XEM", 2, noi, f"{truong} có {ten}: \"{doan(s, m)}\"")


def doan(s: str, m, rong: int = 25) -> str:
    a, b = max(0, m.start() - rong), min(len(s), m.end() + rong)
    return s[a:b].replace("\n", " ⏎ ")


def dem_ngon_ngu(s: str) -> tuple[int, int, int]:
    s2 = chuan_hoa(s).lower()
    vi = sum(1 for c in s2 if c in VI_CHU)
    cjk = sum(1 for c in s2 if "\u4e00" <= c <= "\u9fff")
    gian = sum(1 for c in s2 if c in GIAN_THE)
    return vi, cjk, gian


# ------------------------------------------------------------------ kiem caption theo mau skill (K, 5, 6)
def kiem_caption(kq: KetQua, ma_tk: str, kenh: str, mang: str, ten_video: str, chu: str, noi: str,
                 short_cat: bool = False) -> None:
    kiem_tu_cam(kq, chu, noi)
    dong = [d.strip() for d in chu.replace("\r", "").split("\n") if d.strip()]
    if not dong:
        kq.them("CAN_XEM", 5, noi, "caption trống")
        return
    vi, cjk, gian = dem_ngon_ngu(chu)
    tags = re.findall(r"#[^\s#]+", chu)
    tag_low = [t.lower() for t in tags]
    # --- dung kenh theo noi dung
    if kenh == "vietwan":
        if not ten_video.upper().startswith("VIETWAN_"):
            kq.them("CAN_XEM", "K", noi, "video trong hàng chờ Vietwan nhưng tên file không bắt đầu bằng VIETWAN_")
        if vi < 3 or cjk > vi * 2:
            kq.them("VI_PHAM", "K", noi, f"caption không phải tiếng Việt (chữ Việt {vi}, chữ Hán {cjk}) → có thể là video kênh khác")
        if any(t in tag_low for t in ("#經濟懶人包",)):
            kq.them("VI_PHAM", "K", noi, "caption có hashtag kênh econlazypack trong hàng chờ Vietwan")
    elif kenh == "econ":
        if ten_video.upper().startswith("VIETWAN_"):
            kq.them("VI_PHAM", "K", noi, "video tên VIETWAN_ nằm trong hàng chờ econlazypack")
        if cjk < 10 or vi > 0:
            kq.them("VI_PHAM", "K", noi, f"caption không phải tiếng Trung phồn thể (chữ Hán {cjk}, chữ Việt {vi}) → có thể là video kênh khác")
        if gian >= 2:
            kq.them("CAN_XEM", 5, noi, f"caption có {gian} chữ giản thể (kênh dùng phồn thể)")
        if "#vietwan" in tag_low:
            kq.them("VI_PHAM", "K", noi, "caption có #vietwan trong hàng chờ econlazypack")
    # --- mau skill
    co_url = re.search(r"https?://|www\.|\b[a-z0-9-]+\.(com|tw|net|org|io|me|ly|gl)\b", chu, _I)
    dong_tag = [d for d in dong if d.startswith("#")]
    dong_noi_dung = [d for d in dong if not d.startswith("#")]
    if kenh == "vietwan":
        bat_buoc = ["#tindailoan", "#vietwan", "#nguoivietodailoan"]
        thieu = [t for t in bat_buoc if t not in tag_low]
        if thieu:
            kq.them("CAN_XEM", 5, noi, f"thiếu hashtag cố định của skill: {' '.join(thieu)}")
        them_tag = len([t for t in tag_low if t not in bat_buoc])
        if not 2 <= them_tag <= 3 and not (them_tag == 3 and "#duhocdailoan" in tag_low):
            kq.them("CAN_XEM", 6, noi, f"skill: 2–3 hashtag chủ đề (tin du học thêm #duhocdailoan) — đang có {them_tag}")
        nguon = [i for i, d in enumerate(dong_noi_dung) if d.lower().startswith("nguồn")]
        if not nguon:
            kq.them("CAN_XEM", 5, noi, "thiếu dòng \"Nguồn: <báo> (dd/mm/yyyy)\" theo skill")
        truoc = dong_noi_dung[:nguon[0]] if nguon else dong_noi_dung
        sau = dong_noi_dung[nguon[0] + 1:] if nguon else []
        if len(truoc) > 2:
            kq.them("CAN_XEM", 6, noi, f"skill cho tối đa 2 dòng nội dung, đang có {len(truoc)}: \"{truoc[-1][:60]}\"")
        for d in sau:
            kq.them("CAN_XEM", 6, noi, f"dòng ngoài mẫu skill: \"{d[:80]}\"")
        if any("?" in d for d in truoc):
            kq.them("CAN_XEM", 5, noi, "skill cấm câu hỏi trong caption TikTok Vietwan (có dấu ?)")
        if re.search(r"youtube|youtu\.be", chu, _I) or co_url:
            kq.them("CAN_XEM", 6, noi, "caption có link / dẫn sang YouTube (skill: không dẫn sang YouTube)")
    elif kenh == "econ":
        if "#經濟懶人包" not in tags:
            kq.them("CAN_XEM", 5, noi, "thiếu hashtag cố định #經濟懶人包")
        cta = "完整影片👉 YouTube 搜尋 經濟懶人包"
        cho_phep = 1
        if mang == "instagram":
            cho_phep = 2   # dong 1 = tieu de, dong 2 = mo ta
        if short_cat:
            if not any(chuan_hoa(cta) == chuan_hoa(d) for d in dong_noi_dung):
                kq.them("CAN_XEM", 5, noi, f"short cắt thiếu dòng \"{cta}\" theo skill kinhte-long")
            dong_noi_dung = [d for d in dong_noi_dung if chuan_hoa(d) != chuan_hoa(cta)]
        else:
            for t in ("#創業", "#副業"):
                if t not in tags:
                    kq.them("CAN_XEM", 5, noi, f"thiếu hashtag cố định {t} (skill kinhte-short)")
            them_tag = len([t for t in tags if t not in ("#經濟懶人包", "#創業", "#副業")])
            if not 2 <= them_tag <= 3:
                kq.them("CAN_XEM", 6, noi, f"skill: 2–3 hashtag chủ đề — đang có {them_tag}")
        if mang == "instagram":  # chu kenh 16/11: caption IG co dong nguon thi khong sao
            dong_noi_dung = [d for d in dong_noi_dung if not DONG_NGUON.search(d)]
        for d in dong_noi_dung[cho_phep:]:
            kq.them("CAN_XEM", 6, noi, f"dòng ngoài mẫu skill: \"{d[:80]}\"")
        if co_url:
            kq.them("CAN_XEM", 6, noi, "caption có link (skill: không link bán hàng trừ khi chủ kênh đưa)")
    if len(dong_tag) > 1:
        kq.them("GHI_CHU", 6, noi, f"hashtag nằm trên {len(dong_tag)} dòng")


# ------------------------------------------------------------------ metadata video (tieu chi 1, 2)
def kiem_mp4(kq: KetQua, p: Path, noi: str | None = None) -> None:
    noi = noi or str(p)
    try:
        f = open(p, "rb")
    except Exception as e:
        kq.them("GHI_CHU", 1, noi, f"không mở được video để kiểm metadata ({type(e).__name__})")
        return
    with f:
        size = os.fstat(f.fileno()).st_size
        pos, hop, chu_meta = 0, [], b""
        while pos + 8 <= size and len(hop) < 200:
            f.seek(pos)
            h = f.read(8)
            if len(h) < 8:
                break
            n, kieu = int.from_bytes(h[:4], "big"), h[4:8]
            dau = 8
            if n == 1:
                n = int.from_bytes(f.read(8), "big")
                dau = 16
            elif n == 0:
                n = size - pos
            if n < dau:
                break
            ten = kieu.decode("latin-1")
            hop.append(ten)
            if ten != "mdat" and ten != "free":
                doc = min(n - dau, 16 * 1024 * 1024)
                data = f.read(doc)
                if ten == "uuid" and data[:16] == C2PA_UUID:
                    ky = "Anthropic (Claude tự gắn khi giao file)" if b"Anthropic" in data else "nguồn khác"
                    ai = any(x in data for x in (b"trainedAlgorithmicMedia", b"compositeSynthetic", b"algorithmicMedia"))
                    kq.them("GHI_CHU", 1, noi, f"video có Content Credentials (C2PA) — ký bởi {ky}"
                                               + ("; có cờ 'tạo bằng AI'" if ai else ""), c2pa=ky, c2pa_ai=ai)
                    data = b""  # goi C2PA: khong tinh vao kiem ten cong cu
                chu_meta += data
            pos += n
        if not hop or hop[0] not in ("ftyp", "free", "wide", "moov", "mdat", "skip"):
            kq.them("GHI_CHU", 1, noi, "không đọc được cấu trúc mp4 (bỏ qua kiểm metadata)")
            return
        low = chu_meta.lower()
        dau = [d.decode() for d in DAU_AI_FILE if d.lower() in low]
        if dau:
            kq.them("VI_PHAM", 1, noi, f"metadata video có dấu hiệu nội dung AI ({', '.join(dau)}) → mạng xã hội có thể TỰ GẮN nhãn AI")
        chuoi = " | ".join(x.decode("latin-1") for x in re.findall(rb"[\x20-\x7e]{5,}", chu_meta)[:4000])
        cong_cu = []
        for rx, ten in TU_CAM_RE:
            m = rx.search(chuoi)
            if m:
                cong_cu.append(f"{ten}: \"{doan(chuoi, m, 20)}\"")
        if cong_cu:
            kq.them("VI_PHAM", 2, noi, "metadata video có tên công cụ/ghi công: " + "; ".join(cong_cu))


# ------------------------------------------------------------------ kiem .json YouTube (tieu chi 1-4, 6)
def kiem_json_youtube(kq: KetQua, p: Path, kenh: str) -> None:
    noi = p.name
    m = doc_json(p)
    if not isinstance(m, dict):
        kq.them("CAN_XEM", 5, noi, "file .json đọc không được")
        return
    for k in ("made_for_kids", "madeForKids", "self_declared_made_for_kids", "selfDeclaredMadeForKids"):
        if k in m:
            kq.them("GHI_CHU", 3, noi, f".json còn ghi \"{k}\": {json.dumps(m[k])} — Apps Script đã bỏ trường này (16/11); "
                                       "chỉ là vi phạm nếu mã Apps Script còn selfDeclaredMadeForKids")
    for k in ("contains_synthetic_media", "containsSyntheticMedia", "altered_content", "ai_label"):
        if m.get(k) is True:
            kq.them("VI_PHAM", 1, noi, f".json có \"{k}\": true → YouTube gắn nhãn nội dung AI/chỉnh sửa")
        elif k in m:
            kq.them("GHI_CHU", 1, noi, f".json có \"{k}\": {json.dumps(m[k])} (không gắn nhãn AI)")
    for k in m:
        if re.search(r"location|recording|geo|lat$|lng$|longitude|latitude", k, _I):
            kq.them("VI_PHAM", 4, noi, f".json có trường vị trí \"{k}\"")
    chu = []
    for k in ("title", "description", "pin_comment", "tiktok", "caption", "hook"):
        if isinstance(m.get(k), str):
            kiem_tu_cam(kq, m[k], noi, k)
            chu.append(m[k])
    if isinstance(m.get("tags"), list):
        kiem_tu_cam(kq, ", ".join(map(str, m["tags"])), noi, "tags")
    vi, cjk, gian = dem_ngon_ngu(" ".join(str(m.get(k, "")) for k in ("title", "description")))
    if kenh == "vietwan" and vi < 3:
        kq.them("VI_PHAM", "K", noi, "tiêu đề/mô tả không phải tiếng Việt → có thể nhầm kênh")
    if kenh == "econ" and (cjk < 5 or vi > 0):
        kq.them("VI_PHAM", "K", noi, "tiêu đề/mô tả không phải tiếng Trung phồn thể → có thể nhầm kênh")
    if kenh == "econ" and gian >= 2:
        kq.them("CAN_XEM", 5, noi, f"tiêu đề/mô tả có {gian} chữ giản thể")
    if kenh == "tso" and (cjk > 0 or vi > 0):
        kq.them("VI_PHAM", "K", noi, "The Still Observer là kênh tiếng Anh nhưng .json có chữ Việt/Hán")
    if kenh == "cq":
        if vi > 0:
            kq.them("CAN_XEM", 5, noi, "Chinese Quest: skill cấm tiếng Việt trong tiêu đề/mô tả")
        n = len(re.findall(r"#[^\s#]+", str(m.get("description", ""))))
        if n > 15:
            kq.them("CAN_XEM", 5, noi, f"Chinese Quest: mô tả có {n} hashtag (skill: đúng 15, quá 15 YouTube bỏ hết)")
    if len(str(m.get("title", ""))) > 100:
        kq.them("CAN_XEM", 5, noi, "tiêu đề dài hơn 100 ký tự")
    if kenh == "vietwan" and isinstance(m.get("tiktok"), str):
        kiem_caption(kq, "tiktok_vietwan", "vietwan", "tiktok", noi, m["tiktok"], noi + " [tiktok]")


# ------------------------------------------------------------------ kiem laptop
def tim_goc(goc: str | None) -> Path:
    ung = [goc] if goc else []
    ung += [os.environ.get("KTM_GOC", "")]
    ung += sorted(glob.glob(os.path.join(os.path.expanduser("~"), "mnt", "*")))
    ung += ["E:/01_YouTube", "/mnt/e/01_YouTube"]
    for u in ung:
        if u and (Path(u) / "00_Dung-chung" / "dang-mxh" / "cau-hinh.json").exists():
            return Path(u)
        if u and (Path(u) / "01_YouTube" / "00_Dung-chung" / "dang-mxh" / "cau-hinh.json").exists():
            return Path(u) / "01_YouTube"
    raise SystemExit("KHONG_TIM_THAY: không thấy thư mục 01_YouTube (cần 00_Dung-chung/dang-mxh/cau-hinh.json)")


def doi_duong_dan(goc: Path, p: str) -> Path:
    """Duong dan Windows trong cau-hinh.json (E:/01_YouTube/...) -> duong dan that tren may dang chay."""
    s = str(p).replace("\\", "/")
    m = re.match(r"^[A-Za-z]:/01_YouTube/?(.*)$", s)
    return goc / m.group(1) if m else Path(s)


def kiem_cau_hinh(kq: KetQua, goc: Path, cfg: dict) -> dict:
    noi = "dang-mxh/cau-hinh.json"
    tk = {}
    for a in cfg.get("tai_khoan", []):
        if not isinstance(a, dict):
            continue
        ma = f"{a.get('mang')}_{a.get('cookie')}"
        tk[ma] = a
        bat = a.get("bat", True)
        if ma in TAI_KHOAN_PHAI_TAT:
            if bat:
                kq.them("VI_PHAM", 5, noi, f"{ma} đang BẬT — chuẩn: tắt (YouTube econlazypack đi Drive + Apps Script)")
            continue
        c = TAI_KHOAN_CHUAN.get(ma)
        if not c:
            if bat:
                kq.them("CAN_XEM", 5, noi, f"tài khoản mới {ma} (@{a.get('username')}) chưa có trong chuẩn của agent kiểm tra")
            continue
        if not bat:
            kq.them("GHI_CHU", 5, noi, f"{ma} đang tạm dừng (bat=false)")
        u = str(a.get("username") or "").lstrip("@").lower()
        if not u:
            kq.them("VI_PHAM", "K", noi, f"{ma} chưa ghim tên @ → máy có thể đăng nhầm kênh")
        elif not c["username"]:
            kq.them("CAN_XEM", "K", noi, f"{ma}: thiếu tên @ chuẩn trong kiem-tra-mxh/tai-khoan-chuan.json → chưa kiểm đúng kênh")
        elif u != c["username"].lower():
            kq.them("VI_PHAM", "K", noi, f"{ma} ghim @{u}, chuẩn là @{c['username']}")
        tm = str(a.get("thu_muc") or "").replace("\\", "/")
        if not tm.rstrip("/").lower().endswith(c["thu_muc"].lower()):
            kq.them("VI_PHAM", "K", noi, f"{ma} dùng thư mục {tm}, chuẩn là E:/01_YouTube/{c['thu_muc']}")
        if c.get("dang_ngay"):
            if not a.get("dang_ngay") or a.get("khung_gio"):
                kq.them("VI_PHAM", 5, noi, f"{ma}: chuẩn là đăng ngay (Lập tức), cấu hình đang khác")
            if int(a.get("cach_toi_thieu_phut") or 0) < c.get("cach_phut", 0):
                kq.them("VI_PHAM", 5, noi, f"{ma}: khoảng cách tối thiểu {a.get('cach_toi_thieu_phut')} phút < chuẩn {c['cach_phut']}")
        else:
            if sorted(a.get("khung_gio") or []) != sorted(c["khung_gio"]) or a.get("dang_ngay"):
                kq.them("VI_PHAM", 5, noi, f"{ma}: khung giờ {a.get('khung_gio')} khác lịch chuẩn {c['khung_gio']}")
    for ma in TAI_KHOAN_CHUAN:
        if ma not in tk:
            kq.them("CAN_XEM", 5, noi, f"không thấy tài khoản {ma} trong cấu hình")
    return tk


def kiem_so_ghi(kq: KetQua, data: dict, tu: dt.datetime) -> list:
    """du-lieu.json: dang dung tai khoan, dung gio, khong dang trung."""
    noi = "dang-mxh/du-lieu.json"
    for ma, st in (data.get("dang_nhap") or {}).items():
        c = TAI_KHOAN_CHUAN.get(ma)
        that = str(st.get("tai_khoan_that") or "").lower()
        if c and that and that != c["username"].lower():
            kq.them("VI_PHAM", "K", noi, f"{ma} đang đăng nhập @{that}, chuẩn là @{c['username']}")
    moi = []
    for r in data.get("lich_su") or []:
        t = gio(r.get("luc"))
        if t and t >= tu:
            moi.append(r)
    da_ok = {}
    for r in sorted(data.get("lich_su") or [], key=lambda x: str(x.get("luc"))):
        if r.get("kq") == "ok":
            da_ok.setdefault((r.get("tk"), r.get("file")), []).append(r)
    for r in moi:
        ma, c = r.get("tk"), TAI_KHOAN_CHUAN.get(r.get("tk"))
        n = f"{ma} · {r.get('file')}"
        if r.get("kq") != "ok":
            if r.get("kq") == "loi" and re.search(r"NHAM KENH|SAI_TAI_KHOAN|sai kenh", str(r.get("loi")), _I):
                kq.them("VI_PHAM", "K", n, f"máy ghi: {str(r.get('loi'))[:160]}")
            continue
        if ma in TAI_KHOAN_PHAI_TAT:
            kq.them("VI_PHAM", 5, n, f"{ma} đã tắt mà vẫn đăng bài")
        if c:
            that = str(r.get("tai_khoan") or "").lower()
            if not that:
                kq.them("CAN_XEM", "K", n, "bài ghi \"đã đăng\" nhưng không ghi tài khoản thật")
            elif that != c["username"].lower():
                kq.them("VI_PHAM", "K", n, f"ĐĂNG NHẦM KÊNH: lên @{that}, chuẩn là @{c['username']}", link=r.get("link"))
            link = str(r.get("link") or "")
            if ma.startswith("tiktok") and link and f"/@{c['username'].lower()}/" not in link.lower():
                kq.them("VI_PHAM", "K", n, f"link bài không thuộc @{c['username']}", link=link)
            if not link:
                kq.them("CAN_XEM", 5, n, "ghi đã đăng nhưng không có link bài (luật máy: phải có bằng chứng)")
            # dung gio
            khung = str(r.get("khung") or "")
            t = gio(r.get("luc"))
            if c.get("khung_gio") and " hen " not in khung:
                hm = khung[11:16]
                if hm and hm not in c["khung_gio"]:
                    kq.them("VI_PHAM", 5, n, f"đăng ở khung {hm}, lịch chuẩn chỉ {', '.join(c['khung_gio'])}")
                kt = gio(khung[:16].replace(" ", "T") + ":00") if len(khung) >= 16 else None
                if kt and t and not (kt <= t <= kt + dt.timedelta(minutes=CUA_SO_PHUT)):
                    kq.them("VI_PHAM", 5, n, f"giờ đăng {t:%H:%M} lệch khung {kt:%H:%M} quá {CUA_SO_PHUT} phút")
        bo = da_ok.get((ma, r.get("file")), [])
        if len(bo) > 1:
            kq.them("VI_PHAM", 5, n, f"cùng 1 video ghi \"đã đăng\" {len(bo)} lần trên {ma} (đăng trùng?)",
                    link=" ; ".join(str(x.get("link")) for x in bo))
        if r.get("canh_bao"):
            kq.them("VI_PHAM", 5, n, str(r["canh_bao"])[:200])
    # Vietwan: cach nhau >= 30 phut
    for ma, c in TAI_KHOAN_CHUAN.items():
        if not c.get("dang_ngay"):
            continue
        ts = sorted(gio(r["luc"]) for r in data.get("lich_su") or [] if r.get("tk") == ma and r.get("kq") == "ok" and gio(r.get("luc")))
        for a, b in zip(ts, ts[1:]):
            if b >= tu and (b - a) < dt.timedelta(minutes=c["cach_phut"]):
                kq.them("VI_PHAM", 5, ma, f"2 bài cách nhau {int((b - a).total_seconds() // 60)} phút (< {c['cach_phut']})")
    return moi


def ten_goc(ten: str) -> str:
    """'2026-11-16_1209_2026-11-16_02_nomad-list.mp4' -> '2026-11-16_02_nomad-list' (bo tien to ngay gio may them)."""
    s = Path(ten).stem
    for _ in range(2):
        s2 = re.sub(r"^\d{4}-\d{2}-\d{2}_\d{4}_", "", s)
        if s2 == s:
            break
        s = s2
    return re.sub(r"\.gio$", "", s)


def kiem_hang_cho(kq: KetQua, goc: Path, tk: dict, tu: dt.datetime, kiem_video: bool) -> dict:
    thong_ke = {}
    for ma, a in tk.items():
        thu_muc = doi_duong_dan(goc, a.get("thu_muc", ""))
        c = TAI_KHOAN_CHUAN.get(ma)
        cho = thu_muc / "cho-dang"
        if ma in TAI_KHOAN_PHAI_TAT:
            if cho.exists():
                vids = [p.name for p in cho.iterdir() if p.suffix.lower() in (".mp4", ".mov")]
                if vids:
                    kq.them("CAN_XEM", 5, f"{ma}/cho-dang", f"{len(vids)} video bị bỏ vào hàng chờ ĐÃ TẮT (skill nào đó còn dùng đường cũ?): {', '.join(vids[:3])}")
            continue
        if not c:
            continue
        if not thu_muc.exists():
            kq.them("CAN_XEM", 5, ma, f"không thấy thư mục hàng chờ {a.get('thu_muc')}")
            continue
        tk_dem = {"cho": 0, "cho_moi": 0, "da_dang_moi": 0}
        da_dang_goc = set()
        dd = thu_muc / "da-dang"
        ds_da = sorted(dd.iterdir()) if dd.exists() else []
        for p in ds_da:
            if p.suffix.lower() in (".mp4", ".mov"):
                da_dang_goc.add(ten_goc(p.name))
        # cho-dang: kiem TRUOC khi may dang
        ds_cho = sorted(cho.iterdir()) if cho.exists() else []
        for p in ds_cho:
            if p.suffix.lower() not in (".mp4", ".mov"):
                continue
            tk_dem["cho"] += 1
            if dt.datetime.fromtimestamp(p.stat().st_mtime, TZ) >= tu:
                tk_dem["cho_moi"] += 1
            txt = p.with_suffix(".txt")
            noi = f"{ma}/cho-dang/{p.name}"
            if not txt.exists():
                kq.them("CAN_XEM", 5, noi, "video chưa có file caption .txt")
            else:
                kiem_caption(kq, ma, c["kenh"], ma.split("_")[0], p.name, doc_chu(txt), noi,
                             short_cat=p.with_suffix(".gio.txt").exists() or "_short" in p.stem.lower())
            if ten_goc(p.name) in da_dang_goc:
                kq.them("VI_PHAM", 5, noi, "video này đã có trong da-dang → sắp ĐĂNG LẠI (skill cấm đăng lại video đã đăng)")
            if kiem_video:
                kiem_mp4(kq, p, noi)
        for p in ds_cho:
            if p.suffix.lower() == ".txt" and not p.name.endswith(".gio.txt") and not p.with_suffix(".mp4").exists() \
                    and not p.with_suffix(".mov").exists() and not p.name.endswith(".loi.txt"):
                kq.them("GHI_CHU", 5, f"{ma}/cho-dang/{p.name}", "caption không có video đi kèm")
        # da-dang moi (trong cua so kiem)
        for p in ds_da:
            if p.suffix.lower() not in (".mp4", ".mov"):
                continue
            m = re.match(r"^(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})_", p.name)
            t = gio(f"{m.group(1)}T{m.group(2)}:{m.group(3)}:00") if m else None
            if t is None:
                t = dt.datetime.fromtimestamp(p.stat().st_mtime, TZ)
            if t < tu:
                continue
            tk_dem["da_dang_moi"] += 1
            noi = f"{ma}/da-dang/{p.name}"
            txt = p.with_suffix(".txt")
            if txt.exists():
                kiem_caption(kq, ma, c["kenh"], ma.split("_")[0], ten_goc(p.name) + p.suffix, doc_chu(txt), noi,
                             short_cat=p.with_suffix(".gio.txt").exists() or "_short" in p.stem.lower())
            else:
                kq.them("CAN_XEM", 5, noi, "bài đã đăng nhưng không còn file caption để đối chiếu")
            if kiem_video:
                kiem_mp4(kq, p, noi)
        thong_ke[ma] = tk_dem
    return thong_ke


def kiem_nhat_ky_tiktok(kq: KetQua, goc: Path, tu: dt.datetime) -> None:
    p = goc / "00_Dung-chung/social-auto-upload/logs/tiktok.log"
    if not p.exists():
        return
    with open(p, "rb") as f:
        f.seek(max(0, p.stat().st_size - 600_000))
        dong = f.read().decode("utf-8", "replace").splitlines()
    for i, d in enumerate(dong):
        m = re.match(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})", d)
        if not m:
            continue
        t = gio(f"{m.group(1)}T{m.group(2)}")
        if not t or t < tu:
            continue
        if "hop thoai" in d and HOP_THOAI_NGUY.search(d.split("hop thoai", 1)[1]):
            sau = next((x for x in dong[i + 1:i + 4] if "da bam" in x), "")
            nut = re.search(r"da bam '([^']+)'", sau)
            dong_y = bool(nut) and nut.group(1).strip().lower() not in NUT_TU_CHOI
            kq.them("VI_PHAM" if dong_y else "CAN_XEM", 1, f"tiktok.log {m.group(1)} {m.group(2)}",
                    f"TikTok hiện hộp thoại có thể về nhãn AI/location/độ tuổi: \"{d.split('hop thoai', 1)[1][:200].strip(' :')}\""
                    + (f" → máy bấm '{nut.group(1)}'" + (" (ĐỒNG Ý — có thể đã gắn nhãn/đổi cài đặt)" if dong_y else "") if nut else ""))
        b = re.search(r"da bam '([^']+)'", d)
        if b and b.group(1).strip().lower() not in NUT_AN_TOAN:
            kq.them("CAN_XEM", 5, f"tiktok.log {m.group(1)} {m.group(2)}", f"máy bấm nút lạ trên TikTok: '{b.group(1)}'")
        if re.search(r"Turn on|Bật|開啟", d) and "da bam" in d:
            kq.them("VI_PHAM", 5, f"tiktok.log {m.group(1)} {m.group(2)}", "máy đã BẬT một cài đặt tài khoản TikTok (không có trong skill)")


def kiem_ma_may_dang(kq: KetQua, goc: Path, thu_muc_kt: Path, trang_thai: dict, luu: bool) -> None:
    """Ma may dang doi so voi lan kiem truoc -> bao dong them/bot; dong them co dung nhan AI/tre em/location -> bao rieng."""
    ban = thu_muc_kt / "ban-da-kiem"
    cu = trang_thai.get("md5") or {}
    moi = {}
    for rel in FILE_THEO_DOI:
        p = goc / rel
        if not p.exists():
            kq.them("CAN_XEM", 5, rel, "không thấy file (bị đổi tên/xóa?)")
            continue
        h = md5(p)
        moi[rel] = h
        luu_p = ban / rel.replace("/", "__")
        if rel not in cu or not luu_p.exists():
            kq.them("GHI_CHU", 5, rel, "lần đầu theo dõi file này: đã lưu bản gốc để so lần sau")
            them = doc_chu(p).splitlines()
            dong_moi = list(enumerate(them, 1))
        elif cu[rel] == h:
            continue
        else:
            truoc = doc_chu(luu_p).splitlines()
            sau = doc_chu(p).splitlines()
            diff = list(difflib.unified_diff(truoc, sau, "ban-truoc", "ban-moi", n=1, lineterm=""))
            dong_moi = []
            so = 0
            for d in diff:
                mh = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", d)
                if mh:
                    so = int(mh.group(1)) - 1
                    continue
                if d.startswith("+") and not d.startswith("+++"):
                    so += 1
                    dong_moi.append((so, d[1:]))
                elif not d.startswith("-"):
                    so += 1
            kq.them("CAN_XEM", 5, rel, f"file đã ĐỔI từ lần kiểm trước ({len(dong_moi)} dòng thêm/sửa) — xem có đúng việc chủ kênh yêu cầu không",
                    diff="\n".join(diff[:120]))
        for so, d in dong_moi:
            if rel.endswith(".json"):
                continue
            s = d.strip()
            if s.startswith("#") and not s.startswith("#!"):
                continue
            for tc, rx, ten in MA_CAM:
                if rx.search(d):
                    kq.them("CAN_XEM", tc, f"{rel}:{so}", f"dòng mã {ten}: \"{s[:140]}\"")
        if luu:
            luu_p.parent.mkdir(parents=True, exist_ok=True)
            luu_p.write_bytes(p.read_bytes())
    trang_thai["md5"] = {**cu, **moi}


def kiem_laptop(goc_arg: str | None, tu_arg: str | None, luu: bool, kiem_video: bool) -> dict:
    goc = tim_goc(goc_arg)
    kt = goc / "00_Dung-chung" / "kiem-tra-mxh"
    st_file = kt / "trang-thai-kiem.json"
    trang_thai = doc_json(st_file, {}) or {}
    luc = bay_gio()
    tu = gio(tu_arg) if tu_arg else gio(trang_thai.get("lan_cuoi")) or (luc - dt.timedelta(hours=48))
    kq = KetQua()
    cfg = doc_json(goc / "00_Dung-chung/dang-mxh/cau-hinh.json")
    if not isinstance(cfg, dict):
        raise SystemExit("KHONG_DOC_DUOC: cau-hinh.json")
    tk = kiem_cau_hinh(kq, goc, cfg)
    data = doc_json(goc / "00_Dung-chung/dang-mxh/du-lieu.json", {}) or {}
    moi = kiem_so_ghi(kq, data, tu)
    thong_ke = kiem_hang_cho(kq, goc, tk, tu, kiem_video)
    kiem_nhat_ky_tiktok(kq, goc, tu)
    kiem_ma_may_dang(kq, goc, kt, trang_thai, luu)
    c2 = [d for d in kq.ds if d.get("c2pa")]
    if c2:
        nguon = sorted({d["c2pa"] for d in c2})
        chi_anthropic = nguon == ["Anthropic (Claude tự gắn khi giao file)"] and not any(d.get("c2pa_ai") for d in c2)
        kq.them("GHI_CHU" if chi_anthropic else "CAN_XEM", 1, "C2PA", f"{len(c2)} video mang Content Credentials (C2PA) ký bởi {', '.join(nguon)}"
                + (f"; {sum(1 for d in c2 if d.get('c2pa_ai'))} có cờ 'tạo bằng AI'" if any(d.get('c2pa_ai') for d in c2) else "")
                + " — mạng xã hội có thể dựa vào đây để tự gắn nhãn AI. Agent chỉ báo, không gỡ chữ ký nguồn gốc.")
    tt = doc_json(goc / "00_Dung-chung/dang-mxh/trang-thai-mxh.json", {}) or {}
    khoa = lambda d: "|".join([d["muc"], d["tieu_chi"], d["noi"], d["chi_tiet"][:100]])
    da_bao = set(trang_thai.get("da_bao") or [])
    for d in kq.ds:
        d["moi"] = khoa(d) not in da_bao
    loi = [d for d in kq.ds if d["muc"] in ("VI_PHAM", "CAN_XEM")]
    tom_tat = {"bai_moi": sum(1 for r in moi if r.get("kq") == "ok"), "bai_loi_moi": sum(1 for r in moi if r.get("kq") != "ok"),
               "video_moi_vao_hang_cho": sum(v.get("cho_moi", 0) for v in thong_ke.values()),
               "loi_moi": sum(1 for d in loi if d["moi"]), "loi_van_con": sum(1 for d in loi if not d["moi"])}
    ket = {
        "phien_ban": PHIEN_BAN, "luc": luc.isoformat(), "tu": tu.isoformat(), "goc": str(goc),
        "may_dang_cap_nhat_luc": tt.get("cap_nhat_luc"),
        "bai_dang_trong_cua_so": [{k: r.get(k) for k in ("tk", "luc", "file", "kq", "tai_khoan", "link")} for r in moi],
        "tom_tat": tom_tat, "hang_cho": thong_ke, "dem": kq.dem(), "ket_qua": kq.ds,
    }
    if luu:
        (kt / "bao-cao").mkdir(parents=True, exist_ok=True)
        out = kt / "bao-cao" / f"{luc:%Y-%m-%d_%H%M}.json"
        out.write_text(json.dumps(ket, ensure_ascii=False, indent=2), encoding="utf-8")
        ket["file_bao_cao"] = str(out)
        trang_thai["lan_cuoi"] = luc.isoformat()
        trang_thai["da_bao"] = sorted(khoa(d) for d in loi)
        trang_thai["phien_ban"] = PHIEN_BAN
        st_file.write_text(json.dumps(trang_thai, ensure_ascii=False, indent=2), encoding="utf-8")
    return ket


def main(argv: list[str]) -> int:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    def lay(ten, mac_dinh=None):
        return argv[argv.index(ten) + 1] if ten in argv and argv.index(ten) + 1 < len(argv) else mac_dinh

    if "--chu" in argv:
        kq = KetQua()
        kenh = lay("--kenh", "")
        ds = []
        for p in [Path(lay("--chu"))]:
            ds += sorted(p.glob("*")) if p.is_dir() else [p]
        for p in ds:
            if p.suffix.lower() == ".json":
                kiem_json_youtube(kq, p, kenh)
            elif p.suffix.lower() == ".txt":
                kiem_caption(kq, "", kenh, lay("--mang", "tiktok"), p.name, doc_chu(p), p.name)
        print(json.dumps({"dem": kq.dem(), "ket_qua": kq.ds}, ensure_ascii=False, indent=1))
        return 0
    if "--phien-ban" in argv:
        print(PHIEN_BAN)
        return 0
    if "--tu-cam" in argv:
        # File chu chep tu Drive (read_file_content tra ve JSON bi escape kieu markdown: \_ \# \[ ...) -> go escape,
        # doc duoc JSON thi kiem nhu .json YouTube, khong thi quet tu cam + khoa cam tren chu tho.
        kq = KetQua()
        kenh = lay("--kenh", "")
        goc = Path(lay("--tu-cam"))
        for p in (sorted(goc.glob("*")) if goc.is_dir() else [goc]):
            raw = re.sub(r"\\([\\_#*\[\]()>~`|{}+.!-])", r"\1", doc_chu(p))
            try:
                m = json.loads(raw)
            except Exception:
                m = None
            if isinstance(m, dict):
                tmp = p.with_suffix(".giai.json")
                tmp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
                kiem_json_youtube(kq, tmp, kenh)
                for d in kq.ds:
                    d["noi"] = d["noi"].replace(tmp.name, p.name)
                tmp.unlink()
                continue
            noi = p.name
            if re.search(r'"(made_for_kids|madeForKids|selfDeclaredMadeForKids|self_declared_made_for_kids)"\s*:', raw):
                kq.them("GHI_CHU", 3, noi, "còn khóa made_for_kids — Apps Script đã bỏ trường này; chỉ vi phạm nếu mã còn selfDeclaredMadeForKids")
            if re.search(r'"(contains_synthetic_media|containsSyntheticMedia)"\s*:\s*true', raw):
                kq.them("VI_PHAM", 1, noi, "contains_synthetic_media = true → YouTube gắn nhãn AI")
            if re.search(r'"[^"]*(location|recording|latitude|longitude)[^"]*"\s*:', raw, _I):
                kq.them("VI_PHAM", 4, noi, "có trường vị trí")
            kiem_tu_cam(kq, raw, noi, "nội dung")
        print(json.dumps({"dem": kq.dem(), "ket_qua": kq.ds}, ensure_ascii=False, indent=1))
        return 0
    if "--mp4" in argv:
        kq = KetQua()
        kiem_mp4(kq, Path(lay("--mp4")))
        print(json.dumps({"dem": kq.dem(), "ket_qua": kq.ds}, ensure_ascii=False, indent=1))
        return 0
    ket = kiem_laptop(lay("--goc"), lay("--tu"), "--khong-luu" not in argv, "--khong-video" not in argv)
    print(json.dumps(ket, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
