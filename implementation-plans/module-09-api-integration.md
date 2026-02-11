# Module 09: REST API 与集成/E2E 测试

## 模块背景

本模块是系统的最终交付层，将核心引擎通过 FastAPI 暴露为 REST API，并完成所有集成测试和端到端测试。同时完善 `main.py` 入口，支持 CLI 和 API 双模式启动。

**在系统中的位置**: API 层 (`gmp/api/`) + 入口 (`gmp/main.py`) + 全量测试

**前置依赖**: Module 01-08 全部完成

## 设计依据

- [05-api.md](../design/05-api.md): 全部 API 定义（viewpoints, forecast, timeline, 错误响应, 枚举值）
- [07-code-interface.md](../design/07-code-interface.md): §7.4 目录结构 — api/ 目录
- [08-operations.md](../design/08-operations.md): §8.1 错误分级, §8.4 日志分级, §8.5 结构化日志
- [09-testing-config.md](../design/09-testing-config.md): §9.3 集成测试, §9.4 Mock 数据

## 待创建文件列表

| 文件 | 说明 |
|------|------|
| `gmp/api/__init__.py` | 包初始化 |
| `gmp/api/routes.py` | FastAPI 路由定义 |
| `gmp/api/schemas.py` | Pydantic 请求/响应模型 |
| `gmp/api/middleware.py` | 错误处理中间件 |
| `gmp/main.py` | 应用入口 (API + CLI) |
| `tests/integration/test_api_endpoints.py` | API 端点测试 |
| `tests/e2e/__init__.py` | E2E 测试包 |
| `tests/e2e/test_full_forecast.py` | 完整 7 天预报 E2E 测试 |

## 代码接口定义

### `gmp/api/routes.py`

```python
from fastapi import FastAPI, Query, Path, HTTPException

app = FastAPI(title="GMP 景观预测引擎", version="1.0.0")

@app.get("/api/v1/viewpoints")
def list_viewpoints(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """获取观景台列表
    
    响应字段: viewpoints[], pagination{page, page_size, total, total_pages}
    """

@app.get("/api/v1/forecast/{viewpoint_id}")
def get_forecast(
    viewpoint_id: str = Path(...),
    days: int = Query(7, ge=1, le=7),
    events: str | None = Query(None),  # 逗号分隔: "cloud_sea,frost"
) -> dict:
    """获取景观预测报告
    
    响应: ForecastReporter 生成的 JSON
    
    错误:
    - 404: ViewpointNotFound
    - 422: InvalidParameter (days > 7)
    - 408: APITimeout (外部 API 超时)
    - 503: ServiceDegraded (使用过期缓存)
    """

@app.get("/api/v1/timeline/{viewpoint_id}")
def get_timeline(
    viewpoint_id: str = Path(...),
    days: int = Query(7, ge=1, le=7),
) -> dict:
    """获取逐小时时间轴数据
    
    响应: TimelineReporter 生成的 JSON
    """
```

### `gmp/api/schemas.py`

```python
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    error: dict = Field(..., example={
        "type": "ViewpointNotFound",
        "message": "未找到观景台: invalid_id",
        "code": 404,
    })

class PaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int

class ViewpointListResponse(BaseModel):
    viewpoints: list[dict]
    pagination: PaginationResponse
```

### `gmp/api/middleware.py`

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from gmp.core.exceptions import GMPError, ViewpointNotFoundError, APITimeoutError

async def gmp_exception_handler(request: Request, exc: GMPError) -> JSONResponse:
    """统一异常处理中间件
    
    映射:
    - ViewpointNotFoundError → 404
    - APITimeoutError → 408
    - InvalidCoordinateError → 422
    - ServiceUnavailableError → 503
    - GMPError (其他) → 500
    """
```

### `gmp/main.py`

```python
import argparse
from gmp.api.routes import app

