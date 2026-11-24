@echo off
chcp 65001 >nul
rem Bam dup SAU KHI sua loi dang MXH: may dang bu ngay + Gmail "Da dang" kem cho da sua.
cd /d "%~dp0thong-bao"
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -X utf8 dang_bu.py
pause
