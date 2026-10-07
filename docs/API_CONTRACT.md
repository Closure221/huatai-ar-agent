# 接口契约（草案）

> 模块间数据交换的 JSON Schema 约定。各模块实现时必须严格遵循，契约变更需团队评审。

## 1. 核心数据结构

### 1.1 分镜（Shot）

```json
{
  "shot_id": "shot_001",
  "index": 1,
  "scene_desc": "镜头画面文字描述：宣讲者在校园宣传栏前讲解",
  "duration_sec": 6,
  "transition": "fade",
  "narration": "本镜头旁白文本",
  "camera": "medium-shot",
  "ar_overlay": {
    "type": "text|image|video|model",
    "content": "AR叠加内容描述或资源引用",
    "position": "center|top-left|...",
    "style": "政治宣讲风|红色主题|极简"
  },
  "asset_requirement": {
    "keywords": ["宣传栏", "红色文化", "理论学习"],
    "style": "写实",
    "size": "1920x1080"
  }
}
```

### 1.2 分镜脚本（Storyboard）

```json
{
  "storyboard_id": "sb_001",
  "script_id": "sc_001",
  "title": "《坚持人民至上》宣讲视频",
  "key_points": ["核心论点1", "关键数据2"],
  "shots": [ "Shot 数组，见 1.1" ],
  "total_duration_sec": 48,
  "generated_by": "llm",
  "created_at": "2026-08-24T09:00:00Z"
}
```

### 1.3 场景信息（SceneInfo）

```json
{
  "scene_id": "scene_001",
  "source_image": "data/scenes/campus_board_01.jpg",
  "ocr_text": "识别出的全部文字（含坐标）",
  "ocr_blocks": [
    { "text": "深入学习党的二十大精神", "bbox": [x1, y1, x2, y2], "confidence": 0.97 }
  ],
  "detected_objects": [
    { "class": "propaganda_board", "confidence": 0.93, "bbox": [...] }
  ],
  "culture_attributes": {
    "theme": "党的二十大精神",
    "category": "政治理论宣传",
    "keywords": ["二十大", "理论", "宣传"]
  },
  "semantic_summary": "多模态模型对场景的自然语言描述",
  "audit_hint": "可选：场景内容初步合规提示"
}
```

### 1.4 素材包（AssetPack）

```json
{
  "asset_pack_id": "ap_001",
  "storyboard_id": "sb_001",
  "items": [
    {
      "shot_index": 1,
      "source": "library|aigc",
      "asset_id": "ast_001",
      "type": "image|video|model|text",
      "path": "data/assets/...",
      "status": "ready|generating|failed",
      "quality_score": 0.85
    }
  ]
}
```

### 1.5 审核结果（AuditResult）

```json
{
  "audit_id": "au_001",
  "target_type": "script|storyboard|asset|video",
  "target_id": "sb_001",
  "auto_check": {
    "sensitive_words": ["命中词列表"],
    "llm_semantic": { "passed": true, "reason": "..." },
    "image_safety": { "passed": true, "risk_score": 0.02 }
  },
  "auto_passed": true,
  "needs_human": false,
  "human_review": null,
  "final_status": "pending|passed|rejected|revised",
  "audit_log": ["操作记录"]
}
```

## 2. 模块间接口清单

| 接口 | 方向 | 输入 | 输出 |
|------|------|------|------|
| `scene_analyze(image)` | vision 对外 | 图片路径/URL | `SceneInfo` |
| `generate_storyboard(script_text)` | llm 对外 | 脚本文本 | `Storyboard` |
| `match_assets(storyboard)` | aigc 对外 | `Storyboard` | `AssetPack` |
| `render_video(scene, asset_pack, storyboard)` | render 对外 | 三者组合 | 成片文件 + 渲染任务状态 |
| `audit(content, target_type)` | audit 对外 | 任意内容 | `AuditResult` |
| `extract_key_points(script_text)` | llm 子能力 | 脚本文本 | 要点列表 |

## 3. REST API（backend 对外，草案）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/scripts | 上传/录入理论脚本 |
| POST | /api/v1/storyboards | 生成分镜（触发 llm） |
| GET  | /api/v1/storyboards/{id} | 获取分镜详情 |
| PUT  | /api/v1/storyboards/{id}/shots/{shot_id} | 人工编辑分镜 |
| POST | /api/v1/scenes/analyze | 上传场景图并识别 |
| POST | /api/v1/render/jobs | 提交渲染任务 |
| GET  | /api/v1/render/jobs/{id} | 查询渲染进度 |
| POST | /api/v1/audit/reviews | 提交人工审核结论 |
| GET  | /api/v1/videos/{id} | 获取成片下载地址 |
