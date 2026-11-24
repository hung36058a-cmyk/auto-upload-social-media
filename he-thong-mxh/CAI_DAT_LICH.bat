@echo off
chcp 65001 >nul
rem Bam dup 1 lan: dat lich Windows ThongBaoMXH (Gmail bao dang, 10 phut/lan). Kiem 2 gio = tac vu Claude kiem-dang-mxh-2-gio.
set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
schtasks /create /f /tn "ThongBaoMXH" /sc minute /mo 10 /st 00:03 /tr "\"%PYW%\" -X utf8 \"%~dp0thong-bao\thong_bao_mxh.py\""
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew; try { Set-ScheduledTask -TaskName 'ThongBaoMXH' -Settings $s -ErrorAction Stop | Out-Null; Write-Host 'Da bat chay ca khi dung pin' } catch { Write-Host ('CHU Y: chua chay duoc khi dung pin: ' + $_.Exception.Message) }"
echo.
echo === Xong: ThongBaoMXH (10 phut/lan) ===
pause
