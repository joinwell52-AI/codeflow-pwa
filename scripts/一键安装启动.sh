#!/bin/bash
# BridgeFlow 一键安装启动（macOS / Linux）

set -e

echo ""
echo " ╔══════════════════════════════════════════════════╗"
echo " ║          BridgeFlow  一键安装启动                ║"
echo " ║     手机主控台 + PC 执行机 + 文件协作桥接         ║"
echo " ╚══════════════════════════════════════════════════╝"
echo ""

# ── 切换到脚本所在目录 ─────────────────────────────────────────────────────
cd "$(dirname "$0")"

# ── 检查 Python ───────────────────────────────────────────────────────────
echo " [1/3] 检查 Python 环境..."

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; }; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo ""
    echo " ✗ 未检测到 Python 3.10+！"
    echo ""
    echo " macOS 安装方式（推荐 Homebrew）："
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo "   brew install python@3.11"
    echo ""
    echo " 或前往：https://www.python.org/downloads/"
    echo ""
    exit 1
fi

echo " ✓ $($PYTHON --version)"

# ── 安装 / 升级 bridgeflow ────────────────────────────────────────────────
echo ""
echo " [2/3] 安装 BridgeFlow（首次约需 10-30 秒）..."
"$PYTHON" -m pip install --upgrade bridgeflow -q
echo " ✓ BridgeFlow 安装完成"

# ── 启动 BridgeFlow ───────────────────────────────────────────────────────
echo ""
echo " [3/3] 启动 BridgeFlow..."
echo ""
bridgeflow run
