# -*- coding: utf-8 -*-
r"""THU KHONG DANG (Instagram): chay dung buoc "dang o tai khoan nao" ma may dang dung truoc moi lan dang.
CHI DOC: mo Instagram bang Chrome an voi file dang nhap, doc ten tai khoan. KHONG dang, KHONG ghi de file dang nhap.
Ket qua: chan-doan\thu-ig-<ten>.json
Chay: <repo>\.venv\Scripts\python.exe thu_instagram.py <ten file dang nhap>"""
import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dang_mxh as M

cookie = sys.argv[1]
cfg = M.load_cfg()
acc = next((a for a in cfg["tai_khoan"] if a.get("mang") == "instagram" and a.get("cookie") == cookie), None)
res = {"cookie": cookie, "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "co_trong_cau_hinh": bool(acc)}
if acc:
    acc["ma"] = f"instagram_{cookie}"
    t0 = time.time()
    res["trang_thai"], res["tai_khoan_that"] = M.check_login(cfg, acc)
    res["mat_giay"] = round(time.time() - t0, 1)
    res["da_ghim"] = M.ghim(acc) or None
    res["duoc_dang"] = M.ly_do_chan(acc, M.dn_record(acc, res["trang_thai"], M.now(), res["tai_khoan_that"])) is None
out = HERE / "chan-doan"
out.mkdir(exist_ok=True)
(out / f"thu-ig-{cookie}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
