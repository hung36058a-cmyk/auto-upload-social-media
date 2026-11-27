# -*- coding: utf-8 -*-
"""
KIEM LOI THEO KENH - chay BAT BUOC truoc khi dua video vao hang cho / Drive. Chi doc, khong sua file nao.
  python kiem_loi.py <vietwan|econ|tso|cq> <file|thu muc>... [--loi <duong dan LOI.md>]
Ma thoat: 0 = DAT, 1 = CHAN (co loi, hoac khong kiem duoc: thieu LOI.md, luat viet sai, khong co file).

Moi kenh 1 file <thu muc kenh>/LOI.md. Dong may kiem:
  - [ma] CAM   <o> /regex/   :: ly do      (khong duoc co)
  - [ma] PHAI  <o> /regex/   :: ly do      (bat buoc co)
  - [ma] TOIDA <o> <so>      :: ly do      (so ky tu toi da)
  - [ma] GIAY  video <a>-<b> :: ly do      (do dai video, giay)
/regex/ co the them co: i (khong phan biet hoa thuong), m (^ $ theo dong).
<o> (cach nhau dau phay): title mota tags binhluan (trong .json) | caption (.txt, hoac json "tiktok"/"caption")
  | threads (.txt trong thu muc threads*) | baichu (.chu.txt) | srt | json (nguyen file) | tenfile | chu (moi cho co chu)
Dong "- [ma] chu thuong" = luat nguoi/agent kiem, script bo qua.
Tu cam AI, nham kenh, nhan AI/vi tri, metadata video: dung lai kiem_tra_mxh.py (khong chep lai vao LOI.md).
"""
from __future__ import annotations

import codecs
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import kiem_tra_mxh as ktm  # noqa: E402

KENH = {"vietwan": "02_Vietwan", "econ": "04_econlazypack", "tso": "01_The-Still-Observer", "cq": "03_ChineseQuest"}
O = {"title", "mota", "tags", "binhluan", "caption", "threads", "baichu", "srt", "json", "tenfile", "chu", "video"}
LOAI = ("CAM", "PHAI", "TOIDA", "GIAY")
VIDEO = (".mp4", ".mov", ".webm")


class LoiKiem(Exception):
    """Khong kiem duoc -> phai chan."""


def tim_loi_md(kenh: str, files: list[Path]) -> Path:
    # may that: ../../<kenh>/LOI.md; may ao (mount rieng tung thu muc): di nguoc len tu file dang kiem
    ung = [Path(__file__).resolve().parents[2] / KENH[kenh] / "LOI.md"]
    if files:
        ung += [d / "LOI.md" for d in files[0].resolve().parents]
    for p in ung:
        if p.is_file() and f"KENH: {kenh}" in p.read_text(encoding="utf-8-sig"):
            return p
    raise LoiKiem(f"không thấy LOI.md của kênh {kenh} (thử --loi <đường dẫn>)")


def doc_luat(p: Path) -> list[dict]:
    luat, muc_may = [], False
    for so, dong in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
        m = re.match(r"\s*-\s*\[(\w+)\]\s+(%s)\b(.*)$" % "|".join(LOAI), dong)
        if dong.startswith("## "):
            muc_may = dong.startswith("## Máy kiểm")
        if not m:
            if muc_may and dong.lstrip().startswith(("-", "*")):     # go sai -> khong duoc am tham bo qua
                raise LoiKiem(f"LOI.md dòng {so} nằm trong mục Máy kiểm nhưng sai cú pháp: {dong.strip()}")
            continue
        ma, loai, con = m.groups()
        try:
            than, ly_do = con.split("::", 1)
            o, gia = than.split(None, 1)
            o, gia = o.split(","), gia.strip()
            if set(o) - O:
                raise ValueError(f"ô lạ {set(o) - O}")
            if loai != "GIAY" and "video" in o:
                raise ValueError("ô video chỉ dùng với GIAY")
            if loai in ("CAM", "PHAI"):
                r = re.fullmatch(r"/(.+)/([im]*)", gia)
                co = (re.I if "i" in r[2] else 0) | (re.M if "m" in r[2] else 0)
                gia = re.compile(unicodedata.normalize("NFC", r[1]), co)
            elif loai == "TOIDA":
                gia = int(gia)
            else:
                gia = tuple(float(x) for x in gia.split("-"))
                if len(gia) != 2 or o != ["video"]:
                    raise ValueError("GIAY video a-b")
        except Exception as e:
            raise LoiKiem(f"LOI.md dòng {so} viết sai cú pháp ({type(e).__name__}: {e}): {dong.strip()}")
        luat.append({"ma": ma, "loai": loai, "o": o, "gia": gia, "ly_do": ly_do.strip()})
    if not luat:
        raise LoiKiem(f"{p} không có luật máy kiểm nào")
    return luat


def giay_video(p: Path) -> float | None:
    """Do dai mp4/mov doc tu hop moov > mvhd (khong can ffprobe)."""
    with open(p, "rb") as f:
        while len(h := f.read(8)) == 8:
            n, dau = int.from_bytes(h[:4], "big"), 8
            if n == 1:
                n, dau = int.from_bytes(f.read(8), "big"), 16
            if n < dau:
                return None
            if h[4:] != b"moov":
                f.seek(n - dau, 1)
                continue
            d = f.read(n - dau)
            i = d.find(b"mvhd") + 4
            if i < 4 or len(d) < i + 32:     # moov cut
                return None
            ti_le, dai = (i + 20, (i + 24, i + 32)) if d[i] == 1 else (i + 12, (i + 16, i + 20))
            t = int.from_bytes(d[ti_le:ti_le + 4], "big")
            return int.from_bytes(d[dai[0]:dai[1]], "big") / t if t else None
    return None


