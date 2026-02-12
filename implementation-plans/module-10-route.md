# Module 10: 线路预测 Route Forecast

## 模块背景

当前系统以单个观景台 (Viewpoint) 为核心进行预测。实际出行中，用户沿一条线路行驶，需要获取线路级别的汇总预测来规划行程。例如"理小路"包含达尔普、红石滩、雷神瀑布等多个观景点。

本模块引入 **Route（线路）** 概念，通过 RouteStop 引用已有的 Viewpoint，形成 N:M 关系（一条线路包含多个观景台，一个观景台可属于多条线路）。

**在系统中的位置**: 配置层 (`config/routes/`) + 核心模型 (`core/models.py`) + 调度器 (`core/scheduler.py`) + API/CLI

**前置依赖**: Module 01-09 全部完成

## 设计依据

- [02-data-model.md](../design/02-data-model.md): §2.1 ER 图中 Route → RouteStop → Viewpoint 关系
- [05-api.md](../design/05-api.md): §5.5 线路列表 API, §5.6 线路级预测 API
- [06-class-sequence.md](../design/06-class-sequence.md): §6.1 Route/RouteConfig 类图, §6.10 线路预测时序图
- [07-code-interface.md](../design/07-code-interface.md): §7.1 Route/RouteStop dataclass, §7.2 RouteNotFoundError

## 核心设计决策

1. **Route 配置独立管理** — `gmp/config/routes/*.yaml`，不修改 Viewpoint YAML
2. **复用现有引擎** — `run_route()` 内部逐一调用 `self.run()`，无需新的评分/分析逻辑
3. **缓存自然复用** — 相近点位的天气数据按坐标 ROUND(2) 去重，无需额外优化

## 待创建/修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `gmp/core/models.py` | 修改 | 新增 `Route`, `RouteStop` dataclass |
| `gmp/core/exceptions.py` | 修改 | 新增 `RouteNotFoundError` |
| `gmp/core/config_loader.py` | 修改 | 新增 `RouteConfig` 类 |
| `gmp/config/routes/lixiao.yaml` | 新建 | 理小路线路配置 |
| `gmp/core/scheduler.py` | 修改 | 新增 `run_route()` 方法 |
| `gmp/main.py` | 修改 | 新增 `predict-route` 子命令 |
| `gmp/api/routes.py` | 修改 | 新增线路相关 API 端点 |
| `gmp/reporter/forecast_reporter.py` | 修改 | 新增 `generate_route()` 方法 |
| `gmp/reporter/cli_formatter.py` | 修改 | 新增 `generate_route()` 方法 |
| `tests/fixtures/route_lixiao.yaml` | 新建 | 测试用线路 fixture |
| `tests/core/test_route_config.py` | 新建 | RouteConfig 单元测试 |
| `tests/integration/test_route_pipeline.py` | 新建 | 线路预测集成测试 |
| `tests/integration/test_api_endpoints.py` | 修改 | 新增 `TestRouteEndpoints` 测试类 |

## 代码接口定义

### `gmp/core/models.py` — 新增部分

```python
@dataclass
class RouteStop:
    """线路上的一个停靠点"""
    viewpoint_id: str
    order: int               # 停靠顺序 (1-based)
    stay_note: str = ""      # 停留建议

@dataclass
class Route:
    """旅行线路"""
    id: str                  # 如 "lixiao"
    name: str                # 如 "理小路"
    description: str = ""    # 线路简介
    stops: list[RouteStop] = field(default_factory=list)
```

### `gmp/core/config_loader.py` — 新增 RouteConfig

```python
class RouteConfig:
    """线路配置管理器 — 仿照 ViewpointConfig 模式"""
    
    def __init__(self) -> None:
        self._routes: dict[str, Route] = {}
    
    def load(self, config_dir: str | Path) -> None:
        """加载 config_dir/*.yaml 下的所有线路配置
        
        YAML 格式:
            id: lixiao
            name: 理小路
            description: ...
            stops:
              - viewpoint_id: lixiao_daerpu
                order: 1
                stay_note: ...
        """
        config_path = Path(config_dir)
        if not config_path.is_dir():
            return
        for yaml_file in sorted(config_path.glob("*.yaml")):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and "id" in data:
                route = self._parse_route(data)
                self._routes[route.id] = route
    
    def get(self, route_id: str) -> Route:
        """按 ID 获取线路，不存在抛出 RouteNotFoundError"""
        if route_id not in self._routes:
            raise RouteNotFoundError(route_id)
        return self._routes[route_id]
    
    def list_all(self, page: int = 1, page_size: int = 20) -> dict:
        """分页返回线路列表
        
        返回: {"routes": [Route, ...], "pagination": {...}}
        """
        all_routes = list(self._routes.values())
        total = len(all_routes)
        total_pages = max(1, -(-total // page_size))
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "routes": all_routes[start:end],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            }
        }
    
    def _parse_route(self, data: dict) -> Route:
        stops = []
        for s in data.get("stops", []):
            stops.append(RouteStop(
                viewpoint_id=s["viewpoint_id"],
                order=s.get("order", 0),
                stay_note=s.get("stay_note", ""),
            ))
        return Route(
            id=data["id"],
            name=data.get("name", data["id"]),
            description=data.get("description", ""),
            stops=sorted(stops, key=lambda s: s.order),
        )
```

