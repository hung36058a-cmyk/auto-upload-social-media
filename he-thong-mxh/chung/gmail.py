# -*- coding: utf-8 -*-
"""Gui Gmail cho cac bot MXH (SMTP + mat khau ung dung Google).

Moi thu deu XEP VAO hop-thu-cho/ TRUOC roi moi gui -> mat mang / chua cai mat khau thi khong mat thu,
lan chay sau tu gui bu.

  python gmail.py cai-dat     hoi dia chi Gmail + mat khau ung dung (an khi go), luu bi-mat/gmail.json, gui thu thu
  python gmail.py thu         gui 1 thu thu
  python gmail.py gui-bu      gui cac thu dang cho
  python gmail.py gui-file "<tieu de>" <file.txt>   gui 1 thu soan san (tac vu Claude kiem dang MXH dung)
KHONG in mat khau ra man hinh / nhat ky. bi-mat/ va hop-thu-cho/ nam trong .gitignore.
"""
from __future__ import annotations

import datetime as dt
import getpass
import json
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = HERE / "bi-mat" / "gmail.json"      # {"dia_chi": "...@gmail.com", "mat_khau_ung_dung": "...", "nguoi_nhan": tuy chon}
CHO = HERE / "hop-thu-cho"
NHAT_KY = HERE / "hop-thu-cho" / "nhat-ky-gmail.log"


def _ghi_log(msg: str) -> None:
    CHO.mkdir(exist_ok=True)
    with NHAT_KY.open("a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")


def _cfg() -> dict | None:
    try:
        c = json.loads(CFG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return c if c.get("dia_chi") and c.get("mat_khau_ung_dung") else None


def gui(tieu_de: str, noi_dung: str) -> bool:
    """Xep thu vao hang roi gui. True = da gui het; False = con thu cho (se gui bu)."""
    CHO.mkdir(exist_ok=True)
    f = CHO / f"{dt.datetime.now():%Y%m%d-%H%M%S-%f}.json"
    f.write_text(json.dumps({"tieu_de": tieu_de, "noi_dung": noi_dung}, ensure_ascii=False), encoding="utf-8")
    return gui_bu()


def gui_bu() -> bool:
    c = _cfg()
    thu = sorted(CHO.glob("*.json"))
    if not thu:
        return True
    if not c:
        _ghi_log(f"chua cai Gmail (chay CAI_GMAIL.bat) - {len(thu)} thu dang cho")
        return False
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=40) as s:
            s.login(c["dia_chi"], c["mat_khau_ung_dung"].replace(" ", ""))
            for f in thu:
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    f.rename(f.with_suffix(".hong"))          # thu hong: cat ra, khong chan hang
                    continue
                m = EmailMessage()
                m["Subject"] = d["tieu_de"]
                m["From"] = c["dia_chi"]
                m["To"] = c.get("nguoi_nhan") or c["dia_chi"]
                m.set_content(d["noi_dung"])
                s.send_message(m)
                f.unlink()
                _ghi_log(f"DA_GUI {d['tieu_de'][:80]}")
        return True
    except (OSError, smtplib.SMTPException) as e:                # khong in mat khau, chi ten loi
        _ghi_log(f"LOI gui: {type(e).__name__} {str(e)[:120]}")
        return False


def cai_dat() -> None:
    print("Cai Gmail cho bot MXH. Mat khau ung dung tao o: https://myaccount.google.com/apppasswords")
    dia_chi = input("Dia chi Gmail cua ban: ").strip()
    mk = getpass.getpass("Dan mat khau ung dung 16 ky tu (khong hien chu khi dan, cu dan roi Enter): ").strip()
    if "@" not in dia_chi or len(mk.replace(" ", "")) != 16:
        sys.exit("Sai dia chi hoac mat khau khong du 16 ky tu. Chay lai.")
    CFG.parent.mkdir(exist_ok=True)
    CFG.write_text(json.dumps({"dia_chi": dia_chi, "mat_khau_ung_dung": mk}, ensure_ascii=False), encoding="utf-8")
    print("Da luu. Dang gui thu thu..." )
    print("OK - mo Gmail xem thu '[MXH] Thu cai dat'." if gui("[MXH] Thu cai dat", "Bot MXH da gui duoc Gmail.")
          else "GUI LOI - xem hop-thu-cho/nhat-ky-gmail.log (thuong do sai mat khau ung dung).")


if __name__ == "__main__":
    lenh = (sys.argv[1:] or ["gui-bu"])[0]
    if lenh == "cai-dat":
        cai_dat()
    elif lenh == "gui-file":      # python gmail.py gui-file "<tieu de>" <file .txt UTF-8>  (Claude dung)
        noi = Path(sys.argv[3]).read_text(encoding="utf-8")
        print("DA_GUI" if gui(sys.argv[2], noi) else "CHUA_GUI (vao hang cho, se gui bu)")
    elif lenh == "thu":
        print("DA_GUI" if gui("[MXH] Thu", "Thu thu tu bot MXH.") else "CHUA_GUI (xem nhat-ky-gmail.log)")
    else:
        print("DA_GUI_HET" if gui_bu() else "CON_THU_CHO")
