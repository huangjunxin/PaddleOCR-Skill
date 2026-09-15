#!/usr/bin/env python3
"""调用自托管 PaddleOCR-VL 服务（OpenAI 兼容 API）识别图片 / PDF。

用法:
    python3 ocr.py 文件 [文件...] [--prompt OCR:] [--pages 1-3,5] [--dpi 200]
                   [--server URL] [--model NAME] [--api-key KEY] [--json] [-o 输出文件]

支持的输入: png / jpg / jpeg / webp / bmp / gif / tif / tiff / pdf
PDF 需要 PyMuPDF（本机已装；缺失时按报错提示 pip install PyMuPDF）。

环境变量（可选，用于覆盖默认值）:
    PADDLEOCR_VL_URL      服务地址，必须以 /v1 结尾
    PADDLEOCR_VL_MODEL    模型 id
    PADDLEOCR_VL_API_KEY  若服务端启动时加了 --api-key，这里填同名密钥
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_SERVER = "http://localhost:8111/v1"
DEFAULT_MODEL = "PaddlePaddle/PaddleOCR-VL-1.6"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.env")


def load_config() -> dict:
    """读取 skill 目录下的 config.env（KEY=VALUE，# 开头为注释）。文件不存在返回空。"""
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


_CONFIG = load_config()


def conf(env_name: str, default: str) -> str:
    """优先级: 命令行 > 环境变量 > config.env > 内置默认值。

     argparse 的 default 在解析前求值，命令行传入后仍会覆盖，故天然满足该顺序。
    """
    return os.environ.get(env_name) or _CONFIG.get(env_name) or default


def parse_pages(spec: str, total: int) -> list[int]:
    """把 "1-3,5" 解析成 [1,2,3,5]（1-based），并裁到文档页数范围内。"""
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            pages.update(range(int(a), int(b) + 1))
        else:
            pages.add(int(part))
    return sorted(p for p in pages if 1 <= p <= total)


def load_pages(path: str, dpi: int, pages_spec: str | None):
    """返回 [(页码或None, mime, base64)] 列表。图片为单页，PDF 逐页栅格化。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTS:
        mime = mimetypes.guess_type(path)[0] or "image/png"
        return [(None, mime, base64.b64encode(open(path, "rb").read()).decode())]
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
        except ImportError:
            sys.exit("PDF 需要 PyMuPDF：pip install PyMuPDF")
        doc = fitz.open(path)
        total = doc.page_count
        if total == 0:
            sys.exit(f"{path}: 空 PDF")
        wanted = parse_pages(pages_spec, total) if pages_spec else list(range(1, total + 1))
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        out = []
        for pno in wanted:
            pix = doc.load_page(pno - 1).get_pixmap(matrix=mat, alpha=False)
            out.append((pno, "image/png", base64.b64encode(pix.tobytes("png")).decode()))
        doc.close()
        return out
    sys.exit(f"不支持的文件类型: {ext}（支持 {sorted(IMAGE_EXTS)} 和 .pdf）")


def ocr_one(server: str, model: str, api_key: str | None, prompt: str,
            mime: str, b64: str, timeout: int) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        "temperature": 0,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    url = server.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    return resp["choices"][0]["message"]["content"]


def main() -> None:
    ap = argparse.ArgumentParser(description="PaddleOCR-VL 远程识别")
    ap.add_argument("files", nargs="+", help="图片或 PDF 路径")
    ap.add_argument("--prompt", default="OCR:",
                    help="提问词，默认 OCR:；表格用 'Table Recognition:'，公式用 'Formula Recognition:'")
    ap.add_argument("--pages", help="PDF 页码范围，如 1-3,5（默认全部）")
    ap.add_argument("--dpi", type=int, default=200, help="PDF 栅格化 DPI（默认 200）")
    ap.add_argument("--server", default=conf("PADDLEOCR_VL_URL", DEFAULT_SERVER),
                    help=f"服务地址，须以 /v1 结尾（默认 {DEFAULT_SERVER}，可用环境变量或 config.env 覆盖）")
    ap.add_argument("--model", default=conf("PADDLEOCR_VL_MODEL", DEFAULT_MODEL))
    ap.add_argument("--api-key", default=conf("PADDLEOCR_VL_API_KEY", ""))
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结构化结果")
    ap.add_argument("-o", "--output", help="把结果写入文件（utf-8）")
    args = ap.parse_args()

    if not args.server.rstrip("/").endswith("/v1"):
        sys.exit(f"--server 必须以 /v1 结尾: {args.server}")

    results = []  # (file, page|None, text, seconds)
    for path in args.files:
        pages = load_pages(path, args.dpi, args.pages)
        for pno, mime, b64 in pages:
            t0 = time.time()
            try:
                text = ocr_one(args.server, args.model, args.api_key,
                               args.prompt, mime, b64, args.timeout)
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")[:300]
                sys.exit(f"HTTP {e.code}: {body}\n"
                         f"（404 检查地址是否以 /v1 结尾；401 检查 --api-key）")
            except urllib.error.URLError as e:
                reason = getattr(e, "reason", e)
                sys.exit(f"连不上模型服务（{reason}）。请在服务端重启 mlx_vlm.server 后确认:\n"
                         f"  curl {args.server.rstrip('/')[:-2]}/health")
            results.append((path, pno, text, time.time() - t0))

    multi = len(results) > 1
    if args.json:
        out = json.dumps([
            {"file": f, "page": p, "seconds": round(s, 1), "text": t}
            for f, p, t, s in results
        ], ensure_ascii=False, indent=2)
    else:
        chunks = []
        for f, p, t, s in results:
            label = f if p is None else f"{f} · 第{p}页"
            header = f"===== {label} ({s:.1f}s) =====\n" if multi else ""
            chunks.append(header + t)
        out = "\n\n".join(chunks)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fp:
            fp.write(out + "\n")
        print(f"已写入 {args.output}", file=sys.stderr)
    print(out)


if __name__ == "__main__":
    main()
