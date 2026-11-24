@echo off
chcp 65001 >nul
title Cai lich tu dang MXH
rem Tao task "DangMXH": cu 10 phut chay dang_mxh.py 1 lan (an cua so)
schtasks /create /f /tn "DangMXH" /sc minute /mo 10 /tr "wscript.exe \"%~dp0chay_an.vbs\""
if errorlevel 1 (echo LOI: khong tao duoc lich. & pause & exit /b)
rem Mac dinh Windows KHONG chay lich khi laptop dung pin -> bat cho chay ca khi dung pin + chay bu khi lo gio
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew; Set-ScheduledTask -TaskName 'DangMXH' -Settings $s -ErrorAction Stop | Out-Null; Write-Host 'Da bat: lich chay ca khi laptop dung pin.' } catch { Write-Host ('CHU Y: chua bat duoc che do chay khi dung pin: ' + $_.Exception.Message) }"
echo.
echo Dang chay thu 1 luot (chi ghi trang thai, khong dang)...
"%~dp0..\social-auto-upload\.venv\Scripts\python.exe" "%~dp0dang_mxh.py" --chi-ghi
echo.
echo === XONG: may se tu dang theo khung gio, 10 phut kiem 1 lan ===
pause
