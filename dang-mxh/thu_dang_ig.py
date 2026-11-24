# -*- coding: utf-8 -*-
r"""THU KHONG DANG (Instagram, QUY TAC KHUNG IG 18/11/2026): chay du cac buoc nhu may that
(kiem file bang ffmpeg -> mo IG -> chon Reel/khung Original -> chup + do khung -> dien caption) roi DUNG truoc nut Share.
KHONG dang, KHONG ghi de file dang nhap.
Chay: python thu_dang_ig.py <cookie> <duong dan video> [file caption .txt]
Ket qua: chan-doan\thu-dang-ig.json + anh chup trong social-auto-upload\.local\instagram-xem-truoc\..."""
import asyncio, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dang_mxh as M

cookie, video = sys.argv[1], Path(sys.argv[2])
txt = Path(sys.argv[3]) if len(sys.argv) > 3 else video.with_suffix(".txt")
cfg = M.load_cfg()
repo = Path(cfg["repo"])
sys.path.insert(0, str(repo))
acc = next(a for a in cfg["tai_khoan"] if a.get("mang") == "instagram" and a.get("cookie") == cookie)
out = {"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "video": str(video)}
tam = HERE / "chan-doan" / "tam-ig"
v, loi = M.kiem_video_ig(video, tam)
out["kiem_file"] = loi or ("đúng 1080x1920 H.264/AAC" if v == video else f"đã đổi sang {v.name}")
if v:
    out["thong_tin"] = {k: x for k, x in M.thong_tin_video(v).items() if k != "tho"}
    thumb = video.with_suffix(".jpg") if video.with_suffix(".jpg").exists() else M.lay_bia_ig(v, tam)
    out["bia"] = str(thumb) if thumb else None
    caption = M.read_caption(txt) if txt.exists() else "test"
    first, _, rest = caption.partition("\n")
    from uploader.meta_uploader.insgraph_uploader.main import InstagramUploader
    import os
    os.chdir(repo)
    up = InstagramUploader(repo / "cookies" / f"instagram_{cookie}.json", title=first.strip(), description=rest.strip(),
                           video_file=v, thumbnail=thumb, headless=True,
                           result_file=HERE / "chan-doan" / "thu-dang-ig-kq.json", thu_khong_dang=True)
    try:
        out["ket_qua"] = asyncio.run(up.upload())
    except Exception as e:
        out["loi"] = str(e)[:1500]
        out["ket_qua"] = up.result
    out["anh_dir"] = str((repo / up.anh_dir).resolve())
(HERE / "chan-doan").mkdir(exist_ok=True)
(HERE / "chan-doan" / "thu-dang-ig.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, default=str)[:3000])
