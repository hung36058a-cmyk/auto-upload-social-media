@echo off
chcp 65001 >nul
title Dang nhap lai TikTok / Instagram / Threads (may tu kiem dung kenh)
cd /d "%~dp0..\social-auto-upload"
".venv\Scripts\python.exe" "%~dp0dang_nhap_lai.py" %*
echo.
pause
