# 数据模型（草案）

> 持久化数据设计，对应 PostgreSQL 表 + MinIO 对象存储。当前为框架阶段草案，字段以最终实现为准。

## 1. 实体关系总览

```
Script(理论脚本) 1 ──── n Storyboard(分镜脚本)
Storyboard 1 ──── n Shot(分镜镜头)
Scene(场景) 1 ──── n SceneAnalysis(识别结果)
Shot n ──── m Asset(素材)  ← 通过 AssetPack(素材包) 关联
RenderJob(渲染任务) 1 ──── 1 Video(成片)
任意内容 ──── n AuditRecord(审核记录)
```

## 2. 表设计

### scripts（理论脚本）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| title | varchar | 脚本标题 |
| content | text | 脚本全文 |
| source | varchar | 来源（宣讲稿/政策文件/学习材料） |
| status | varchar | draft / parsed / storyboarded |
| created_at / updated_at | timestamp | |

### storyboards（分镜脚本）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| script_id | UUID FK | 关联 scripts |
| title | varchar | |
| key_points | jsonb | 要点列表 |
| shots | jsonb | 镜头数组（见 API_CONTRACT 1.1） |
| total_duration_sec | int | |
| version | int | 人工编辑后递增 |
| status | varchar | draft / assets_ready / rendered / audited / published |

### scenes（场景）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| source_image | varchar | MinIO 路径 |
| ocr_text | text | 识别全文 |
| detected_objects | jsonb | 检测结果 |
| culture_attributes | jsonb | 文化属性标注 |
| semantic_summary | text | 多模态语义描述 |
| location | varchar | 场景位置（可选） |

### assets（素材）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| type | varchar | image / video / model / text |
| source | varchar | library / aigc |
| path | varchar | MinIO 路径 |
| keywords | jsonb | 检索关键词 |
| style | varchar | 风格标签 |
| quality_score | float | 质量分 |
| status | varchar | ready / generating / failed |
| audit_status | varchar | pending / passed / rejected |

### asset_packs（素材包）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| storyboard_id | UUID FK | |
| items | jsonb | 镜头-素材映射（见 API_CONTRACT 1.4） |

### render_jobs（渲染任务）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| storyboard_id | UUID FK | |
| scene_ids | jsonb | 关联场景 |
| status | varchar | queued / rendering / done / failed |
| progress | float | 0~1 |
| params | jsonb | 渲染参数（分辨率/编码/时长） |
| error | text | 失败原因 |

### videos（成片）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| render_job_id | UUID FK | |
| path | varchar | MinIO 路径 |
| duration_sec | float | |
| resolution | varchar | 1920x1080 等 |
| format | varchar | mp4 / mov |
| audit_status | varchar | pending / passed / rejected |

### audit_records（审核记录，不可篡改）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| target_type | varchar | script / storyboard / asset / video |
| target_id | UUID | |
| auto_check | jsonb | 自动审核明细 |
| human_review | jsonb | 人工结论与批注 |
| final_status | varchar | passed / rejected / revised |
| reviewed_by | varchar | 审核人 |
| reviewed_at | timestamp | |
| audit_log | jsonb | 全量操作记录（追加式） |

## 3. 对象存储（MinIO）桶规划

| Bucket | 用途 | 目录示例 |
|--------|------|----------|
| scenes | 场景原始图片/视频 | campus/board_01.jpg |
| assets | AR 素材库 + AIGC 生成物 | library/xxx.png, aigc/xxx.mp4 |
| outputs | 成片视频 | videos/sb_001.mp4 |
| temp | 中间产物（可清理） | frames/, audio/ |

## 4. 状态机

### Storyboard 生命周期
```
draft → assets_ready → rendered → audited → published
   ↘                    ↗
   revision（人工编辑后回 draft）
```

### RenderJob 生命周期
```
queued → rendering → done
             ↘
            failed → retry
```

### 审核流转
```
auto_check → auto_passed ? published_pending : human_review
human_review → passed → published
             → rejected → 退回 revision
```
