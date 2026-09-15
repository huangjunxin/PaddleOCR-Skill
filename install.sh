#!/bin/bash
# 把 paddleocr-vl-remote skill 安装到本机 skills 目录（各 AI agent 共享）
# 重复安装会保留已有的 config.env 个人配置
set -e
SRC="$(cd "$(dirname "$0")" && pwd)/paddleocr-vl-remote"
DEST="$HOME/.agents/skills/paddleocr-vl-remote"

# 备份已有个人配置
BACKUP=""
if [ -f "$DEST/config.env" ]; then
    BACKUP="$(mktemp)"
    cp "$DEST/config.env" "$BACKUP"
fi

rm -rf "$DEST"
cp -R "$SRC" "$DEST"
chmod +x "$DEST"/scripts/*.py

if [ -n "$BACKUP" ]; then
    cp "$BACKUP" "$DEST/config.env"
    rm -f "$BACKUP"
    echo "config.env 已保留"
fi
echo "installed: $DEST"
echo "首次使用请: cp $DEST/config.env.example $DEST/config.env 并填写你的服务地址"
