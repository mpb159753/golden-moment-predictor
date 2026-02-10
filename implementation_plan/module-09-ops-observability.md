# M09 - 运维能力（日志、降级、并发、限流）

## 1. 模块目标

把系统从“能跑”提升到“可观测、可降级、可控并发”：

- 错误分级与降级策略
- 结构化日志
- 并发与限流控制
- 核心指标采集

---

## 2. 背景上下文

- 参考：`design/08-operations.md`
- 关键分级：
  - L0 透明恢复
  - L1 降级响应（stale）
  - L2 部分失败（partial_data）
  - L3 服务不可用（503）

---

## 3. 交付范围

### 本模块要做

- `ops/degradation.py`
- `ops/logging.py`
- `ops/concurrency.py`
- `ops/metrics.py`（可先实现抽象 + 基础实现）

### 本模块不做

- 不重写业务评分逻辑
- 不调整 API schema 字段

---

## 4. 输入与输出契约

### 输入

- Fetcher 异常与缓存可用性
- 配置中的并发上限、超时与重试参数

### 输出

- 降级标记（`Degraded`）与告警日志
- 可被 API/监控采集的指标数据

---

## 5. 实施任务清单

1. `DegradationPolicy`：
   - API timeout 时尝试 stale 缓存
   - 无数据则抛服务不可用异常
2. `Structlog` 配置：
   - 请求级日志
   - Plugin 评分日志
   - 降级告警日志
3. `ConcurrencyControl`：
   - API 并发信号量
   - batch 并发信号量
4. 限流与合并：
   - 光路点坐标去重
   - 批量请求封装 `fetch_multi_points`
5. 指标上报（最小实现）：
   - 耗时、API 调用数、缓存命中率、降级次数

---

## 6. 验收标准

1. 超时场景能优先返回 stale，而非直接失败；
2. 日志具备关键字段（viewpoint/date/plugin/score/api_calls 等）；
3. 并发上限可配置且生效；
4. 指标接口可用于后续接入 Prometheus/OTel。

---

## 7. 测试清单

- `tests/unit/test_degradation_policy.py`
  - stale 命中、无缓存失败
- `tests/unit/test_concurrency.py`
  - 信号量上限生效
- `tests/unit/test_request_coalescer.py`
  - 坐标去重数量正确
- `tests/integration/test_degraded_response.py`
  - API 层返回 `X-Data-Freshness: stale`

---

## 8. 新会话启动提示词

```text
请按 implementation_plan/module-09-ops-observability.md 完成 M09：
实现降级策略、结构化日志、并发控制、请求合并与关键指标统计。
要求：重点验证“API超时+有stale缓存”场景，确保系统降级可用并可观测。
```
