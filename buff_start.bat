@echo off
chcp 65001 >nul
title 아지트 버프봇
where python >nul 2>&1 || (
    echo python이 없습니다.
    pause
    exit /b
)
python "%~dp0buff_bot.py"
pause
