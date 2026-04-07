@echo off
chcp 65001 >nul 2>&1
title 小爱例行数据整理工具

echo ========================================
echo   小爱例行数据整理网页工具 - 一键启动
echo ========================================
echo.

cd /d "%~dp0"

:: ---- 检测 Python ----
set PYTHON=
where py >nul 2>&1 && set PYTHON=py
if not defined PYTHON (
    where python >nul 2>&1 && set PYTHON=python
)
if not defined PYTHON (
    where python3 >nul 2>&1 && set PYTHON=python3
)
if not defined PYTHON (
    echo [错误] 未检测到 Python，请先安装 Python 3.13 或以上版本后重试。
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [信息] 检测到 Python：%PYTHON%
%PYTHON% --version
echo.

:: ---- 尝试创建虚拟环境（失败则跳过，直接用全局 Python） ----
set USE_VENV=0
if exist ".venv\Scripts\activate.bat" (
    set USE_VENV=1
    echo [信息] 虚拟环境已存在。
) else (
    echo [信息] 正在创建虚拟环境...
    %PYTHON% -m venv .venv >nul 2>&1
    if exist ".venv\Scripts\activate.bat" (
        set USE_VENV=1
        echo [信息] 虚拟环境创建完成。
    ) else (
        echo [信息] venv 不可用，将直接使用全局 Python 环境。
    )
)

if "%USE_VENV%"=="1" (
    call .venv\Scripts\activate.bat
)

:: ---- 安装依赖（优先从本地 packages 目录离线安装） ----
echo [信息] 正在安装依赖...
%PYTHON% -m pip install --no-index --find-links=packages -r requirements.txt --quiet 2>nul
if errorlevel 1 (
    echo [信息] 本地离线包不兼容当前环境，正在从网络安装...
    %PYTHON% -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查 Python 版本或网络连接。
        pause
        exit /b 1
    )
)
echo [信息] 依赖已就绪。
echo.

:: ---- 启动服务 ----
echo [信息] 正在启动服务...
echo [信息] 启动后请在浏览器中访问：http://127.0.0.1:8000
echo [信息] 按 Ctrl+C 可停止服务。
echo ========================================
echo.

:: ---- 延迟打开浏览器 ----
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8000"

:: ---- 启动 Django ----
%PYTHON% manage.py runserver
pause
