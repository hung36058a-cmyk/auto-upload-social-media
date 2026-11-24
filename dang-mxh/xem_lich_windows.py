# -*- coding: utf-8 -*-
r"""CHI DOC: xem cai dat cua lich "DangMXH" trong Windows (co chay khi laptop dung pin khong, co chay bu khi lo gio khong...).
Khong doi gi. Ket qua: chan-doan\lich-windows.txt"""
import subprocess
from pathlib import Path

out = Path(__file__).resolve().parent / "chan-doan"
out.mkdir(exist_ok=True)
p = subprocess.run(["schtasks", "/query", "/tn", "DangMXH", "/xml"], capture_output=True)
txt = ""
for raw in (p.stdout, p.stderr):
    for enc in ("utf-8", "utf-16", "cp950", "cp1252"):
        try:
            txt += raw.decode(enc)
            break
        except Exception:
            continue
(out / "lich-windows.txt").write_text(txt, encoding="utf-8")
print(txt)
