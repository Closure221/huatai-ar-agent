# 前端（框架占位）

Vue3 + Vite + TypeScript，页面规划：

| 页面 | 路由 | 说明 |
|------|------|------|
| 脚本录入 | /scripts | 上传/粘贴理论脚本 |
| 分镜编辑 | /storyboards/:id | 分镜列表、镜头编辑、AR 标注调整 |
| 场景识别 | /scenes | 上传场景图片，查看识别结果 |
| AR 预览 | /preview/:storyboardId | Three.js AR 叠加预览 |
| 审核工作台 | /audit | 待审列表、批注、结论 |
| 成片管理 | /videos | 成片列表与下载 |

TODO:
- npm create vite@latest frontend -- --template vue-ts
- 安装 axios / pinia / vue-router / three
- 按 docs/API_CONTRACT.md 第 3 节对接 REST API