def cac_o(p: Path) -> dict:
    """Tra {o: chu} cua 1 file chu."""
    raw = p.read_bytes()     # nhu may dang: nhan ca UTF-16 (Notepad "Unicode")
    ma_hoa = "utf-16" if raw[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE) else "utf-8-sig"
    chu = unicodedata.normalize("NFC", "\n".join(raw.decode(ma_hoa).splitlines()))
    if p.suffix.lower() == ".srt":
        return {"srt": chu}
    if p.suffix.lower() == ".txt":
        if p.name.endswith(".chu.txt"):
            return {"baichu": chu}
        if any(x.name.lower().startswith("threads") for x in list(p.resolve().parents)[:3]):
            return {"threads": chu}
        return {"caption": chu}
    m = json.loads(chu)
    if not isinstance(m, dict):
        raise ValueError("json không phải metadata video")
    m = json.loads(unicodedata.normalize("NFC", json.dumps(m, ensure_ascii=False)))
    tags = m.get("tags") or []
    o = {"json": chu, "title": str(m.get("title", "")), "mota": str(m.get("description", "")),
         "tags": ", ".join(map(str, tags)) if isinstance(tags, list) else str(tags)}
    for k, ten in (("tiktok", "caption"), ("caption", "caption"), ("pin_comment", "binhluan")):
        if isinstance(m.get(k), str):
            o[ten] = m[k]
    return o


def kiem(kenh: str, duong: list, loi_md: str | None = None) -> list[str]:
    """Tra danh sach loi (rong = dat). Raise LoiKiem neu khong kiem duoc."""
    if kenh not in KENH:
        raise LoiKiem(f"kênh lạ: {kenh} (chọn: {', '.join(KENH)})")
    files = []
    for d in map(Path, duong):
        if not d.exists():
            raise LoiKiem(f"không có file/thư mục: {d}")
        files += sorted(x for x in d.rglob("*") if x.is_file()) if d.is_dir() else [d]
    files = [f for f in files if f.suffix.lower() in (".txt", ".json", ".srt", ".jpg", ".png") + VIDEO
             and not f.name.endswith((".gio.txt", ".loi.txt"))]
    if not files:
        raise LoiKiem("không có file nào để kiểm")
    luat = doc_luat(Path(loi_md) if loi_md else tim_loi_md(kenh, files))
    loi = []
    for p in files:
        kq = ktm.KetQua()
        o = {}
        duoi = p.suffix.lower()
        try:
            if duoi in VIDEO:
                ktm.kiem_mp4(kq, p, p.name)
                if any(r["loai"] == "GIAY" for r in luat):
                    giay = giay_video(p)
                    for r in (r for r in luat if r["loai"] == "GIAY"):
                        if giay is None:
                            loi.append(f"[{r['ma']}] {p.name}: không đọc được độ dài video")
                        elif not r["gia"][0] <= giay <= r["gia"][1]:
                            loi.append(f"[{r['ma']}] {p.name}: dài {giay:.1f} giây → {r['ly_do']}")
            elif duoi in (".txt", ".json", ".srt"):
                o = cac_o(p)
                if duoi == ".json":
                    ktm.kiem_json_youtube(kq, p, kenh)
                elif "caption" in o and kenh in ("vietwan", "econ"):
                    ktm.kiem_caption(kq, "", kenh, "instagram", p.name, o["caption"], p.name)
                else:
                    ktm.kiem_tu_cam(kq, next(iter(o.values())), p.name, duoi)
        except ValueError as e:     # OSError (file dang bi khoa) -> nem ra: giu hang cho, luot sau kiem lai
            loi.append(f"{p.name}: không đọc được ({type(e).__name__}: {e})")
            continue
        loi += [f"[chung-{d['tieu_chi']}] {d['noi']}: {d['chi_tiet']}" for d in kq.ds if d["muc"] == "VI_PHAM"]
        o["tenfile"] = p.name
        for r in luat:
            for ten, chu in o.items():
                if not (ten in r["o"] or ("chu" in r["o"] and ten not in ("json", "tenfile"))):
                    continue
                if r["loai"] == "CAM" and (m := r["gia"].search(chu)):
                    loi.append(f"[{r['ma']}] {p.name} ({ten}) có \"{m[0].strip()[:60]}\" → {r['ly_do']}")
                elif r["loai"] == "PHAI" and not r["gia"].search(chu):
                    loi.append(f"[{r['ma']}] {p.name} ({ten}) thiếu → {r['ly_do']}")
                elif r["loai"] == "TOIDA" and len(chu.strip()) > r["gia"]:
                    loi.append(f"[{r['ma']}] {p.name} ({ten}) dài {len(chu.strip())} > {r['gia']} ký tự → {r['ly_do']}")
    return list(dict.fromkeys(loi))


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    loi_md = None
    if "--loi" in argv:
        i = argv.index("--loi")
        loi_md, argv = (argv[i + 1:i + 2] or [""])[0], argv[:i] + argv[i + 2:]
    try:
        if len(argv) < 2:
            raise LoiKiem("cách dùng: kiem_loi.py <kênh> <file|thư mục>...")
        loi = kiem(argv[0], argv[1:], loi_md)
    except Exception as e:
        print(f"CHAN - không kiểm được: {e}")
        return 1
    if loi:
        print(f"CHAN - {len(loi)} lỗi, KHÔNG đưa vào hàng chờ/Drive:")
        print("\n".join("  " + x for x in loi))
        return 1
    print("DAT")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