### `gmp/core/scheduler.py` — 新增 run_route()

```python
def run_route(
    self,
    route: Route,
    days: int = 7,
    events: list[str] | None = None,
) -> dict:
    """线路级别预测 — 聚合线路上每个点位的预测结果
    
    流程:
    1. 遍历 route.stops (按 order 排序)
    2. 对每个 stop 调用 self.run(stop.viewpoint_id, days, events)
    3. 汇总 meta 数据 (api_calls, cache_hits)
    
    返回:
        {
            "route": {"id": str, "name": str},
            "stops": [
                {
                    "viewpoint_id": str,
                    "viewpoint_name": str,
                    "order": int,
                    "stay_note": str,
                    "forecast_days": [...],
                }, ...
            ],
            "meta": {"total_api_calls": int, "total_cache_hits": int},
        }
    """
    stops_result = []
    total_api_calls = 0
    total_cache_hits = 0
    
    for stop in route.stops:
        result = self.run(
            viewpoint_id=stop.viewpoint_id,
            days=days,
            events=events,
        )
        stops_result.append({
            "viewpoint_id": stop.viewpoint_id,
            "viewpoint_name": result.get("viewpoint", stop.viewpoint_id),
            "order": stop.order,
            "stay_note": stop.stay_note,
            "forecast_days": result.get("forecast_days", []),
        })
        meta = result.get("meta", {})
        total_api_calls += meta.get("api_calls", 0)
        total_cache_hits += meta.get("cache_hits", 0)
    
    return {
        "route": {"id": route.id, "name": route.name},
        "stops": stops_result,
        "meta": {
            "total_api_calls": total_api_calls,
            "total_cache_hits": total_cache_hits,
        },
    }
```

### `gmp/config/routes/lixiao.yaml`

```yaml
id: lixiao
name: 理小路
description: 理县至小金县经典穿越线路，沿途可赏云海、雾凇、冰挂等高原景观

stops:
  - viewpoint_id: lixiao_daerpu
    order: 1
    stay_note: 高海拔云海观赏点

  - viewpoint_id: lixiao_hongshitan
    order: 2
    stay_note: 红石滩与冰挂观赏

  - viewpoint_id: lixiao_leishen_falls
    order: 3
    stay_note: 雷神瀑布冰挂景观
```

### `gmp/api/routes.py` — 新增端点

```python
@app.get("/api/v1/routes")
def list_routes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """获取线路列表"""
    result = app.state.route_config.list_all(page=page, page_size=page_size)
    return {
        "routes": [_serialize_route(r) for r in result["routes"]],
        "pagination": result["pagination"],
    }

@app.get("/api/v1/route/{route_id}/forecast")
def get_route_forecast(
    route_id: str = Path(..., description="线路 ID"),
    days: int = Query(7, ge=1, le=7),
    events: str | None = Query(None, description="逗号分隔的事件类型过滤"),
) -> dict:
    """获取线路级预测报告"""
    route = app.state.route_config.get(route_id)
    events_list = events.split(",") if events else None
    
    result = app.state.scheduler.run_route(
        route=route,
        days=days,
        events=events_list,
    )
    return app.state.forecast_reporter.generate_route(result)
```

### `gmp/main.py` — 新增 predict-route 子命令

```python
# 子命令: predict-route
route_parser = subparsers.add_parser("predict-route", help="线路级预测")
route_parser.add_argument("route_id", help="线路 ID (如 lixiao)")
route_parser.add_argument("--days", type=int, default=7, help="预测天数")
route_parser.add_argument("--events", type=str, default=None, help="事件类型过滤")
route_parser.add_argument("--no-color", action="store_true", help="禁用彩色输出")
route_parser.set_defaults(func=_run_predict_route)
```

