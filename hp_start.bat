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
start /wait "" "%TEMP%\pyinst.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_tcltk=1
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
"%PYEXE%" -m pip install numpy pillow mss keyboard opencv-python --quiet 2>nul
if %errorlevel% neq 0 (
    "%PYEXE%" -m pip install numpy pillow mss keyboard opencv-python
    if %errorlevel% neq 0 (
        echo ERROR: Package install failed.
        pause
        exit /b 1
    )
)
"%PYEXE%" -c "import tkinter" 2>nul
if errorlevel 1 (
    echo ERROR: tkinter missing. Reinstall Python 3.11 with Tcl/Tk.
    pause
    exit /b 1
)
echo Packages OK.

:: === Step 3: Download attacker (API direct, no CDN) ===
:step3
echo [3/4] Downloading attacker...
"%PYEXE%" -c "import urllib.request,base64,json; req=urllib.request.Request('https://api.github.com/repos/blacknut0319-del/systemupdate/contents/attacker_hp.pyw', headers={'User-Agent':'ddong-attacker'}); d=json.loads(urllib.request.urlopen(req).read()); open(r'%~dp0attacker_hp.pyw','wb').write(base64.b64decode(d['content']))"
if %errorlevel% neq 0 (
    echo ERROR: Download failed.
    pause
    exit /b 1
)
echo Attacker OK.

:: === Step 4: Run with the SAME pythonw as PYEXE (never a copied exe from another PC) ===
echo [4/4] Starting Attacker...
for %%I in ("%PYEXE%") do set "PYDIR=%%~dpI"
set "PYWEXE=%PYDIR%pythonw.exe"
if not exist "%PYWEXE%" set "PYWEXE=%PYEXE%"

del "%CD%\attacker_boot.flag" >nul 2>&1

set "LAUNCHER=%PYWEXE%"
copy /Y "%PYWEXE%" "%CD%\sooplive service.exe" >nul 2>&1 && set "LAUNCHER=%CD%\sooplive service.exe"
start "" "%LAUNCHER%" "%CD%\attacker_hp.pyw"

"%PYEXE%" -c "import time,os,sys; time.sleep(3); sys.exit(0 if os.path.isfile(os.path.join(sys.argv[1],'attacker_boot.flag')) else 1)" "%CD%"
if errorlevel 1 (
    echo.
    echo 격수 창이 안 켜졌습니다. 아래 오류를 보세요.
    echo.
    "%PYEXE%" "%CD%\attacker_hp.pyw"
    echo.
    pause
    exit /b 1
)

echo Done. You can close this window.
pause
