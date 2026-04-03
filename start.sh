#!/usr/bin/env bash
set -e

echo "========================================"
echo "  小爱例行数据整理网页工具 - 一键启动"
echo "========================================"
echo

cd "$(dirname "$0")"

# ---- 检测 Python ----
PYTHON=""
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
fi

if [ -z "$PYTHON" ]; then
    echo "[错误] 未检测到 Python，请先安装 Python 3.13 或以上版本后重试。"
    exit 1
fi

echo "[信息] 检测到 Python：$PYTHON"
$PYTHON --version
echo

# ---- 创建虚拟环境 ----
if [ ! -d ".venv" ]; then
    echo "[信息] 正在创建虚拟环境..."
    $PYTHON -m venv .venv
    echo "[信息] 虚拟环境创建完成。"
else
    echo "[信息] 虚拟环境已存在，跳过创建。"
fi

# ---- 激活虚拟环境 ----
source .venv/bin/activate

# ---- 安装依赖（优先从本地 packages 目录离线安装） ----
echo "[信息] 正在安装依赖..."
if ! pip install --no-index --find-links=packages -r requirements.txt --quiet 2>/dev/null; then
    echo "[信息] 本地离线包不兼容当前环境，正在从网络安装..."
    pip install -r requirements.txt --quiet
fi
echo "[信息] 依赖已就绪。"
echo

# ---- 启动服务 ----
echo "[信息] 正在启动服务..."
echo "[信息] 启动后请在浏览器中访问：http://127.0.0.1:8000"
echo "[信息] 按 Ctrl+C 可停止服务。"
echo "========================================"
echo

# ---- 延迟打开浏览器 ----
(sleep 2 && open http://127.0.0.1:8000 2>/dev/null || xdg-open http://127.0.0.1:8000 2>/dev/null) &

# ---- 启动 Django ----
python manage.py runserver
