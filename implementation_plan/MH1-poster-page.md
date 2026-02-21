# MH1: 小红书运营海报页面 — 总览

> 本计划已拆分为以下三个独立子计划，按依赖顺序执行：

| 编号 | 计划 | 描述 | 依赖 |
|------|------|------|------|
| MH1A | [Viewpoint 分组配置](./MH1A-viewpoint-groups-config.md) | 删除重复 viewpoint + 新增 `groups` 字段 + 批量更新 48 YAML | 无 |
| MH1B | [海报数据生成器](./MH1B-poster-data-generator.md) | 后端 `poster_generator.py` + `json_file_writer` + `batch_generator` 集成 | MH1A |
| MH1C | [海报前端页面](./MH1C-poster-frontend-page.md) | 前端路由 + `PosterView.vue` + `PredictionMatrix.vue` + 导出 | MH1B |

**设计文档:** [12-poster-page.md](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/12-poster-page.md)

---

*计划版本: v3.0 | 更新: 2026-02-21 | 拆分为三个独立子计划*
