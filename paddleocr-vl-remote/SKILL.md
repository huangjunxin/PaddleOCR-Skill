---
name: paddleocr-vl-remote
description: 调用自托管在 mac-mini（Tailscale 100.72.227.27:8111）上的 PaddleOCR-VL 模型服务，把图片、截图、扫描件、PDF 转成文字（支持中文、英文、表格、公式）。当用户要 OCR、提取图片或 PDF 中的文字、截图识字、扫描件转文字、表格识别、公式识别时使用。Trigger: OCR, 文字识别, 图片转文字, 截图识字, 提取图中文字, 扫描件识别, PDF 转文字, 表格识别, 公式识别, image to text, extract text from image, screenshot OCR, table recognition, PaddleOCR。不用于：询问图片内容/含义（用模型自身视觉能力）；需要保留完整版面结构的 Word/Markdown 输出（见"完整文档解析"一节）。
metadata:
  version: "1.0"
---

# PaddleOCR-VL 远程识别

通过 OpenAI 兼容 API 调用自托管在 mac-mini 上的 PaddleOCR-VL-1.6 文档识别模型
（Apple Silicon GPU 推理，中英文、表格、公式效果强）。纯 HTTP 调用，无需任何 API token。

- 服务地址：`http://100.72.227.27:8111/v1`（Tailscale 内网；默认值可用环境变量 `PADDLEOCR_VL_URL` 覆盖）
- 模型 id：`PaddlePaddle/PaddleOCR-VL-1.6`
- 当前无鉴权（服务端如加 `--api-key`，用 `--api-key` 参数或 `PADDLEOCR_VL_API_KEY` 传入）

## 何时使用 / 不使用

**使用**：提取图片/PDF 中的文字、表格内容、公式（LaTeX）；扫描件数字化；截图转文本。

**不使用**：
- 问图片"是什么/画了什么"等视觉问答 → 用模型自身的看图能力
- 需要完整版面还原（标题层级、阅读顺序、图片定位、Word 输出）→ 见下方"完整文档解析"

## 第一步：检查服务

```bash
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/check_server.py
```

服务不可达时告知用户：在 mac-mini 上执行 `cd ~/Projects/paddleocr-vl && ./start_server.sh`，
等待 1-2 分钟后重试。（该服务随终端关闭/机器睡眠会中断，这是最常见故障。）

## 识别图片

```bash
# 单张 / 多张（中文截图、照片、扫描件均可）
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/ocr.py 截图.png
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/ocr.py a.png b.jpg

# 表格 → 结构化单元格（<fcel> 单元格分隔，<nl> 行分隔）
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/ocr.py 表格.png --prompt "Table Recognition:"

# 公式 → LaTeX
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/ocr.py 公式.png --prompt "Formula Recognition:"

# 结果写入文件 / 输出 JSON（多文件批量处理时用）
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/ocr.py scan.png -o result.txt
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/ocr.py *.png --json -o result.json
```

## 识别 PDF

PDF 由脚本用 PyMuPDF 逐页栅格化（本机已装）后逐页识别：

```bash
# 整本 PDF（页间用 ===== 分隔符输出）
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/ocr.py report.pdf

# 指定页码范围
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/ocr.py report.pdf --pages 1-3,7

# 提高扫描件清晰度（默认 200 DPI，模糊老文档可试 300）
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/ocr.py report.pdf --dpi 300 -o report.txt
```

## 结果处理

- 完整展示识别结果，不要截断；超过 1 万字才考虑摘要 + 落盘
- 表格的 `<fcel>/<nl>` 输出可自行转为 Markdown 表格，或改用"完整文档解析"
- 公式输出偶有 LaTeX 上标瑕疵（如 `mc^{2}2`），属模型特性，提示用户即可

## 完整文档解析（Markdown / DOCX 输出）

当用户要"PDF 转 Markdown/Word"、保留标题层级/阅读顺序/表格结构时，用 PaddleOCR
官方管线（版面分析在本机 CPU，识别走 mac-mini GPU）。本机一次性安装：

```bash
pip install paddlepaddle==3.2.1 "paddleocr[doc-parser]" python-docx python-pptx pylatexenc
```

之后任意文档：

```bash
paddleocr doc_parser -i 文档.pdf --device cpu --save_path ./out \
  --vl_rec_backend mlx-vlm-server \
  --vl_rec_server_url http://100.72.227.27:8111/v1 \
  --vl_rec_api_model_name PaddlePaddle/PaddleOCR-VL-1.6
```

输出 `./out/<名>.md / .docx / .json / 版面可视化.png`。

## 故障排查

| 现象 | 原因与处理 |
|---|---|
| Connection refused | 服务没起：mac-mini 跑 `./start_server.sh` 后用 check_server.py 确认 |
| HTTP 404 | 服务地址缺 `/v1` 后缀（脚本已强制检查） |
| HTTP 401 | 服务端启用了鉴权，加 `--api-key` |
| 结果为空/乱码 | 图片倒置或严重形变；换一张正向扫描图重试 |
| PDF 报错缺 PyMuPDF | `pip install PyMuPDF` |
| 首次请求较慢 | 模型冷启动 + 图大属正常，之后同尺寸图片约 1-2 秒/页 |

## 技术参考

- 接口标准：OpenAI `/v1/chat/completions`；图像只能传 **base64 data URL 或公网 URL**（服务端访问不到本地路径，脚本已处理）
- 服务端就是 `mlx_vlm.server`（mlx-vlm ≥0.6.9 自带），部署文档见 mac-mini 项目 `~/Projects/paddleocr-vl/README.md`
- 常用提问词：`OCR:`（通用）、`Table Recognition:`、`Formula Recognition:`（与官方 doc_parser 管线一致）
