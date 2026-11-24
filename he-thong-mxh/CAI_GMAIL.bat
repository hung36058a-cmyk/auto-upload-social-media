@echo off
chcp 65001 >nul
rem Bam dup 1 lan: luu Gmail + mat khau ung dung de bot MXH gui thu. Tao mat khau: https://myaccount.google.com/apppasswords
cd /d "%~dp0chung"
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -X utf8 gmail.py cai-dat
pause
