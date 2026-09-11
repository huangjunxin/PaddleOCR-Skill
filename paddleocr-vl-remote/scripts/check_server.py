#!/usr/bin/env python3
"""检查 PaddleOCR-VL 远程服务状态。

用法:
    python3 check_server.py [--server URL]

退出码: 0 正常，1 不可达或异常。
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_SERVER = "http://100.72.227.27:8111"


def get(url: str, timeout: int = 10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=os.environ.get("PADDLEOCR_VL_BASE", DEFAULT_SERVER))
    args = ap.parse_args()
    base = args.server.rstrip("/")

    try:
        health = get(f"{base}/health")
    except urllib.error.URLError as e:
        print(f"✗ 服务不可达（{getattr(e, 'reason', e)}）")
        print("  在 mac-mini 上重启: cd ~/Projects/paddleocr-vl && ./start_server.sh")
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
