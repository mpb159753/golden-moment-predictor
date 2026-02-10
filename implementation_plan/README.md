# GMP 实施计划书（可交接新会话）

## 1. 目标与使用方式

本计划书基于 `design/README.md` 及 01~09 子文档，拆解为 **10 个可独立执行的开发模块**。  
每个模块文档都包含：

- 背景与目标（为什么做）
- 交付范围（做什么、不做什么）
- 输入输出契约（与上下游如何对接）
- 开发任务清单（建议文件级别）
- 测试与验收标准（如何证明完成）
- 可直接复制到新会话的启动提示词

> 适用场景：把某个模块文档单独发给新会话，由新会话直接完成该模块开发与测试。

### 独立执行约定

- 每个模块都按“输入契约 → 输出契约”开发，不依赖会话历史。
- 若前置模块尚未实现，新会话可先按契约创建最小桩（stub）再完成本模块。
- 交付时必须包含本模块测试，确保可独立验证。

---

## 2. 架构目标（实施必须遵守）

1. **Plugin 驱动**：新增景观类型仅需新增 Plugin + 注册，不改 Scheduler/API 主流程。
2. **懒加载**：先 L1 本地过滤，再按触发结果决定是否拉取 L2 远程数据。
3. **数据复用**：通过 `DataContext` 共享本地天气/天文/L2 数据，避免重复请求。
4. **多级缓存**：内存 TTL（5min）→ SQLite TTL（1h）→ 外部 API。
5. **配置驱动**：阈值、权重、并发、分页都从配置读取。
6. **可降级运行**：API 超时时可用 stale 缓存降级返回，并打标记。

---

## 3. 模块拆分总览

| 模块 | 文档 | 主要产出 | 推荐依赖 |
|---|---|---|---|
| M01 | `module-01-foundation.md` | 项目骨架、核心模型、异常、配置加载 | 无 |
| M02 | `module-02-data-cache-fetcher.md` | SQLite/内存缓存、天气拉取器 | M01 |
| M03 | `module-03-astro-geo.md` | 天文与地理计算能力 | M01 |
| M04 | `module-04-analyzer-plugin-kernel.md` | 分析器、Plugin 契约、注册中心 | M01 |
| M05 | `module-05-builtin-plugins.md` | 4 个内置评分 Plugin | M04 |
| M06 | `module-06-scheduler-pipeline.md` |构建 GMP 的最小可运行基础层lyScheduler 与主流水线 | M02~M05 |
| M07 | `module-07-reporters-summary.md` | Forecast/Timeline 输出层 | M06 |
| M08 | `module-08-api-layer.md` | FastAPI 路由、Schema、中间件 | M06~M07 |
| M09 | `module-09-ops-observability.md` | 日志、降级、并发、限流、指标 | M02、M06、M08 |
| M10 | `module-10-testing-fixtures.md` | 测试基建、fixtures、集成/E2E 用例 | M01~M09 |

---

## 4. 推荐执行节奏（兼顾并行与上下文）

- **Wave A（先打底）**：M01
- **Wave B（可并行）**：M02、M03、M04
- **Wave C（能力落地）**：M05、M06
- **Wave D（对外能力）**：M07、M08
-提供标准 REST 接口，将 GMP 能力稳定暴露给客户端：M09、M10

---

## 5. 全局交付标准（DoD）

每个模块都应满足：

1. 代码实现与模块文档约定一致；
2. 模块级单测/集成测试可执行并通过；
3. 输出与接口字段遵循 `design/05-api.md`；
4. 不破坏 Plugin 可扩展性；
5. 关键参数来自配置，不硬编码在业务逻辑中。

---

## 6. 模块文档清单

- `implementation_plan/module-01-foundation.md`
- `implementation_plan/module-02-data-cache-fetcher.md`
- `implementation_plan/module-03-astro-geo.md`
- `implementation_plan/module-04-analyzer-plugin-kernel.md`
- `implementation_plan/module-05-builtin-plugins.md`
- `implementation_plan/module-06-scheduler-pipeline.md`
- `implementation_plan/module-07-reporters-summary.md`
- `implementation_plan/module-08-api-layer.md`
- `implementation_plan/module-09-ops-observability.md`
- `implementation_plan/module-10-testing-fixtures.md`
