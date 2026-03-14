@echo off
title 杀戮尖塔2 存档同步工具启动器
echo 正在检查 Python 环境...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 环境，请先安装 Python！
    pause
    exit /b
)

echo 正在启动工具...
python StS2_Ultimate_Sync.py

if %errorlevel% neq 0 (
    echo [错误] 程序运行出错，请检查路径是否正确。
    pause
)