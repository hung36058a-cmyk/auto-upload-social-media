# -*- coding: utf-8 -*-
"""Tu kiem logic bot MXH bang du lieu gia (khong mang, khong gui Gmail, khong dung may dang that).
Chay: python -X utf8 test_mxh.py   -> in "TAT CA DAT" neu dung."""
from __future__ import annotations

import datetime as dt
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parents[1]      # he-thong-mxh
for p in ("chung", "thong-bao", "kiem-2-gio"):
    sys.path.insert(0, str(R / p))
import mxh_chung as C  # noqa: E402
import thong_bao_mxh as TB  # noqa: E402
import dang_bu as DB  # noqa: E402
import kiem_2_gio as K  # noqa: E402

t = dt.datetime(2026, 11, 24, 11, 30, tzinfo=C.TZ)
iso = lambda d: d.isoformat()  # noqa: E731


def test_gom_su_kien():
    st = {"cap_nhat_luc": iso(t - dt.timedelta(minutes=5)), "ngay": "2026-11-24", "loi_he_thong": [],
          "tai_khoan": [
              {"ma": "instagram_x", "mang": "instagram", "kenh": "Econ", "dang_nhap": {"trang_thai": "ok"},
               "hom_nay": [{"gio": "08:00", "trang_thai": "bo_lo"}],
               "lich_toi": [{"luc": iso(t + dt.timedelta(minutes=30)), "file": "a.mp4"},     # sap dang
                            {"luc": iso(t + dt.timedelta(minutes=50)), "file": "b.mp4"},     # chua toi 35 phut
                            {"luc": iso(t + dt.timedelta(minutes=20)), "file": None}]},      # het video
              {"ma": "tiktok_v", "mang": "tiktok", "kenh": "V", "dang_ngay": True,
               "dang_nhap": {"trang_thai": "sai_tai_khoan", "tai_khoan_that": "b", "can": "a"},
               "lich_toi": [{"luc": None, "file": "c.mp4"}]},
              {"ma": "tiktok_econlazypack", "mang": "tiktok", "kenh": "E", "dang_nhap": {"trang_thai": "ok"},
               "hom_nay": [{"gio": "12:00", "trang_thai": "het_video"}],
               "lich_toi": [{"luc": iso(t + dt.timedelta(minutes=10)), "file": None}]}],   # DANG_TAY -> im
          "lich_su": [{"tk": "tiktok_v", "luc": iso(t - dt.timedelta(minutes=8)), "kq": "ok", "file": "z.mp4", "link": "L"},
                      {"tk": "tiktok_v", "luc": iso(t - dt.timedelta(days=2)), "kq": "ok", "file": "old.mp4"},   # truoc bat_dau
                      {"tk": "instagram_x", "luc": iso(t - dt.timedelta(minutes=9)), "kq": "chua_ro", "file": "q.mp4", "loi": "x"}]}
    so = {"bat_dau": iso(t - dt.timedelta(hours=1)), "da_bao": {}, "loi_mo": {}}
    loi, ok, sap = TB.gom_su_kien(st, so, t, {})
    assert [k for k, _, _ in sap] == ["sap|instagram_x|" + iso(t + dt.timedelta(minutes=30)) + "|a.mp4", "sap|tiktok_v|c.mp4"], sap
    assert len(ok) == 1 and "z.mp4" in ok[0][2], ok
    st2 = {**st, "lich_su": [{"tk": "tiktok_v", "luc": iso(t), "kq": "ok", "file": "w.mp4", "loi": "ĐĂNG NHẦM TRANG"}]}
    l2, o2, _ = TB.gom_su_kien(st2, so, t, {})
    assert o2 and any(k.startswith("okloi|") for k, _, _ in l2), "bai len nham trang phai vao muc LOI"
    ks = [k for k, _, _ in loi]
    assert any(k.startswith("tt|instagram_x") for k in ks) and any(k.startswith("trong|instagram_x") for k in ks)
    assert any(k.startswith("dn|tiktok_v|sai_tai_khoan") for k in ks) and any(k.startswith("loi|instagram_x|q.mp4") for k in ks)
    assert not any("econlazypack" in k for k in ks), "tai khoan dang tay khong duoc bao het video"
    # may dang khong chay
    st["cap_nhat_luc"] = iso(t - dt.timedelta(minutes=45))
    assert any(k.startswith("chet|") for k, _, _ in TB.gom_su_kien(st, so, t, {})[0])


def test_soan_thu_da_sua():
    tieu, noi = TB.soan_thu([], [("ok|v|1", "tiktok_v", "V · TikTok lúc ...")], [], {"tiktok_v": ["đăng nhập lại"]})
    assert "Đã đăng 1" in tieu and "ĐÃ SỬA: đăng nhập lại" in noi


