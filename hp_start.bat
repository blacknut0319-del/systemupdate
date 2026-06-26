@echo off
pushd "%~dp0"
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"
title DDONG Attacker

:: === Step 1: Python install ===
echo [1/4] Checking Python...
if exist "C:\Program Files\Python311\python.exe" goto :step2
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" goto :step2

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

set "PATH=C:\Program Files\Python311\Scripts;C:\Program Files\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;%LocalAppData%\Programs\Python\Python311;%PATH%"

if exist "C:\Program Files\Python311\python.exe" goto :step2
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" goto :step2

echo ERROR: Python install failed. Run as Administrator.
pause
exit /b 1

:: === Step 2: Packages ===
:step2
echo [2/4] Installing packages...
python -m pip install --upgrade pip --quiet 2>nul
python -m pip install numpy pillow mss keyboard pywin32 opencv-python dxcam --quiet 2>nul
if %errorlevel% neq 0 (
    python -m pip install numpy pillow mss keyboard pywin32 opencv-python dxcam
    if %errorlevel% neq 0 (
        echo ERROR: Package install failed.
        pause
        exit /b 1
    )
)
echo Packages OK.

:: === Step 3: Download attacker ===
echo [3/4] Downloading attacker...
python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/attacker_hp.pyw?t=%RANDOM%', r'%~dp0attacker_hp.pyw')"
if %errorlevel% neq 0 (
    echo ERROR: Download failed.
    pause
    exit /b 1
)
echo Attacker OK.

:: === Step 4: Run ===
echo [4/4] Starting Attacker...
if exist "C:\Program Files\Python311\pythonw.exe" (
    start "" "C:\Program Files\Python311\pythonw.exe" "%~dp0attacker_hp.pyw"
) else (
    start "" "%LocalAppData%\Programs\Python\Python311\pythonw.exe" "%~dp0attacker_hp.pyw"
)

echo Done. You can close this window.
pause
