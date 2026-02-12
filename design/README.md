# 川西旅行景观预测引擎 - 系统设计文档

**版本:** v3.1  
**日期:** 2026-02-10  
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
| [05-api.md](./05-api.md) | REST API 接口定义、枚举值 | forecast, timeline, events 过滤 |
| [06-class-sequence.md](./06-class-sequence.md) | 类图、时序图 | UML, 主流程, 评分流程 |
| [07-code-interface.md](./07-code-interface.md) | 代码接口定义 (Protocol)、目录结构 | dataclass, Protocol, 项目结构 |
| [08-operations.md](./08-operations.md) | 错误处理、日志、并发限流 | 降级策略, structlog, Semaphore |
| [09-testing-config.md](./09-testing-config.md) | 测试策略、配置数据、附录 | 测试金字塔, YAML, 依赖 |

## 版本变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v3.1 | 2026-02-12 | 新增线路预测 (Route) 概念：02-data-model Route/RouteStop ER、05-api 线路 API §5.5-5.6、06-class-sequence Route 类图 §6.10 时序图、07-code-interface Route/RouteStop dataclass |
| v3.0 | 2026-02-10 | 架构重构：可插拔 ScorerPlugin 体系、DataContext 数据复用、日照金山解耦云海、文档模块化拆分 |
| v2.0 | 2026-02-10 | 全面重写：章节重组、ER图、评分一致性修复、10点光路、雾凇模型、观星时间逻辑、数值化score_breakdown、API分页、ScoreEngine注册机制 |
| v1.0 | 2026-02-09 | 初版设计文档 |

---

*文档版本: v3.1 | 最后更新: 2026-02-12 | 作者: GMP Team*
