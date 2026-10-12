---
name: paddleocr-vl-remote
description: >-
  调用自托管的 PaddleOCR-VL 服务（OpenAI 兼容 API，如 mlx_vlm.server / vLLM / SGLang），
  把图片、截图、扫描件、PDF 转成文字（支持中文、英文、表格、公式）；需要保留版面结构时
  用远端解析服务（8112）一条 curl 拿到 Markdown / DOCX / JSON / 版面可视化，零安装。
  当用户要 OCR、提取图片或 PDF 中的文字、截图识字、扫描件转文字、表格识别、公式识别、
  PDF 转 Markdown/Word、完整文档解析、版面还原时使用。
  Trigger: OCR, 文字识别, 图片转文字, 截图识字, 提取图中文字, 扫描件识别, PDF 转文字, PDF 转 Markdown,
  PDF 转 Word, 文档解析, 版面分析, 表格识别, 公式识别, image to text, extract text from image,
  screenshot OCR, table recognition, document parsing, PaddleOCR。
  不用于：询问图片内容/含义（用模型自身视觉能力）；纯文本处理。
metadata:
  version: "1.1"
---

# PaddleOCR-VL 远程识别

通过 OpenAI 兼容 API 调用自托管的 PaddleOCR-VL 文档识别模型
（Apple Silicon GPU 推理，中英文、表格、公式效果强）。纯 HTTP 调用，无需任何云端 token。

- 服务地址：默认 `http://localhost:8111/v1`，可用 `--server` 参数、环境变量 `PADDLEOCR_VL_URL`
  或 skill 目录下 `config.env` 覆盖（优先级依次降低）
- 模型 id：`PaddlePaddle/PaddleOCR-VL-1.6`
- 若服务端设置了 `--api-key`，用 `--api-key` 参数、`PADDLEOCR_VL_API_KEY` 环境变量或 config.env 传入
- 完整文档解析：远端 `http://100.72.227.27:8112/parse`（一条 curl 出 Markdown/DOCX/JSON，零安装，见下方"完整文档解析"）

## 何时使用 / 不使用

**使用**：提取图片/PDF 中的文字、表格内容、公式（LaTeX）；扫描件数字化；截图转文本；
需要完整版面还原（标题层级、阅读顺序、图片定位、Word 输出）→ 见下方"完整文档解析"。

**不使用**：
- 问图片"是什么/画了什么"等视觉问答 → 用模型自身的看图能力

## 第一步：检查服务

```bash
python3 ~/.agents/skills/paddleocr-vl-remote/scripts/check_server.py
```

服务不可达时告知用户：在服务端机器上执行
`mlx_vlm.server --model PaddlePaddle/PaddleOCR-VL-1.6 --port 8111 --trust-remote-code`，
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

当用户要"PDF 转 Markdown/Word"、保留标题层级/阅读顺序/表格结构时，**首选远端解析服务
（8112，零安装）**：版面分析在 Mac mini CPU（PP-DocLayoutV3），识别走 8111 GPU，
一条 curl 上传即可，不用 SSH、不用装 paddleocr、文件用完即删。

```bash
# 默认返回 zip（<原名>.md / .docx / _res.json / _layout_det_res.png）
curl -F "file=@报告.pdf" http://100.72.227.27:8112/parse -o 报告.zip

# 只要某一种格式
curl -F "file=@报告.pdf" "http://100.72.227.27:8112/parse?format=md"   -o 报告.md
curl -F "file=@报告.pdf" "http://100.72.227.27:8112/parse?format=json" -o 报告.json
curl -F "file=@报告.pdf" "http://100.72.227.27:8112/parse?format=docx" -o 报告.docx

# 健康检查（含上游 8111 状态）
curl http://100.72.227.27:8112/health
```

- 前提是 Tailscale 连通；同一局域网可用 `http://192.168.31.14:8112/parse`
- **串行排队**：同一时刻只跑一个请求，其余排队（不会把服务端机器打爆）；上传上限 100MB、单请求超时 30 分钟
- 实测：中英+表格+公式样例图约 9.5 秒；2 页中文 PDF → Markdown 15.2 秒
- 服务端由 launchd 托管，管理命令（在 Mac mini 上）：`./docparse-service.sh status|restart|stop|logs`
- 默认无鉴权（与 8111 一致）；若启用了 `DOCPARSE_API_KEY`，请求加 `-H "X-API-Key: <key>"`

### 备选：本机跑官方管线（8112 不可达 / 需离线处理）

本机一次性安装：

```bash
pip install paddlepaddle==3.2.1 "paddleocr[doc-parser]" python-docx python-pptx pylatexenc
```

之后任意文档：

```bash
paddleocr doc_parser -i 文档.pdf --device cpu --save_path ./out \
  --vl_rec_backend mlx-vlm-server \
  --vl_rec_server_url "$PADDLEOCR_VL_URL" \
  --vl_rec_api_model_name PaddlePaddle/PaddleOCR-VL-1.6
```

输出 `./out/<名>.md / .docx / .json / 版面可视化.png`。

## 故障排查

| 现象 | 原因与处理 |
|---|---|
| Connection refused | 服务没起：服务端重启 `mlx_vlm.server` 后用 check_server.py 确认 |
| HTTP 404 | 服务地址缺 `/v1` 后缀（脚本已强制检查） |
| HTTP 401 | 服务端启用了鉴权，加 `--api-key` |
| 8112 连不上 | 解析服务停了或 Tailscale 断了：先 `curl http://100.72.227.27:8112/health`；Mac mini 上 `./docparse-service.sh status`（launchd KeepAlive 一般会自动拉起） |
| 8112 返回 401 | 服务端开了 `DOCPARSE_API_KEY`，请求加 `-H "X-API-Key: <key>"` |
| 8112 久等不回 | 串行排队中（前面有请求在跑），`/health` 里 `busy:true` 即有人占用，属正常 |
| 结果为空/乱码 | 图片倒置或严重形变；换一张正向扫描图重试 |
| PDF 报错缺 PyMuPDF | `pip install PyMuPDF` |
| 首次请求较慢 | 模型冷启动 + 图大属正常，之后同尺寸图片约 1-2 秒/页 |

## 技术参考

- 接口标准：OpenAI `/v1/chat/completions`；图像只能传 **base64 data URL 或公网 URL**（服务端访问不到本地路径，脚本已处理）
- 服务端就是 `mlx-vlm`（≥0.6.9）自带的 `mlx_vlm.server`；NVIDIA 机器可用 vLLM/SGLang 起同样的 OpenAI 兼容端点
- 常用提问词：`OCR:`（通用）、`Table Recognition:`、`Formula Recognition:`（与官方 doc_parser 管线一致）
- 完整解析链路：`8112 FastAPI`（上传 / 串行排队 / 100MB / 30 分钟超时）→ `paddleocr doc_parser` 版面 **PP-DocLayoutV3**（CPU）→ `8111` MLX 识别（GPU）；两个服务均由 launchd 托管（`com.paddleocr-vl.docparse`，KeepAlive）
- 8112 默认无鉴权，靠 Tailscale ACL 兜底
