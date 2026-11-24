# -*- coding: utf-8 -*-
"""
DANG BU NGAY SAU KHI SUA (bam dup DA_SUA_XONG.bat, hoac Claude chay: python dang_bu.py --ghi-chu "da sua gi")
1. Hoi "ban da sua gi" (ghi vao thu Gmail "Da dang" -> muc DA SUA).
2. Tra video trong thu muc loi/ ve cho-dang (TRU video "chua ro" - co the da len, khong dang lai de khoi trung).
3. Tai khoan theo khung gio co khung hom nay bi loi/bo lo/het video -> hen video dau hang dang NGAY
   (file <ten>.gio.txt = gio hien tai; tinh nang san co cua may dang, khong chiem khung_gio).
4. Chay may dang 1 luot ngay (cho xong), roi chay thong bao -> Gmail "Da dang ... DA SUA: ...".
Khong sua dang_mxh.py / cau-hinh.json / du-lieu.json.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "chung"))
import mxh_chung as C  # noqa: E402
import thong_bao_mxh as TB  # noqa: E402

VIDEO_EXT = {".mp4", ".mov"}
# bi_chan / thu_lai: khung con trong cua so, may tu thu lai -> KHONG bu (bu them = dang 2 bai)
CAN_BU = {"bo_lo", "loi", "het_video"}
LOI_TOI_DA_GIO = 48     # chi tra ve hang cho video loi trong 48 gio qua (cu hon: de nguoi xem tay)
PY_MAY_DANG = C.DANG_MXH.parent / "social-auto-upload" / ".venv" / "Scripts" / "python.exe"


def co_the_da_len(noi_dung: str) -> bool:
    l = noi_dung.lower()
    return "không đăng lại" in l or "chưa rõ" in l or "chua_ro" in l


def tra_ve_hang_cho(acc: dict, lam: bool = True) -> tuple[list[str], list[str]]:
    """(video da tra ve cho-dang, video can xem tay). lam=False: chi liet ke, khong chuyen file."""
    q = Path(acc["thu_muc"])
    loi_dir, cho = q / "loi", q / "cho-dang"
    tra, xem = [], []
    for lt in sorted(loi_dir.glob("*.loi.txt")) if loi_dir.exists() else []:
        stem = lt.name[:-len(".loi.txt")]
        try:
            noi = lt.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            noi = ""
        video = next((f for f in loi_dir.iterdir() if f.stem == stem and f.suffix.lower() in VIDEO_EXT), None)
        cu = time.time() - lt.stat().st_mtime > LOI_TOI_DA_GIO * 3600
        if co_the_da_len(noi) or video is None or cu or (cho / video.name).exists():
            xem.append(video.name if video else lt.name)
            continue
        if not lam:
            tra.append(video.name)
            continue
        cho.mkdir(exist_ok=True)
        for f in [x for x in loi_dir.iterdir() if x.stem == stem and x != lt]:   # video + caption + anh bia
            f.replace(cho / f.name)
        lt.replace(lt.with_name(lt.name + ".da-sua"))      # giu lai ly do loi, bang trang thai khong dem nua
        tra.append(video.name)
    return tra, xem


def da_bu_hom_nay(ma: str, acc: dict, t) -> bool:
    """Da co video hen bu (dang cho hoac da dang hom nay) -> bam DA_SUA_XONG lan nua khong hen them."""
    cho = Path(acc["thu_muc"]) / "cho-dang"
    if cho.exists() and any(cho.glob("*.gio.txt")):
        return True
    done = ((C.doc_json(C.SO_GHI, {}) or {}).get("da_xu_ly") or {}).get(ma) or {}
    return any(k.startswith(t.strftime("%Y-%m-%d")) and " hen " in k for k in done)


def hen_dang_ngay(acc: dict, uu_tien: list[str], t) -> str | None:
    cho = Path(acc["thu_muc"]) / "cho-dang"
    videos = sorted(f for f in cho.glob("*") if f.suffix.lower() in VIDEO_EXT
                    and (cho / f"{f.stem}.txt").exists() and not (cho / f"{f.stem}.gio.txt").exists())
    chon = next((v for v in videos if v.name in uu_tien), videos[0] if videos else None)
    if chon:
        (cho / f"{chon.stem}.gio.txt").write_text(t.strftime("%Y-%m-%d %H:%M"), encoding="utf-8")
        return chon.name
    return None


def main(argv: list[str]) -> None:
    ghi_chu = argv[argv.index("--ghi-chu") + 1].strip() if "--ghi-chu" in argv and argv.index("--ghi-chu") + 1 < len(argv) else ""
    if not ghi_chu and "--khong-hoi" not in argv:
        ghi_chu = input("Bạn đã sửa gì? (gõ ngắn rồi Enter, bỏ trống cũng được): ").strip()
    t = C.now()
    sap_tra = [f"{C.ten_tk(m, a)}: {v}" for m, a in C.tai_khoan_bat().items() for v in tra_ve_hang_cho(a, lam=False)[0]]
    if sap_tra and "--khong-hoi" not in argv:
        print("Sẽ trả các video lỗi này về hàng chờ để đăng lại:\n- " + "\n- ".join(sap_tra))
        if input("Có video nào trong đây ĐÃ LÊN mạng rồi không? Gõ c (có) để dừng, Enter để tiếp tục: ").strip().lower().startswith("c"):
            sys.exit("Đã dừng, không đổi gì. Nói với Claude /dang-mxh video nào đã lên để xử lý tay.")
    st = C.doc_json(C.STATUS, {}) or {}
    the = {a["ma"]: a for a in st.get("tai_khoan", [])}
    bao, can_xem, ghi = [], [], C.doc_json(TB.GHI_CHU_SUA, {}) or {}
    for ma, acc in C.tai_khoan_bat().items():
        ten = C.ten_tk(ma, acc)
        tra, xem = tra_ve_hang_cho(acc)
        can_xem += [f"{ten}: {x}" for x in xem]
        if tra:
            ghi.setdefault(ma, []).append(f"trả {len(tra)} video lỗi về hàng chờ")
        hong = [r for r in (the.get(ma) or {}).get("hom_nay", []) if r.get("trang_thai") in CAN_BU]
        if acc.get("dang_ngay"):
            if tra:
                bao.append(f"{ten}: trả {len(tra)} video về hàng chờ → đăng ở lượt kế")
        elif (tra or hong) and da_bu_hom_nay(ma, acc, t):
            bao.append(f"{ten}: hôm nay đã hẹn/đăng bù rồi → không bù thêm")
        elif tra or hong:
            v = hen_dang_ngay(acc, tra, t)
            bao.append(f"{ten}: " + (f"đăng bù NGAY {v}" if v else "muốn đăng bù nhưng hàng chờ HẾT video → bỏ thêm video"))
            if v:
                ghi.setdefault(ma, []).append("đăng bù khung bị lỡ")
    if ghi_chu:
        ghi.setdefault("*", []).append(ghi_chu)
    C.ghi_json(TB.GHI_CHU_SUA, ghi)

    print("\n".join(bao) or "Không có tài khoản nào cần đăng bù hôm nay.")
    if can_xem:
        print("CẦN XEM TAY (có thể đã lên, máy không đăng lại):\n- " + "\n- ".join(can_xem))
    if bao and "--khong-chay" not in argv:
        print("Đang chạy máy đăng... (đừng tắt cửa sổ, có thể mất vài phút)")
        if (C.DANG_MXH / ".dang-chay.lock").exists():
            print("Máy đăng đang chạy lượt tự động → lượt này bỏ qua; video hẹn bù sẽ đăng trong ≤10 phút, thư Gmail tới sau.")
        try:
            r = subprocess.run([str(PY_MAY_DANG), str(C.DANG_MXH / "dang_mxh.py")], cwd=str(C.DANG_MXH), timeout=45 * 60)
            print("Máy đăng chạy xong." if r.returncode == 0 else f"Máy đăng trả mã {r.returncode} (xem nhat-ky.log).")
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"Không chạy được máy đăng ({type(e).__name__}); lượt tự động 10 phút sau sẽ đăng.")
    TB.chay()      # gui Gmail "Da dang ... DA SUA" (neu may dang con khoa vi dang chay, thu se toi o luot 10 phut sau)
    print("Xong. Mở Gmail xem thư [MXH].")


if __name__ == "__main__":
    main(sys.argv[1:])
