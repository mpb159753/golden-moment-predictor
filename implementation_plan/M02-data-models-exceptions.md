# M02: 核心数据模型与异常定义

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现所有核心 dataclass 数据模型和自定义异常类，它们是所有后续模块的基础依赖。

**依赖模块:** M01 (项目初始化)

---

## 背景

GMP 系统使用大量 dataclass 在模块间传递数据。数据模型分为：
- **领域模型**: `Location`, `Target`, `Viewpoint`, `Route`, `RouteStop` — 描述观景台和线路
- **天文模型**: `SunEvents`, `MoonStatus`, `StargazingWindow` — 天文计算结果
- **评分模型**: `DataRequirement`, `DataContext`, `ScoreResult`, `PipelineResult` — 评分管线
- **异常**: `GMPError` 层次 — 错误处理

所有模型定义参见设计文档 [07-code-interface.md](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/07-code-interface.md)。

---

## Task 1: 核心数据模型 (`gmp/core/models.py`)

**Files:**
- Create: `gmp/core/models.py`
- Test: `tests/unit/test_models.py`

### 要实现的 dataclass

```python
@dataclass
class Location:
    lat: float       # 纬度 WGS84
    lon: float       # 经度 WGS84
    altitude: int    # 海拔 m

@dataclass
class Target:
    name: str
    lat: float
    lon: float
    altitude: int
    weight: str                              # "primary" | "secondary"
    applicable_events: Optional[list[str]]   # None = 自动计算

@dataclass
class Viewpoint:
    id: str
    name: str
    location: Location
    capabilities: list[str]   # ["sunrise", "sunset", "stargazing", ...]
    targets: list[Target]

@dataclass
class RouteStop:
    viewpoint_id: str
    order: int                # 停靠顺序 (1-based)
    stay_note: str = ""

@dataclass
class Route:
    id: str
    name: str
    description: str = ""
    stops: list[RouteStop] = field(default_factory=list)

@dataclass
class SunEvents:
    sunrise: datetime
    sunset: datetime
    sunrise_azimuth: float   # 0-360
    sunset_azimuth: float    # 0-360
    astronomical_dawn: datetime
    astronomical_dusk: datetime

@dataclass
class MoonStatus:
    phase: int               # 0-100
    elevation: float         # degrees, 负 = 地平线下
    moonrise: Optional[datetime]
    moonset: Optional[datetime]

@dataclass
class StargazingWindow:
    optimal_start: Optional[datetime]
    optimal_end: Optional[datetime]
    good_start: Optional[datetime]
    good_end: Optional[datetime]
    quality: str             # "optimal" | "good" | "partial" | "poor"

@dataclass
class ScoreResult:
    event_type: str
    total_score: int         # 0-100
    status: str              # "Perfect" | "Recommended" | "Possible" | "Not Recommended"
    breakdown: dict          # {"dimension": {"score": int, "max": int, "detail": str}}
    time_window: str = ""    # "07:15 - 07:45"
    confidence: str = ""     # "High" | "Medium" | "Low"
    highlights: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    note: str = ""

@dataclass
class PipelineResult:
    viewpoint: Viewpoint
    forecast_days: list[dict]
    meta: dict
```

### status 映射工具函数

```python
def score_to_status(score: int) -> str:
    """根据分数返回状态字符串 — 阈值定义见设计文档 §3.4"""
    if score >= 95:
        return "Perfect"
    elif score >= 80:
        return "Recommended"
    elif score >= 50:
        return "Possible"
    else:
        return "Not Recommended"
```

> **注意**: 上述 status 阈值 (95, 80, 50) 应来自配置文件。实现时 `score_to_status` 应接受一个 `thresholds` 参数（默认使用上述值）。

### confidence 映射工具函数

```python
def days_ahead_to_confidence(days_ahead: int, config: dict | None = None) -> str:
    """根据预测提前天数返回置信度 — 配置见 engine_config.yaml §confidence"""
    # config 默认: {"high": [1, 2], "medium": [3, 4], "low": [5, 16]}
```

### 应测试的内容

- 每个 dataclass 的基本构建与属性访问
- `Location` 坐标边界值（负/0/正）
- `Target.weight` 仅接受 "primary"/"secondary"
- `Viewpoint.capabilities` 为空列表时行为
- `Route.stops` 默认空列表
- `StargazingWindow.quality` 各合法值
- `ScoreResult` 各字段默认值
- `score_to_status` 边界: 0→"Not Recommended", 49→"Not Recommended", 50→"Possible", 79→"Possible", 80→"Recommended", 94→"Recommended", 95→"Perfect", 100→"Perfect"
- `days_ahead_to_confidence` 各区间映射

---

## Task 2: 异常定义 (`gmp/core/exceptions.py`)

**Files:**
- Create: `gmp/core/exceptions.py`
- Test: `tests/unit/test_exceptions.py`

### 要实现的异常类

```python
class GMPError(Exception):
    """基础异常类"""

class APITimeoutError(GMPError):
    def __init__(self, service: str, timeout: int):
        self.service = service
        self.timeout = timeout
        super().__init__(f"{service} API 超时 ({timeout}s)")

class InvalidCoordinateError(GMPError):
    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        super().__init__(f"坐标超出范围: ({lat}, {lon})")

class ViewpointNotFoundError(GMPError):
    def __init__(self, viewpoint_id: str):
        self.viewpoint_id = viewpoint_id
        super().__init__(f"未找到观景台: {viewpoint_id}")

class RouteNotFoundError(GMPError):
    def __init__(self, route_id: str):
        self.route_id = route_id
        super().__init__(f"未找到线路: {route_id}")

class DataDegradedWarning(UserWarning):
    """数据降级警告"""

class InvalidDateError(GMPError):
    def __init__(self, date, reason: str):
        self.date = date
        super().__init__(f"日期无效: {date} ({reason})")

class ServiceUnavailableError(GMPError):
    """外部服务不可用（API 失败且无缓存）"""
```

### 应测试的内容

- 每个异常类可正常抛出和捕获
- `APITimeoutError` 的 `service`/`timeout` 属性
- `InvalidCoordinateError` 的 `lat`/`lon` 属性
- `ViewpointNotFoundError` / `RouteNotFoundError` 的 ID 属性
- 所有自定义异常均为 `GMPError` 子类 (可通过 `except GMPError` 统一捕获)
- `DataDegradedWarning` 是 `UserWarning` 子类 (非 `GMPError`)
- 各异常的 `str()` 输出包含关键信息

---

## 验证命令

```bash
python -m pytest tests/unit/test_models.py tests/unit/test_exceptions.py -v
```
