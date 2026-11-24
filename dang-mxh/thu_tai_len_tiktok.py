# -*- coding: utf-8 -*-
r"""CHAY THU TAI LEN (KHONG DANG): lam dung moi buoc cua may dang TikTok trong Chrome that - kiem tai khoan, doc danh sach
Posts, mo trang Upload, tai video, dien caption, cho TikTok xu ly xong - roi DUNG NGAY TRUOC NUT POST. Khong bam Post,
khong ghi de file dang nhap. Ket qua: chan-doan\thu-tai-len-<ten>.json
Chay: <repo>\.venv\Scripts\python.exe thu_tai_len_tiktok.py <ten file dang nhap> <video.mp4> <caption.txt>"""
import asyncio, json, os, sys, time, traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / "cau-hinh.json").read_text(encoding="utf-8-sig"))
repo = Path(cfg["repo"])
os.chdir(repo)
sys.path.insert(0, str(repo))
from uploader.tk_uploader.main_chrome import TiktokVideo

cookie, video, txt = sys.argv[1], sys.argv[2], sys.argv[3]
acc = next((a for a in cfg["tai_khoan"] if a["mang"] == "tiktok" and a["cookie"] == cookie), {})
res = {"cookie": cookie, "video": Path(video).name, "luc": time.strftime("%Y-%m-%d %H:%M:%S")}
t0 = time.time()
try:
    caption = Path(txt).read_text(encoding="utf-8-sig").strip()
    app = TiktokVideo(caption, Path(video), [], 0, str(repo / "cookies" / "tk_uploader" / f"{cookie}.json"))
    app.headless = False
    app.expected_username = acc.get("username")
    app.tu_luc = time.time()
    app.khong_bam_post = True          # DUNG truoc nut Post
    asyncio.run(app.main())
    res.update(tai_khoan=app.account_username, da_co_san=app.da_co_san, **app.thu)
    res["dat"] = bool(app.thu.get("toi_nut_post")) and not app.thu.get("nut_bi_khoa")
except Exception as e:
    res["loi"] = (str(e).strip().splitlines() or [type(e).__name__])[0][:300]
    res["chi_tiet"] = traceback.format_exc()[-1500:]
res["giay"] = round(time.time() - t0)
out = HERE / "chan-doan"
out.mkdir(exist_ok=True)
(out / f"thu-tai-len-{cookie}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