def main():
    parser = argparse.ArgumentParser(description="GMP 景观预测引擎")
    subparsers = parser.add_subparsers()
    
    # CLI 模式
    cli_parser = subparsers.add_parser("predict")
    cli_parser.add_argument("viewpoint_id")
    cli_parser.add_argument("--days", type=int, default=7)
    cli_parser.add_argument("--events", type=str, default=None)
    cli_parser.add_argument("--no-color", action="store_true")
    
    # API 模式
    api_parser = subparsers.add_parser("serve")
    api_parser.add_argument("--host", default="0.0.0.0")
    api_parser.add_argument("--port", type=int, default=8000)
    
    args = parser.parse_args()
    # ... 处理子命令

if __name__ == "__main__":
    main()
```

## 实现要点

### FastAPI 应用初始化

```python
# routes.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时: 加载配置、初始化数据库、注册 Plugin
    config = load_engine_config("gmp/config/engine_config.yaml")
    viewpoint_config = ViewpointConfig()
    viewpoint_config.load("gmp/config/viewpoints/")
    
    # 初始化 ScoreEngine 并注册所有 Plugin
    score_engine = ScoreEngine()
    score_engine.register(GoldenMountainPlugin("sunrise_golden_mountain"))
    score_engine.register(GoldenMountainPlugin("sunset_golden_mountain"))
    score_engine.register(StargazingPlugin())
    score_engine.register(CloudSeaPlugin())
    score_engine.register(FrostPlugin())
    score_engine.register(SnowTreePlugin())
    score_engine.register(IceIciclePlugin())
    
    # 存储到 app.state
    app.state.scheduler = GMPScheduler(config, viewpoint_config, ...)
    
    yield
    
    # 关闭时: 清理资源

app = FastAPI(lifespan=lifespan)
```

### 错误响应格式

统一使用设计文档 §5.4 定义的格式：

```json
{
  "error": {
    "type": "ViewpointNotFound",
    "message": "未找到观景台: invalid_id",
    "code": 404
  }
}
```

### events 参数解析

```python
events_list = events.split(",") if events else None
# 过滤无效事件类型（忽略不报错）
```

### 降级响应标记

当使用过期缓存数据时，在响应头中添加：
```
X-Data-Freshness: stale
```

### 结构化日志

使用 `structlog` 记录请求级日志：
```python
logger.info("forecast_generated",
    viewpoint="niubei_gongga",
    events_count=4,
    top_score=98,
    duration_ms=1200
)
```

## 测试计划

### 测试操作步骤

```bash
source venv/bin/activate
pip install fastapi uvicorn httpx pytest-asyncio

# API 端点测试
python -m pytest tests/integration/test_api_endpoints.py -v

# E2E 测试
python -m pytest tests/e2e/test_full_forecast.py -v

# 全量测试
python -m pytest tests/ -v --tb=short
```

### 具体测试用例

#### API 端点测试 (使用 FastAPI TestClient)

| 测试函数 | 验证内容 |
|---------|---------|
| `test_list_viewpoints_200` | GET /api/v1/viewpoints → 200, 含分页 |
| `test_list_viewpoints_pagination` | page=2, page_size=1 → 正确分页 |
| `test_forecast_200` | GET /api/v1/forecast/niubei_gongga → 200 |
| `test_forecast_with_events` | ?events=cloud_sea,frost → 仅含指定事件 |
| `test_forecast_404` | /forecast/invalid_id → 404, ViewpointNotFound |
| `test_forecast_422` | ?days=10 → 422 |
| `test_timeline_200` | GET /api/v1/timeline/niubei_gongga → 200 |
| `test_timeline_24hours` | timeline 每天含 24 小时数据 |
| `test_error_format` | 错误响应结构正确 |

#### E2E 测试

| 测试函数 | 验证内容 |
|---------|---------|
| `test_full_7day_forecast` | 完整 7 天预测流程，使用 MockFetcher |
| `test_cli_predict_output` | CLI 模式输出不为空 |
| `test_forecast_timeline_consistency` | forecast 和 timeline 使用同一 DataContext |

## 验收标准

- [ ] 三个 API 端点正确响应
- [ ] 错误处理中间件覆盖所有异常类型
- [ ] events 参数过滤功能正常
- [ ] 分页功能正常
- [ ] CLI 模式可执行预测
- [ ] API 模式可启动服务器
- [ ] 全量测试通过 (单元 + 集成 + E2E)
- [ ] 结构化日志正常输出
