# Module 01: 项目基础框架

## 模块背景

本模块是整个 GMP（Golden Moment Predictor，川西旅行景观预测引擎）系统的基石。所有后续模块都依赖此模块提供的数据结构、异常类和配置加载功能。

**在系统中的位置**: 核心层 (`gmp/core/`) — 定义了系统的"词汇表"和"骨架"。

## 设计依据

- [07-code-interface.md](../design/07-code-interface.md): §7.1 核心接口, §7.2 异常定义, §7.3 配置接口, §7.4 目录结构
- [02-data-model.md](../design/02-data-model.md): §2.1 实体关系图
- [09-testing-config.md](../design/09-testing-config.md): §9.5 引擎配置, §9.6 观景台配置

## 待创建文件列表

### 项目根文件

| 文件 | 说明 |
|------|------|
| `gmp/__init__.py` | 包初始化，导出版本号 |
| `gmp/main.py` | 应用入口占位（后续模块填充） |
| `requirements.txt` | Python 依赖声明 |
| `pyproject.toml` | 项目元数据（若使用） |

### 核心模块 `gmp/core/`

| 文件 | 说明 |
|------|------|
| `gmp/core/__init__.py` | 包初始化 |
| `gmp/core/models.py` | 核心数据模型 dataclass |
| `gmp/core/exceptions.py` | 异常层级定义 |
| `gmp/core/config_loader.py` | 配置加载器（YAML → dataclass） |

### 配置文件 `gmp/config/`

| 文件 | 说明 |
|------|------|
| `gmp/config/engine_config.yaml` | 引擎全局配置 |
| `gmp/config/viewpoints/niubei_gongga.yaml` | 牛背山观景台配置（示例） |

### 测试文件

| 文件 | 说明 |
|------|------|
| `tests/__init__.py` | 测试包 |
| `tests/core/__init__.py` | 核心测试包 |
| `tests/core/test_models.py` | 数据模型测试 |
| `tests/core/test_exceptions.py` | 异常类测试 |
| `tests/core/test_config_loader.py` | 配置加载测试 |
| `tests/fixtures/viewpoint_niubei.yaml` | 测试用观景台配置 |

## 代码接口定义

### `gmp/core/models.py` — 核心数据模型

```python
from dataclasses import dataclass, field
from typing import Optional
from datetime import date, datetime

@dataclass
class Location:
    lat: float       # 纬度 WGS84
    lon: float       # 经度 WGS84
    altitude: int    # 海拔 (m)

@dataclass
class Target:
    name: str
    lat: float
    lon: float
    altitude: int
    weight: str  # "primary" | "secondary"
    applicable_events: Optional[list[str]] = None  # None = 自动计算

@dataclass
class Viewpoint:
    id: str
    name: str
    location: Location
    capabilities: list[str]  # ["sunrise", "sunset", "stargazing", "cloud_sea", "frost", "snow_tree", "ice_icicle"]
    targets: list[Target]

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
    phase: int                       # 0-100
    elevation: float                 # degrees
    moonrise: Optional[datetime]
    moonset: Optional[datetime]

@dataclass
class StargazingWindow:
    optimal_start: Optional[datetime]
    optimal_end: Optional[datetime]
    good_start: Optional[datetime]
    good_end: Optional[datetime]
    quality: str  # "optimal" | "good" | "partial" | "poor"

@dataclass
class AnalysisResult:
    passed: bool
    score: int          # 0-100
    reason: str
    details: dict

@dataclass
class ScoreResult:
    total_score: int
    status: str         # "Perfect" | "Recommended" | "Possible" | "Not Recommended"
    breakdown: dict     # {"dimension": {"score": int, "max": int, "detail": str}}

@dataclass
class DataRequirement:
    needs_l2_target: bool = False
    needs_l2_light_path: bool = False
    needs_astro: bool = False
    season_months: list[int] | None = None

@dataclass
class DataContext:
    """共享数据上下文 — 所有 Plugin 复用"""
    date: date
    viewpoint: Viewpoint
    local_weather: "pd.DataFrame"
    sun_events: SunEvents | None = None
    moon_status: MoonStatus | None = None
    stargazing_window: StargazingWindow | None = None
    target_weather: "dict[str, pd.DataFrame] | None" = None
    light_path_weather: "list[dict] | None" = None
    l2_result: AnalysisResult | None = None
```

> **注意**: `DataContext` 中 `pd.DataFrame` 使用前向引用字符串，避免强制导入 pandas。

### `gmp/core/exceptions.py` — 异常定义

