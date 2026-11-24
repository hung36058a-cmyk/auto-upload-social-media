@echo off
chcp 65001 >nul
title Dang nhap Facebook cho may tu dang (2 Fanpage: Vietwan + econlazypack)
cd /d "%~dp0..\social-auto-upload"
echo.
echo  Mot cua so Chrome se mo trang Meta Business Suite.
echo  Dang nhap Facebook (tai khoan quan ly 2 Fanpage). Dang nhap xong cua so tu dong.
echo  Khong can bam gi them. Doi toi da 10 phut.
echo.
".venv\Scripts\sau.exe" facebook-page login --account fb_vietwan
if errorlevel 1 (
  echo.
  echo  CHUA DANG NHAP DUOC. Chay lai file nay hoac chup man hinh gui Claude.
  pause
  exit /b 1
)
rem Ca 2 Fanpage dung chung 1 tai khoan Facebook -> dung chung file dang nhap
copy /y "cookies\facebook-page_fb_vietwan.json" "cookies\facebook-page_fb_econ.json" >nul
echo.
echo  Kiem tra lai dang nhap...
".venv\Scripts\sau.exe" facebook-page check --account fb_vietwan
echo.
echo  XONG. May tu dang se dang Reels len 2 Fanpage moi khi video TikTok duoc dang.
pause
