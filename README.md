# PaddleOCR-VL Remote Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

让 AI Agent 随时调用**自托管的 PaddleOCR-VL 文档识别服务**，把图片、截图、扫描件、PDF 转成文字（支持表格结构与公式）。

An [Agent Skill](https://platform.claude.com/docs/zh-CN/agents-and-tools/agent-skills/overview) that connects your AI coding agent (Kimi Code, Claude Code, OpenClaw, …) to a **self-hosted PaddleOCR-VL service** via its OpenAI-compatible API — no cloud token, no per-call cost, data never leaves your network.

## 为什么做这个

PaddleOCR 官方也出了 Agent Skills（`paddleocr-text-recognition` / `paddleocr-doc-parsing`），但它们调用的是 **PaddleOCR 云端 API**，需要申请 token、按量付费。本 skill 对接的是**自己部署的 `mlx_vlm.server`**（OpenAI 兼容接口），适合：

- 已经在本地 / 内网服务器（如 Mac mini）上用 MLX 跑起了 PaddleOCR-VL
- 希望 agent 说句话就能 OCR，而不是每次手写 curl
- 数据不想出网（合同、发票、内部文档）

## 架构

```
你说："识别这张截图" / "把这个 PDF 转出来"
        │
        ▼
Agent 加载 skill（按 SKILL.md 里的触发词自动匹配）
        │
        ▼
scripts/ocr.py ──HTTP POST──▶ mlx_vlm.server :8111/v1/chat/completions
（纯标准库，零依赖）              （OpenAI 兼容，Apple Silicon GPU 推理）
        │                           │
        ◀──── 文字 / 表格 / LaTeX ────┘
```

- 图片走 base64 内联；PDF 由 PyMuPDF 逐页栅格化后逐页识别
- 服务端就是 [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) 自带的 `mlx_vlm.server`，模型 [PaddlePaddle/PaddleOCR-VL-1.6](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6)

## 目录结构

```
paddleocr-vl-remote/
├── SKILL.md                  # skill 主体：触发规则、用法、故障排查
├── config.env.example        # 个人配置模板（复制为 config.env 后填写，不会被 git 跟踪）
└── scripts/
    ├── ocr.py                # 图片/PDF → 文字（含表格、公式、批量、JSON）
    └── check_server.py       # 服务健康检查
install.sh                    # 安装到 ~/.agents/skills/（重复安装保留 config.env）
```

## 安装

```bash
git clone https://github.com/huangjunxin/PaddleOCR-Skill.git
cd PaddleOCR-Skill
./install.sh        # 拷贝到 ~/.agents/skills/paddleocr-vl-remote
```

装好后**新开一个会话**即可被 agent 自动发现和触发。手动安装也可以直接 `cp -R paddleocr-vl-remote ~/.agents/skills/`。

### 配置服务地址

脚本默认连 `localhost:8111`。服务在别的机器上（如局域网服务器、Tailscale 设备）时，
把配置模板复制为 `config.env` 并填写：

```bash
cp ~/.agents/skills/paddleocr-vl-remote/config.env.example ~/.agents/skills/paddleocr-vl-remote/config.env
# 编辑 config.env，例如:
#   PADDLEOCR_VL_URL=http://100.x.x.x:8111/v1
```

优先级：命令行 `--server` > 环境变量 `PADDLEOCR_VL_URL` > `config.env` > 默认 localhost。
`config.env` 已在 .gitignore 中，个人地址/密钥不会误入仓库。

### 前置要求

| 依赖 | 用途 | 说明 |
|---|---|---|
| Python ≥ 3.8 | 运行脚本 | 纯标准库，无需 pip 安装任何东西 |
| PyMuPDF | 识别 PDF 时 | `pip install PyMuPDF`（只识别图片则不需要） |
| 一个运行中的 PaddleOCR-VL 服务 | 提供识别能力 | 见下节 |

### 服务端（一次部署，长期受用）

在装有 Apple Silicon 的机器上（以 Mac mini 为例）：

```bash
pip install "mlx-vlm>=0.6.9"
mlx_vlm.server --model PaddlePaddle/PaddleOCR-VL-1.6 --port 8111 --trust-remote-code
```

跨机器调用配 Tailscale / 内网 / SSH 隧道均可；服务端无鉴权，**仅建议跑在私有网络内**。
NVIDIA GPU 机器可用 vLLM/SGLang 起同样的 OpenAI 兼容服务，本 skill 同样适用（改 `--server` 即可）。

## 使用

### 方式一：让 Agent 自动调用（推荐）

装好后直接用自然语言，例如：

- 「识别这张截图里的文字」
- 「把这个 PDF 的前 5 页转成文本」
- 「提取这个表格的内容」

Agent 会自己跑健康检查、选择参数、回读结果。

### 方式二：命令行手动用

```bash
SKILL=~/.agents/skills/paddleocr-vl-remote/scripts

# 健康检查
python3 $SKILL/check_server.py

# 图片 OCR（单张/多张，中文截图、照片、扫描件均可）
python3 $SKILL/ocr.py 截图.png
python3 $SKILL/ocr.py a.png b.jpg

# 表格 → 结构化单元格（<fcel> 分隔单元格，<nl> 分行）
python3 $SKILL/ocr.py 表格.png --prompt "Table Recognition:"

# 公式 → LaTeX
python3 $SKILL/ocr.py 公式.png --prompt "Formula Recognition:"

# PDF（逐页识别，页间加分隔符；支持页码范围与 DPI）
python3 $SKILL/ocr.py report.pdf
python3 $SKILL/ocr.py report.pdf --pages 1-3,7 --dpi 300 -o report.txt

# 批量 + 结构化输出
python3 $SKILL/ocr.py scan/*.png --json -o result.json
```

### 环境变量

| 变量 | 作用 | 默认值 |
|---|---|---|
| `PADDLEOCR_VL_URL` | 服务地址（**必须以 `/v1` 结尾**） | `http://localhost:8111/v1` |
| `PADDLEOCR_VL_MODEL` | 模型 id | `PaddlePaddle/PaddleOCR-VL-1.6` |
| `PADDLEOCR_VL_API_KEY` | 服务端若加 `--api-key`，此处填密钥 | 空 |

## 输出示例

```text
$ python3 $SKILL/ocr.py invoice.png
深圳市某某科技有限公司
统一社会信用代码: 91440300MA5FXXX23
金额: ¥12,800.00

$ python3 $SKILL/ocr.py price.png --prompt "Table Recognition:"
<fcel>型号<fcel>价格<nl><fcel>Mac mini<fcel>5999元<nl>
```

## 故障排查

| 现象 | 处理 |
|---|---|
| Connection refused | 服务端没起：重启 `mlx_vlm.server`，再用 `check_server.py` 确认 |
| HTTP 404 | 地址缺 `/v1` 后缀 |
| HTTP 401 | 服务端启用了鉴权，设置 `PADDLEOCR_VL_API_KEY` |
| PDF 报缺 PyMuPDF | `pip install PyMuPDF` |
| 结果为空白 | 图片倒置/严重形变，换正向扫描图重试 |
| 公式有微小瑕疵 | 模型特性（偶有上标重复），不影响正文和表格 |

## 相关链接

- [PaddleOCR 官方 Skills](https://github.com/PaddlePaddle/PaddleOCR/tree/main/skills)（云端 API 版）
- [PaddleOCR-VL-1.6 模型](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6)
- [mlx-vlm](https://github.com/Blaizzy/mlx-vlm)

## 贡献

欢迎 Issue 和 PR。修改脚本后请确保 `python3 -m py_compile paddleocr-vl-remote/scripts/*.py` 通过；
SKILL.md 的 `description` 字段是 agent 判断是否触发的唯一依据，改动时注意保留关键词。

## License

[MIT](LICENSE)
