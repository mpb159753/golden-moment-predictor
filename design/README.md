# 川西旅行景观预测引擎 - 系统设计文档

**版本:** v4.0  
**日期:** 2026-02-12  
**基于:** [需求规格说明书 v0.4](file:///Users/mpb/WorkSpace/my-home-work/旅行预测.md)

---

> **"让每一次川西之行，都不错过自然的馈赠。"**

## 文档索引

| 文档 | 内容 | 关键词 |
|------|------|--------|
| [01-architecture.md](./01-architecture.md) | 产品背景、设计原则、系统架构、数据流、缓存设计 | 整体架构, 懒加载, L1/L2 滤网 |
| [02-data-model.md](./02-data-model.md) | 实体关系、数据库表结构、示例数据 | ER图, SQLite, WeatherCache |
| [03-scoring-plugins.md](./03-scoring-plugins.md) | 可插拔评分器架构、4 个评分器 Plugin 设计 | ScorerPlugin, DataRequirement, DataContext |
| [04-data-flow-example.md](./04-data-flow-example.md) | 牛背山→贡嘎金山完整数据流演示 | Stage 0-6, 评分明细 |
| [05-api.md](./05-api.md) | CLI 命令与 JSON 输出定义、枚举值 | forecast, timeline, events 过滤 |
| [06-class-sequence.md](./06-class-sequence.md) | 类图、时序图 | UML, 主流程, 评分流程 |
| [07-code-interface.md](./07-code-interface.md) | 代码接口定义 (Protocol)、目录结构 | dataclass, Protocol, 项目结构 |
| [08-operations.md](./08-operations.md) | 错误处理、日志、运维配置 | 降级策略, structlog, 定时任务 |
| [09-testing-config.md](./09-testing-config.md) | 测试策略、配置数据、附录 | 测试金字塔, YAML, 依赖 |
| [10-frontend.md](./10-frontend.md) | 前端展示总体需求、三方案并行策略 | Vue 3, 高德地图, 静态托管 |
| [10-frontend-common.md](./10-frontend-common.md) | 前端公共组件、数据加载、配色、路由 | Pinia, ECharts, UnoCSS, 截图 |
| [10-frontend-A-immersive-map.md](./10-frontend-A-immersive-map.md) | 方案A: 沉浸地图、Bottom Sheet、Marker | 全屏地图, flyTo, 懒加载 |
| [10-frontend-B-split-list.md](./10-frontend-B-split-list.md) | 方案B: 分屏浏览、列表地图联动、手风琴 | Split View, 排序筛选, 拖拽 |
| [10-frontend-C-card-flow.md](./10-frontend-C-card-flow.md) | 方案C: 卡片流、3D翻转、Swiper | 大卡片, 背景地图, 分享图 |

## 版本变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v4.0 | 2026-02-12 | 架构统一：status/confidence/JSON 示例全局对齐、清理时序图残留、移除并发及分页 (CLI-only 同步架构)、修复依赖描述、Phase 2 远程数据一次性批量获取、预测天数最大支持 16 天、Plugin 自治安全检查（移除 SafetyFilter）、移除内存缓存层、组合推荐预留给前端、SummaryGenerator 简化为规则模板 |
| v3.2 | 2026-02-12 | 一致性修复：10 处文档间不一致修正、L1 安全过滤改为逐时评估、DataRequirement 增加 past_hours、新增 Backtester 历史校准模块、ConfigManager 统一配置管理器、评分阶梯阈值可配置化 |
| v3.1 | 2026-02-12 | 新增线路预测 (Route) 概念：02-data-model Route/RouteStop ER、05-api 线路 API §5.5-5.6、06-class-sequence Route 类图 §6.10 时序图、07-code-interface Route/RouteStop dataclass |
| v3.0 | 2026-02-10 | 架构重构：可插拔 ScorerPlugin 体系、DataContext 数据复用、日照金山解耦云海、文档模块化拆分 |
| v2.0 | 2026-02-10 | 全面重写：章节重组、ER图、评分一致性修复、10点光路、雾凇模型、观星时间逻辑、数值化score_breakdown、API分页、ScoreEngine注册机制 |
| v1.0 | 2026-02-09 | 初版设计文档 |

---

*文档版本: v4.0 | 最后更新: 2026-02-12 | 作者: GMP Team*
