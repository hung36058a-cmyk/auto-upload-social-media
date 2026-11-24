@echo off
chcp 65001 >nul
title Xac nhan (ghim) tai khoan dang MXH
echo May se hoi tung tai khoan chua ghim: day co dung kenh cua ban khong?
echo Ghim xong, neu sau nay dang nhap nham sang kenh khac thi may tu dung, khong dang.
echo.
"%~dp0..\social-auto-upload\.venv\Scripts\python.exe" "%~dp0dang_mxh.py" --ghim
echo.
pause
