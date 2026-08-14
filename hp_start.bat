@echo off
pushd "%~dp0"
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"
title DDONG Attacker

set "PYEXE="
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python311\python.exe"
if exist "C:\Program Files\Python311\python.exe" set "PYEXE=C:\Program Files\Python311\python.exe"

:: === Step 1: Python install ===
echo [1/4] Checking Python...
if defined PYEXE goto :step2

echo Python not found. Downloading installer...
bitsadmin /transfer "pyinst" /download /priority high "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" "%TEMP%\pyinst.exe"
if %errorlevel% neq 0 (
    echo ERROR: Cannot download Python. Check internet.
    pause
    exit /b 1
)

echo Installing Python...
start /wait "" "%TEMP%\pyinst.exe" /quiet InstallAllUsers=1 PrependPath=1
del "%TEMP%\pyinst.exe"

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python311\python.exe"
if exist "C:\Program Files\Python311\python.exe" set "PYEXE=C:\Program Files\Python311\python.exe"

if not defined PYEXE (
    echo ERROR: Python install failed. Run as Administrator.
    pause
    exit /b 1
)

:: === Step 2: Packages (MUST use the same PYEXE that will launch) ===
:step2
echo [2/4] Installing packages...
"%PYEXE%" -m pip install --upgrade pip --quiet 2>nul
"%PYEXE%" -m pip install numpy pillow mss keyboard pywin32 opencv-python dxcam --quiet 2>nul
if %errorlevel% neq 0 (
    "%PYEXE%" -m pip install numpy pillow mss keyboard pywin32 opencv-python dxcam
    if %errorlevel% neq 0 (
        echo ERROR: Package install failed.
        pause
        exit /b 1
    )
)
echo Packages OK.

:: === Step 3: Download attacker (API direct, no CDN) ===
echo [3/4] Downloading attacker...
"%PYEXE%" -c "import urllib.request,base64,json; req=urllib.request.Request('https://api.github.com/repos/blacknut0319-del/systemupdate/contents/attacker_hp.pyw', headers={'User-Agent':'ddong-attacker'}); d=json.loads(urllib.request.urlopen(req).read()); open(r'%~dp0attacker_hp.pyw','wb').write(base64.b64decode(d['content']))"
if %errorlevel% neq 0 (
    echo ERROR: Download failed.
    pause
    exit /b 1
)
echo Attacker OK.

:: === Step 4: Run with the SAME Python as pip ===
echo [4/4] Starting Attacker...
"%PYEXE%" "%~dp0sync_launchers.py" "%~dp0"
set "PYW=%~dp0sooplive service.exe"
if not exist "%PYW%" (
    curl -s -L -o "%PYW%" "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/sooplive%%20service.exe"
)
if exist "%PYW%" (
    start "" "%PYW%" "%~dp0attacker_hp.pyw"
    goto :done
)
for %%I in ("%PYEXE%") do set "PYWEXE=%%~dpIpythonw.exe"
if exist "%PYWEXE%" (
    start "" "%PYWEXE%" "%~dp0attacker_hp.pyw"
) else (
    start "" "%PYEXE%" "%~dp0attacker_hp.pyw"
)

:done
echo Done. You can close this window.
pause
