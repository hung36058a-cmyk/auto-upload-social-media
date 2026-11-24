@echo off
chcp 65001 >nul
title Kiem tra dang nhap MXH
"%~dp0..\social-auto-upload\.venv\Scripts\python.exe" "%~dp0dang_mxh.py" --kiem-tra --chi-ghi
echo.
echo Xem ket qua tren bang theo doi (hoac file trang-thai-mxh.json).
pause