def test_dang_bu():
    with tempfile.TemporaryDirectory() as d:
        q = Path(d)
        (q / "loi").mkdir(); (q / "cho-dang").mkdir()
        for n in ("a.mp4", "a.txt", "b.mp4", "b.txt"):
            (q / "loi" / n).write_text("x", encoding="utf-8")
        (q / "loi" / "a.loi.txt").write_text("Qua 20 phut chua xong", encoding="utf-8")
        (q / "loi" / "b.loi.txt").write_text("Đã bấm Chia sẻ ... Máy KHÔNG đăng lại để khỏi trùng", encoding="utf-8")
        tra, xem = DB.tra_ve_hang_cho({"thu_muc": str(q)})
        assert tra == ["a.mp4"] and xem == ["b.mp4"], (tra, xem)
        assert (q / "cho-dang" / "a.mp4").exists() and (q / "cho-dang" / "a.txt").exists()
        assert (q / "loi" / "a.loi.txt.da-sua").exists() and (q / "loi" / "b.mp4").exists()
        v = DB.hen_dang_ngay({"thu_muc": str(q)}, tra, t)
        assert v == "a.mp4" and (q / "cho-dang" / "a.gio.txt").read_text(encoding="utf-8") == "2026-11-24 11:30"
        assert DB.hen_dang_ngay({"thu_muc": str(q)}, [], t) is None      # a da hen, khong con video khac
        assert DB.da_bu_hom_nay("x", {"thu_muc": str(q)}, t), "da co .gio.txt -> bam lan 2 khong hen them"
        old = q / "loi" / "c.loi.txt"; (q / "loi" / "c.mp4").write_text("x"); old.write_text("timeout")
        import os; os.utime(old, (0, 0))                                   # loi qua 48 gio -> khong tra ve
        assert DB.tra_ve_hang_cho({"thu_muc": str(q)}, lam=False) == ([], ["b.mp4", "c.mp4"])


def test_kiem_bai():
    K.tiktok = lambda link: {"views": 0, "likes": 0, "tai_khoan": "nguoi_khac"}   # khong goi mang
    K.time.sleep = lambda s: None
    h = {"tk": "tiktok_v", "luc": iso(t - dt.timedelta(hours=3)), "link": "https://www.tiktok.com/@dung/video/1"}
    _, vd = K.kiem_bai(h, {"mang": "tiktok", "username": "dung"}, t)
    assert any(m == "VI_PHAM" and "@nguoi_khac" in c for m, c in vd) and any("0 lượt xem" in c for _, c in vd), vd
    _, vd = K.kiem_bai({"tk": "facebook_p", "link": "...asset_id=999"}, {"mang": "facebook", "page_id": "111"}, t)
    assert vd and vd[0][0] == "VI_PHAM"
    _, vd = K.kiem_bai({"tk": "threads_e", "link": "https://www.threads.com/@e/post/1"}, {"mang": "threads", "username": "e"}, t)
    assert vd == []


def test_kiem_loi_chan():
    sys.path.insert(0, str(R.parent / "kiem-tra-mxh"))
    sys.path.insert(0, str(R.parent / "dang-mxh"))
    import kiem_loi as KL
    import dang_mxh as DM
    with tempfile.TemporaryDirectory() as d:
        md, txt = Path(d) / "LOI.md", Path(d) / "VIETWAN_a.txt"
        md.write_text("KENH: vietwan\n- [X1] CAM caption /cam_nay/i :: thu\n", encoding="utf-8")
        txt.write_text("Tin Đài Loan cho người Việt\n", encoding="utf-8")
        assert not any("[X1]" in x for x in KL.kiem("vietwan", [txt], str(md)))
        txt.write_text("Tin Đài Loan có CAM_NAY\n", encoding="utf-8")
        assert any("[X1]" in x for x in KL.kiem("vietwan", [txt], str(md)))
        md.write_text("KENH: vietwan\n- [X1] CAM caption /(hong :: thu\n", encoding="utf-8")
        assert KL.main(["vietwan", str(txt), "--loi", str(md)]) == 1      # luat viet sai -> chan
        for sai in ("- [X1] Cam caption /a/ :: x", "* [X1] CAM caption /a/ :: x", "- [X1] CAM video /a/ :: x", ""):
            md.write_text(f"KENH: vietwan\n## Máy kiểm\n{sai}\n", encoding="utf-8")
            assert KL.main(["vietwan", str(txt), "--loi", str(md)]) == 1, sai
        md.write_text("KENH: vietwan\n- [X1] CAM caption /cam_nay/i :: thu\n", encoding="utf-8")
        txt.write_text("có cam_nay\n", encoding="utf-16")
        assert any("[X1]" in x for x in KL.kiem("vietwan", [txt], str(md)))
        assert KL.main(["vietwan", str(Path(d) / "khong-co")]) == 1       # khong co file -> chan

    # may dang: bi chan -> khong goi ham dang, video chuyen sang loi
    goi, ghi = [], []
    DM.POSTERS = {"tiktok": lambda *a: goi.append(1) or {"ok": True}}
    DM.ly_do_chan = lambda *a: None
    DM.kiem_loi_kenh = lambda acc, item: ["[X1] sai"]
    DM.ap_dung = lambda cfg, data, acc, key, tep, cap, res: ghi.append(res)
    item = {"video": Path("a.mp4"), "txt": Path("a.txt"), "thumb": None, "caption": "c"}
    data = {"da_xu_ly": {}, "dang_nhap": {}, "thu": {}, "dang_do": {}}
    DM.dang_1_video({"so_lan_thu_lai": 2}, data, {"ma": "tiktok_v", "mang": "tiktok"}, t, "k", item, {}, [])
    assert not goi and "LOI.md" in ghi[0]["loi"] and data["thu"]["tiktok_v|k"]["n"] == 2
    # tai LAI sau khi het gio cho xac nhan cung phai qua cong
    data["thu"] = {"tiktok_v|k": {"n": 1, "cho_xn": iso(t.replace(tzinfo=None) - dt.timedelta(hours=2))}}
    DM.dang_1_video({"so_lan_thu_lai": 2, "cho_xac_nhan_phut": 30}, data, {"ma": "tiktok_v", "mang": "tiktok"}, t.replace(tzinfo=None), "k", item, {}, [])
    assert not goi and len(ghi) == 2


if __name__ == "__main__":
    for f in [v for k, v in dict(globals()).items() if k.startswith("test_")]:
        f()
        print("DAT", f.__name__)
    print("TAT CA DAT")
