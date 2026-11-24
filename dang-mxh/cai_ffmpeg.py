# -*- coding: utf-8 -*-
r"""Cai ffmpeg cho may dang (QUY TAC KHUNG IG 18/11/2026): pip install imageio-ffmpeg vao .venv,
chep ffmpeg.exe vao dang-mxh\ffmpeg.exe. Chay 1 lan qua chay-1-lan.json."""
import shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
dich = HERE / "ffmpeg.exe"


def chay(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("$", " ".join(cmd), "->", r.returncode)
    print((r.stdout or "")[-800:], (r.stderr or "")[-800:])
    return r.returncode == 0


try:
    import imageio_ffmpeg  # noqa
except ImportError:
    if not chay([sys.executable, "-m", "pip", "install", "imageio-ffmpeg"]):
        chay([sys.executable, "-m", "ensurepip"])
        if not chay([sys.executable, "-m", "pip", "install", "imageio-ffmpeg"]):
            uv = shutil.which("uv")
            if uv:
                chay([uv, "pip", "install", "--python", sys.executable, "imageio-ffmpeg"])
import imageio_ffmpeg
src = imageio_ffmpeg.get_ffmpeg_exe()
shutil.copy2(src, dich)
print("FFMPEG_OK", dich)
chay([str(dich), "-version"])
