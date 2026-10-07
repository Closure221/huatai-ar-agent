# 华泰杯 · AR 视觉识别智能体（huatai-ar-agent）

> 面向政治理论学习和可视化传播场景，以计算机视觉为核心技术，实现「理论脚本输入 → AR 视频成片输出」的自动化流程。
> 人工智能创新实践大赛 · 校园生活赛道 · 命题一「AR 视频创作智能体」参赛作品。
>
> 开源许可：MIT（见 [LICENSE](LICENSE)）。仓库只含源码与文档，模型权重、运行数据（`data/`、`backend/data/`）不在版本库内。

## 项目定位

- 识别校园宣传栏、理论学习展板、红色文化阵地等场景中的文字与图像信息，完成场景政治文化属性智能解析
- 大语言模型对理论脚本进行要点提取与分镜生成，结合 AIGC 自动匹配 AR 素材
- 虚拟 AR 内容与真实校园场景融合渲染与视频合成
- 内置审核机制，确保内容准确、安全、合规

## 核心 Pipeline

```
脚本输入 → LLM要点提取/分镜生成 → 场景识别(OCR) → AR素材匹配/生成 → 视频合成(AI配音) → 内容审核
```

## 功能特性

| 模块 | 技术实现 | 说明 |
|---|---|---|
| 脚本管理 | FastAPI + SQLite | 录入/查看理论宣讲脚本，自动记录状态 |
| 文案扩写（v2） | 本地 Qwen2.5-0.5B + 规则兜底 | AI 扩写/润色/提取要点，三种篇幅可选 |
| 场景识别 | RapidOCR（中文） | 上传校园宣传栏/展板照片，OCR + 政治主题/场景类别自动标注 |
| 内置图库（v2） | 程序化生成 6 张示例场景图 | 无需上传即可一键选用测试（data/gallery） |
| 分镜生成 | 本地 Qwen2.5-0.5B-Instruct（CPU 推理）+ 规则兜底 | 3-8 镜头可自定义，镜头数自动对齐 |
| AR 素材（v2） | PIL 高清 2x 绘制 | 卡片/横幅/图表/徽章/印章/飘带/光效，按主题配色 |
| 视频合成（v4·PPT） | imageio-ffmpeg H.264 + OpenCV 兜底 | 每镜头一页 PPT：顶部标题栏/中部素材大图区/底部字幕条；字幕在底下、画面提亮、淡入淡出翻页 |
| AI 配音（v2） | edge-tts + imageio-ffmpeg | 6 种音色可选、语速 -20%~+50% 可调、自动重试、离线降级 |
| 音画同步（v4） | 逐镜头 TTS + 时长按字数估计(4.5字/s) + adelay 对齐 | 每镜时长≈旁白朗读时长，语音不重叠、音画同步 |
| 素材池+自动配图（v4） | 用户多图上传 + 16 张主题网图 + loremflickr 按需下载 | 每镜自动配不同图（用户素材优先→图库→网图），不再一图到底；前端可手动挑 |
| 内容审核 | 敏感词规则 + LLM 语义复核 | 输出审核记录；最终政治责任由人工终审兜底 |

## 环境要求

- **Windows 10/11**
- **Python 3.12**（rapidocr-onnxruntime 最高支持 3.12，勿用 3.13）
- 联网（首次装依赖 + edge-tts 配音时使用；其余全部本地推理）
- 本地模型：Qwen2.5-0.5B-Instruct（约 1GB）。**仓库不含模型权重**，首次运行前执行 `python backend/download_model.py` 从 ModelScope 拉取到 `backend/data/models/`；未下载时自动降级为规则兜底，功能仍可用

## 安装（首次）

```bat
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\pip install -r requirements.txt
```

> 说明：`torch` 单独从 PyTorch CPU 源安装，避免默认源拉取超大 CUDA 版；`requirements.txt` 与代码 import 一一对应。

首次运行前下载本地模型（约 1GB，可选但推荐；不下载则分镜/扩写走规则兜底）：

```bat
.venv\Scripts\python backend\download_model.py
```

## 启动

```bat
start.bat
```

脚本会自动检测并优先使用 `.venv`，随后：
1. 后台启动后端服务 `http://127.0.0.1:8000`
2. 自动打开浏览器访问前端页面

（手动方式：`cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`）

## 使用流程（Web 操作）

