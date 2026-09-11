#!/bin/bash
# 把 paddleocr-vl-remote skill 安装到本机 skills 目录（各 AI agent 共享）
set -e
SRC="$(cd "$(dirname "$0")" && pwd)/paddleocr-vl-remote"
DEST="$HOME/.agents/skills/paddleocr-vl-remote"

rm -rf "$DEST"
cp -R "$SRC" "$DEST"
chmod +x "$DEST"/scripts/*.py
echo "installed: $DEST"
