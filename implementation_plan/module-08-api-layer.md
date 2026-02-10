# M08 - API 层（FastAPI 路由与错误映射）

## 1. 模块目标

提供标准 REST 接口，将 GMP 能力稳定暴露给客户端：

- `GET /api/v1/viewpoints`
- `GET /api/v1/forecast/{viewpoint_id}`
- `GET /api/v1/timeline/{viewpoint_id}`

---

## 2. 背景上下文

- 参考：`design/05-api.md`
- 关键要求：
  - 参数校验：`days` 范围 1~7，分页上限
  - 错误码映射：404/408/422/503
  - 降级响应头：`X-Data-Freshness: stale`

---

## 3. 交付范围

### 本模块要做

- `gmp/main.py`
- `gmp/api/routes.py`
- `gmp/api/schemas.py`
- `gmp/api/middleware.py`

### 本模块不做

- 不改动评分算法（M05）
- 不重写调度主流程（M06）

---

## 4. 输入与输出契约

### 输入

- URL path/query 参数
- Scheduler/Reporter 的服务对象

### 输出

- 与 API 文档完全一致的 JSON
- 统一错误结构：
  - `{"error":{"type": "...", "message": "...", "code": ...}}`

---

## 5. 实施任务清单

1. 在 `schemas.py` 定义请求参数与响应模型（Pydantic）。
2. 在 `routes.py` 实现 3 个接口：
   - viewpoints 分页
   - forecast（支持 events 过滤）
   - timeline
3. 在 `middleware.py` 建立异常到 HTTP 的映射：
   - `ViewpointNotFoundError -> 404`
   - `APITimeoutError -> 408`
   - 参数错误 -> 422
   - `ServiceUnavailableError -> 503`
4. 在 `main.py` 组装 app、路由与中间件。

---

## 6. 验收标准

1. 路由行为、字段、枚举值符合 `05-api.md`；
2. 非法参数返回 422；
3. 降级场景返回 stale header；
4. OpenAPI 文档可读、示例合理。

---

## 7. 测试清单

- `tests/integration/test_api_endpoints.py`
  - 三个主接口 200 测试
  - 404/422/503 错误分支
  - `events` 过滤行为
- `tests/unit/test_api_middleware.py`
  - 异常映射与响应结构

---

## 8. 新会话启动提示词

```text
请按 gmp_implementation_plan/module-08-api-layer.md 完成 M08：
使用 FastAPI 实现 3 个接口、Pydantic schema 与异常中间件，严格对齐 05-api.md 字段和错误码。
要求：补齐 API 集成测试，覆盖 200/404/422/503 与 events 过滤。
```
