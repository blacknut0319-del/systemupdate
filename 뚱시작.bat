@echo off
title DDONG System
:: 관리자 아니면 UAC로 다시 실행 (Insert/Home/PageUp 핫키용)
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
pushd "%~dp0"
set PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%

where python >nul 2>&1 || where py >nul 2>&1 || (curl -o pyinst.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe && start /wait pyinst.exe /quiet InstallAllUsers=1 PrependPath=1 && del pyinst.exe)
for %%d in ("C:\Program Files\Python311" "%LocalAppData%\Programs\Python\Python311") do if exist %%d\python.exe set PATH=%%d\Scripts\;%%d\;%PATH%

python -m pip install --upgrade pip --quiet
python -m pip install cryptography dxcam opencv-python numpy keyboard pyserial mss pillow customtkinter --quiet

curl -s -o "%TEMP%\dloader.py" "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/ddong_loader.py?t=%RANDOM%"
for /f "tokens=*" %%i in ('python -c "import os,sys; print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do start "" "%%i" "%TEMP%\dloader.py"
exit
