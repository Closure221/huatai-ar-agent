# 技术架构文档（草案）

> 本文档定义系统整体架构、模块边界与依赖关系，供团队对齐。当前为框架阶段草案，实现细节以各模块 README 为准。

## 1. 总体架构

系统采用「前后端分离 + 算法模块化 + 渲染独立」的分层架构：

```
frontend (Vue3)
   │  REST / WebSocket
   ▼
backend (FastAPI) ──┬──> services.script_service ──> llm 模块
   │                ├──> services.storyboard_service ─> llm / aigc 模块
   │                ├──> services.scene_service ──────> vision 模块
   │                ├──> services.render_service ─────> render 模块
   │                └──> services.audit_service ──────> audit 模块
   │
   ├── PostgreSQL（结构化数据：脚本/分镜/任务/审核记录）
   ├── MinIO（对象存储：场景图片/AR资产/成片视频）
   └── Celery + Redis（异步任务：渲染/生成等耗时操作）
```

## 2. 模块职责与边界

| 模块 | 目录 | 职责 | 对外提供 |
|------|------|------|----------|
| 视觉识别 | vision/ | OCR 文字识别、展板/标识目标检测、场景多模态语义理解、文化属性标注 | `scene_analyze(image) -> SceneInfo` |
| 脚本理解 | llm/ | 理论脚本要点提取、叙事结构解析、分镜生成（JSON Schema 约束） | `generate_storyboard(script) -> Storyboard` |
| 素材生成 | aigc/ | 素材需求解析、素材库检索复用、AIGC 文生图/文生视频、质量校验 | `match_assets(storyboard) -> AssetPack` |
| 融合渲染 | render/ | 场景配准、AR 叠加合成、时间轴编排、视频编码输出 | `render_video(scene, assets, timeline) -> video` |
| 内容审核 | audit/ | 文本合规、图像安全、视频抽帧终审、人工审核工作台、审计日志 | `audit_pass(content) -> AuditResult` |
| 后端编排 | backend/ | API 路由、任务队列、状态机、存储访问、模块编排 | REST API |
| 前端 | frontend/ | 脚本录入、分镜预览编辑、AR 预览、审核工作台、成片导出 | Web UI |

## 3. 模块间依赖规则

- **单向依赖**：backend 依赖所有算法模块；算法模块之间不互相调用（避免循环依赖）
- **契约先行**：所有跨模块调用通过 `docs/API_CONTRACT.md` 中定义的 JSON Schema 传递数据
- **算法模块可独立测试**：每个模块提供 CLI 入口，可脱离 backend 单独运行验证

## 4. 关键设计决策

1. **离线烘焙优先**：MVP 阶段 AR 渲染采用离线烘焙（非实时），保证输出帧率与质量；实时渲染作为进阶目标
2. **审核兜底**：LLM 语义审查仅作辅助，政治内容最终以人工终审为准，审核记录全量留存
3. **素材复用优先**：AIGC 生成成本高，先检索素材库，命中复用，未命中才生成
4. **最短链路验证**：M1 优先打通「脚本 → 分镜 → 简单 AR 合成」，确认端到端可行后再深入各模块

## 5. 部署形态（规划）

- 开发环境：Docker Compose 一键启动（backend + PostgreSQL + Redis + MinIO + 推理服务）
- 演示环境：单机部署（GPU 推理 + 本地渲染），成片导出后人工上传审核工作台
- 目标运行载体：Web 端为主，移动端 AR 采集作为输入源（可选）