```python
class GMPError(Exception):
    """基础异常类"""
    pass

class APITimeoutError(GMPError):
    def __init__(self, service: str, timeout: int):
        self.service = service
        self.timeout = timeout
        super().__init__(f"{service} API 超时 ({timeout}s)")

class InvalidCoordinateError(GMPError):
    def __init__(self, lat: float, lon: float):
        super().__init__(f"坐标超出范围: ({lat}, {lon})")

class ViewpointNotFoundError(GMPError):
    def __init__(self, viewpoint_id: str):
        self.viewpoint_id = viewpoint_id
        super().__init__(f"未找到观景台: {viewpoint_id}")

class DataDegradedWarning(UserWarning):
    pass
```

### `gmp/core/config_loader.py` — 配置加载器

```python
@dataclass
class EngineConfig:
    db_path: str = "gmp_cache.db"
    memory_cache_ttl_seconds: int = 300
    db_cache_ttl_seconds: int = 3600
    coord_precision: int = 2
    precip_threshold: float = 50.0
    visibility_threshold: float = 1000
    # ... (完整字段见设计文档 §7.3)

class ViewpointConfig:
    """观景台配置管理器"""
    
    def load(self, config_dir: str) -> None:
        """加载 config/viewpoints/*.yaml 目录下所有观景台"""
    
    def get(self, viewpoint_id: str) -> Viewpoint:
        """按 ID 获取观景台，不存在则抛出 ViewpointNotFoundError"""
    
    def list_all(self, page: int = 1, page_size: int = 20) -> dict:
        """分页返回观景台列表"""
```

### `gmp/config/engine_config.yaml`

完整内容参见设计文档 `09-testing-config.md` §9.5，关键节选：

```yaml
cache:
  memory_ttl_seconds: 300
  db_ttl_seconds: 3600
  db_path: "db/gmp_cache.db"
coord_precision: 2
thresholds:
  precip_probability: 50
  visibility_min: 1000
  # ...
scoring:
  golden_mountain:
    light_path: 35
    target_visible: 40
    local_clear: 25
  # ...
```

### `gmp/config/viewpoints/niubei_gongga.yaml`

```yaml
id: niubei_gongga
name: 牛背山
location:
  lat: 29.75
  lon: 102.35
  altitude: 3660
capabilities:
  - sunrise
  - sunset
  - stargazing
  - cloud_sea
  - frost
  - snow_tree
  - ice_icicle
targets:
  - name: 贡嘎主峰
    lat: 29.58
    lon: 101.88
    altitude: 7556
    weight: primary
    applicable_events: null
  - name: 雅拉神山
    lat: 30.15
    lon: 101.75
    altitude: 5820
    weight: secondary
    applicable_events:
      - sunset
```

## 实现要点

1. **`ViewpointConfig.load()`**: 使用 `pathlib.Path.glob("*.yaml")` 遍历配置目录，`yaml.safe_load()` 解析每个文件
2. **`EngineConfig`**: 从 `engine_config.yaml` 加载，未指定字段使用 dataclass 默认值
3. **`models.py`**: 纯 dataclass，不包含业务逻辑；`DataContext` 中 pandas 相关字段使用延迟导入
4. **分页**: `list_all()` 返回 `{"viewpoints": [...], "pagination": {"page": int, "total": int, ...}}`
5. **`requirements.txt`**: 初始依赖 `pyyaml>=6.0`, `pandas>=2.0`, `pytest>=7.0`

## 测试计划

### 测试操作步骤

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt
pip install pytest

# 3. 运行测试
python -m pytest tests/core/ -v
```

### 具体测试用例

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `test_models.py` | `test_location_creation` | Location 正确创建 |
| `test_models.py` | `test_viewpoint_with_targets` | Viewpoint 包含 Target 列表 |
| `test_models.py` | `test_score_result_status` | ScoreResult 状态字符串正确 |
| `test_models.py` | `test_data_requirement_defaults` | DataRequirement 默认值全 False/None |
| `test_exceptions.py` | `test_gmp_error_hierarchy` | 所有异常继承 GMPError |
| `test_exceptions.py` | `test_api_timeout_message` | APITimeoutError 消息格式正确 |
| `test_exceptions.py` | `test_viewpoint_not_found` | ViewpointNotFoundError 包含 viewpoint_id |
| `test_config_loader.py` | `test_load_viewpoint_yaml` | YAML → Viewpoint 对象正确映射 |
| `test_config_loader.py` | `test_load_engine_config` | engine_config.yaml 正确加载 |
| `test_config_loader.py` | `test_viewpoint_not_found` | 查询不存在 ID 抛出异常 |
| `test_config_loader.py` | `test_list_all_pagination` | 分页逻辑正确 |

## 验收标准

- [ ] 所有 `tests/core/` 测试通过
- [ ] `Viewpoint` 对象可从 YAML 正确加载
- [ ] `EngineConfig` 可从 YAML 正确加载
- [ ] 异常层级结构正确
- [ ] 目录结构符合设计文档 §7.4