## 实现要点

### 1. run_route() 复用 run()

```python
def run_route(self, route, days, events):
    # 核心: 逐一调用 self.run() 并汇总
    for stop in route.stops:
        result = self.run(stop.viewpoint_id, days, events)
        # 汇总到 stops_result
```

这种方式的优势:
- 零新逻辑 — 不需要新的评分/分析代码
- 缓存自然复用 — `WeatherCache` 按 `ROUND(lat,2), ROUND(lon,2)` 去重
- 错误隔离 — 某个点位失败不影响其他点位

### 2. Route 配置独立存放

```
gmp/config/
├── viewpoints/     ← 不修改
│   ├── lixiao_daerpu.yaml
│   ├── lixiao_hongshitan.yaml
│   └── lixiao_leishen_falls.yaml
└── routes/         ← 新增
    └── lixiao.yaml (引用上面的 viewpoint_id)
```

优势:
- Viewpoint 配置不变 — 向后兼容
- Route 通过 viewpoint_id 引用 — 避免数据冗余
- 新增线路只需创建 YAML — 无需改代码

### 3. 错误处理

- `RouteNotFoundError` → 404（复用现有异常处理中间件模式）
- 某个 stop 的 viewpoint_id 不存在 → `ViewpointNotFoundError` 冒泡到 API，返回 404
- 建议: `RouteConfig.load()` 时 **不** 校验 viewpoint_id 是否存在（延迟到 run_route 时自然校验）

### 4. CLI 输出格式

```
╔══════════════════════════════════════════╗
║  🗺️  理小路 — 线路预测                    ║
╠══════════════════════════════════════════╣
║                                          ║
║  📍 1. 达尔普 (lixiao_daerpu)             ║
║     💡 高海拔云海观赏点                     ║
║  ┌──────────────────────────────────────┐ ║
║  │ [同现有 viewpoint 预测输出格式]       │ ║
║  └──────────────────────────────────────┘ ║
║                                          ║
║  📍 2. 红石滩 (lixiao_hongshitan)         ║
║  ...                                     ║
╚══════════════════════════════════════════╝
```

## 测试计划

### 测试操作步骤

```bash
source venv/bin/activate
python -m pytest tests/core/test_route_config.py tests/integration/test_route_pipeline.py -v
python -m pytest tests/ -v --tb=short  # 全量回归
```

### 具体测试用例

#### 单元测试: `tests/core/test_route_config.py`

| 测试函数 | 验证内容 |
|---------|---------|
| `test_load_route_yaml` | YAML → Route 对象正确映射，stops 按 order 排序 |
| `test_route_not_found` | 不存在的 route_id 抛出 `RouteNotFoundError` |
| `test_route_list_all_pagination` | 分页逻辑正确 |
| `test_load_empty_directory` | 空目录不报错 |
| `test_route_stops_order` | stops 自动按 order 排序 |

#### 集成测试: `tests/integration/test_route_pipeline.py`

| 测试函数 | 验证内容 |
|---------|---------|
| `test_run_route_returns_all_stops` | 返回每个 stop 的预测，stops 数量 == route.stops 数量 |
| `test_run_route_events_filter` | events 过滤传递到各点位 |
| `test_run_route_meta_aggregation` | total_api_calls / total_cache_hits 正确汇总 |
| `test_run_route_stop_order` | 结果按 stop.order 排列 |
| `test_run_route_viewpoint_not_found` | stop 引用不存在的 viewpoint → ViewpointNotFoundError |

#### API 测试: `tests/integration/test_api_endpoints.py` 新增类

| 测试函数 | 验证内容 |
|---------|---------|
| `test_list_routes_200` | GET /api/v1/routes → 200, 含分页 |
| `test_route_forecast_200` | GET /api/v1/route/lixiao/forecast → 200 |
| `test_route_forecast_404` | GET /api/v1/route/invalid/forecast → 404 |
| `test_route_forecast_with_events` | events 过滤正常工作 |

## 验收标准

- [ ] `Route`/`RouteStop` dataclass 可正确创建
- [ ] `RouteConfig` 可加载 YAML、按 ID 查询、分页返回
- [ ] `run_route()` 返回所有 stops 的预测，结构正确
- [ ] `predict-route` CLI 子命令可执行
- [ ] API 端点 `/routes` 和 `/route/{id}/forecast` 正确响应
- [ ] 404 错误正确返回 `RouteNotFound`
- [ ] 现有 Viewpoint 测试全部通过 (无回归)
- [ ] 所有新增测试通过
