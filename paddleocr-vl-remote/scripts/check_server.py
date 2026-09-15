#!/usr/bin/env python3
"""检查 PaddleOCR-VL 远程服务状态。

用法:
    python3 check_server.py [--server URL]

地址读取优先级: --server > 环境变量 PADDLEOCR_VL_URL > config.env > 默认 localhost:8111。
退出码: 0 正常，1 不可达或异常。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://localhost:8111"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.env")


def load_config() -> dict:
    cfg = {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return cfg


def resolve_base(cli_value: str | None) -> str:
    url = cli_value or os.environ.get("PADDLEOCR_VL_URL") or load_config().get("PADDLEOCR_VL_URL")
    if not url:
        return DEFAULT_BASE
    base = url.rstrip("/")
    return base[:-3] if base.endswith("/v1") else base


def get(url: str, timeout: int = 10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", help="服务地址（默认 localhost:8111，可用 PADDLEOCR_VL_URL 覆盖）")
    args = ap.parse_args()
    base = resolve_base(args.server)

    try:
        health = get(f"{base}/health")
    except urllib.error.URLError as e:
        print(f"✗ 服务不可达（{getattr(e, 'reason', e)}）: {base}")
        print("  请先启动: mlx_vlm.server --model PaddlePaddle/PaddleOCR-VL-1.6 --port 8111 --trust-remote-code")
        sys.exit(1)

    print(f"✓ {health.get('status')}  模型: {health.get('loaded_model')}"
          f"  上下文: {health.get('effective_context_limit')}"
          f"  连续批处理: {health.get('continuous_batching_enabled')}")
    try:
        models = get(f"{base}/v1/models")
        ids = [m["id"] for m in models.get("data", [])]
        print(f"✓ 可用模型: {', '.join(ids)}")
    except urllib.error.URLError as e:
        print(f"⚠ /v1/models 异常: {getattr(e, 'reason', e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