1. **输入脚本**：粘贴宣讲稿（或只写要点）→ 可点「✨ AI 扩写」自动展开成完整宣讲稿 → 保存
2. **智能分镜**：自动生成 3-8 个镜头卡片，镜头数量可自定义
3. **选择场景**：「内置图库」一键选用 6 张示例场景图，或上传自己的展板照片，自动 OCR + 文化属性识别
4. **自定义设置**：分辨率(720p/1080p)、帧率、画质、字幕开关、配音音色(6 种)、语速，自动记忆
5. **合成交付**：一键生成高清 AR 成片（H.264 + AI 配音），预览/下载 + 内容审核记录

## API 一览（前缀 /api/v1）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST / GET | `/scripts` | 创建 / 列表脚本 |
| POST | `/scripts/expand` | AI 扩写 / 润色 / 提取要点（v2） |
| POST / GET | `/storyboards` | 生成 / 列表分镜 |
| POST / GET | `/scenes/analyze`, `/scenes` | 上传场景图识别 / 场景列表 |
| POST / GET | `/videos`, `/videos/{id}` | 合成视频 / 查询状态 |
| GET | `/videos/{id}/download` | 下载成片 |
| POST / GET | `/audits` | 内容审核 / 审核记录 |

## 测试

- 一键自测：`python scripts/smoke_test.py`（自动走通「脚本→分镜→场景→视频」全链路，生成实测成片）
- 详细用例集见 `docs/测试用例集.md`（覆盖正常/异常/边界 ≥ 12 条）

## 常见问题

1. **分镜一直不生成 / 质量低**：检查 `backend/data/models` 下 Qwen 模型是否完整；模型加载自动探测多个候选目录并在失败时降级「规则兜底」。
2. **合成视频失败**：页面上会直接显示失败原因（如 `error` 字段）。常见：edge-tts 联网不可用 → 自动返回无配音成片；场景图损坏/过大（>10MB 被拒）。
3. **配音无声**：edge-tts 需联网；离线时自动降级，不阻塞出片。
4. **`rapidocr` 装不上**：确认使用 Python 3.12（3.13 无对应 wheel）。
5. **模型被识别成本地路径**：模型路径通过 `qwen_path.txt` + 多候选目录自动探测，项目整体移动后无需手动改配置。

## 目录结构

```
huatai-ar-agent/
├── backend/
│   ├── app/
│   │   ├── core/config.py      # 路径配置（所有路径相对项目根）
│   │   ├── db.py               # SQLite 存储（脚本/分镜/场景/视频/审核）
│   │   ├── modules/            # 核心算法模块
│   │   │   ├── vision.py       # 场景识别（OCR + 文化属性标注）
│   │   │   ├── storyboard.py   # LLM 分镜 + 规则兜底
│   │   │   ├── assets.py       # AR 素材生成（PIL）
│   │   │   ├── video.py        # 视频合成（OpenCV）
│   │   │   ├── audio.py        # AI 配音混流（edge-tts + ffmpeg）
│   │   │   └── audit.py        # 内容审核
│   │   └── routers/            # scripts/storyboards/scenes/videos/audits
│   └── data/models/            # Qwen2.5-0.5B 本地模型
├── frontend/web/index.html     # 单页前端（免构建）
├── docs/                       # 技术文档、测试用例集、合规说明
├── scripts/                    # 一键自测脚本
├── data/                       # uploads / assets / outputs / models（运行数据）
├── requirements.txt            # 运行依赖（已与代码对齐）
└── start.bat                   # 一键启动
```

## 赛事交付文档（2026-08 评审版）

| 文档 | 说明 |
|---|---|
| 项目说明文档_华泰杯AR视觉识别智能体.docx / .pdf | 参赛项目说明（技术文档，十二节） |
| docs/测试用例集.md | 33 条用例（正常/异常/边界），28 条实测通过 |
| 审查与修复总结报告.md | 本轮审查 12 项缺陷的修复记录与验证 |
| docs/合规说明.md | 数据/隐私/内容安全/版权/网络依赖合规 |

> 本轮为 v2.0：修复 12 项缺陷、重建 Python3.12 运行环境、补齐全套赛事文档。

## 合规与安全

参见 `docs/合规说明.md`。要点：数据本地处理、不采集个人身份信息、内容审核 + 人工终审兜底、模型权重本地使用。
