# 7. 代码接口定义与目录结构

## 7.1 核心接口 (Protocols)

```python
from typing import Protocol, Optional
from datetime import date, datetime
import pandas as pd
from dataclasses import dataclass, field

# ==================== Data Models ====================

@dataclass
class Location:
    lat: float
    lon: float
    altitude: int

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
    capabilities: list[str]  # ["sunrise", "sunset", "stargazing", "cloud_sea", "frost"]
    targets: list[Target]

@dataclass
class SunEvents:
    sunrise: datetime
    sunset: datetime
    sunrise_azimuth: float  # 0-360
    sunset_azimuth: float   # 0-360
    astronomical_dawn: datetime
    astronomical_dusk: datetime

@dataclass
class MoonStatus:
    phase: int              # 0-100
    elevation: float        # degrees, negative = below horizon
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
    score: int              # 0-100
    reason: str
    details: dict

@dataclass
class ScoreResult:
    total_score: int
    status: str             # "Perfect" | "Recommended" | "Possible" | "Not Recommended"
    breakdown: dict         # {"dimension": {"score": int, "max": int, "detail": str}}

# ==================== Plugin 架构 ====================

@dataclass
class DataRequirement:
    """评分器的数据需求声明"""
    needs_l2_target: bool = False
    needs_l2_light_path: bool = False
    needs_astro: bool = False
    season_months: list[int] | None = None

@dataclass
class DataContext:
    """共享数据上下文 — 所有 Plugin 复用"""
    date: date
    viewpoint: Viewpoint
    local_weather: pd.DataFrame
    sun_events: SunEvents | None = None
    moon_status: MoonStatus | None = None
    stargazing_window: StargazingWindow | None = None
    target_weather: dict[str, pd.DataFrame] | None = None
    light_path_weather: list[dict] | None = None
    l2_result: AnalysisResult | None = None

# ==================== Protocols ====================

class IFetcher(Protocol):
    """气象数据获取接口"""
    def fetch_hourly(
        self, lat: float, lon: float, days: int = 7
    ) -> pd.DataFrame:
        ...

class IAstroCalculator(Protocol):
    """天文计算接口"""
    def get_sun_events(
        self, lat: float, lon: float, target_date: date
    ) -> SunEvents:
        ...
    def get_moon_status(
        self, lat: float, lon: float, dt: datetime
    ) -> MoonStatus:
        ...
    def determine_stargazing_window(
        self, sun_events: SunEvents, moon_status: MoonStatus
    ) -> StargazingWindow:
        ...

class IGeoCalculator(Protocol):
    """地理计算接口"""
    def calculate_light_path_points(
        self, lat: float, lon: float, azimuth: float,
        count: int = 10, interval_km: float = 10
    ) -> list[tuple[float, float]]:
        ...

class IAnalyzer(Protocol):
    """分析器接口"""
    def analyze(
        self, data: pd.DataFrame, context: dict
    ) -> AnalysisResult:
        ...

class IScorerPlugin(Protocol):
    """可插拔评分器契约"""
    @property
    def event_type(self) -> str: ...
    @property
    def display_name(self) -> str: ...
    @property
    def data_requirement(self) -> DataRequirement: ...
    
    def check_trigger(self, l1_data: dict) -> bool: ...
    def score(self, context: DataContext) -> ScoreResult: ...
    def dimensions(self) -> list[str]: ...

class IReporter(Protocol):
    """报告生成器接口"""
    def generate(self, results: list[AnalysisResult]) -> str:
        ...

class ICacheRepository(Protocol):
    """缓存存储接口"""
    def query(
        self, lat: float, lon: float, 
        target_date: date, hours: list[int]
    ) -> Optional[list[dict]]:
        ...
    def upsert(
        self, lat: float, lon: float,
        target_date: date, hour: int, data: dict
    ) -> None:
        ...
```

---

## 7.2 异常定义

```python
class GMPError(Exception):
    """基础异常类"""
    pass

class APITimeoutError(GMPError):
    """外部API超时"""
    def __init__(self, service: str, timeout: int):
        self.service = service
        self.timeout = timeout
        super().__init__(f"{service} API 超时 ({timeout}s)")

class InvalidCoordinateError(GMPError):
    """坐标无效"""
    def __init__(self, lat: float, lon: float):
        super().__init__(f"坐标超出范围: ({lat}, {lon})")

class ViewpointNotFoundError(GMPError):
    """观景台未找到"""
    def __init__(self, viewpoint_id: str):
        self.viewpoint_id = viewpoint_id
        super().__init__(f"未找到观景台: {viewpoint_id}")

class DataDegradedWarning(UserWarning):
    """数据降级警告"""
    pass
```

---

## 7.3 配置接口

```python
@dataclass
class EngineConfig:
    """引擎配置"""
    # 数据库
    db_path: str = "gmp_cache.db"
    
    # 缓存 TTL
    memory_cache_ttl_seconds: int = 300
    db_cache_ttl_seconds: int = 3600
    
    # 坐标精度
    coord_precision: int = 2
    
    # 安全阈值
    precip_threshold: float = 50.0
    visibility_threshold: float = 1000
    local_cloud_threshold: float = 30
    target_cloud_threshold: float = 30
    light_path_threshold: float = 50
    wind_threshold: float = 20
    frost_temp_threshold: float = 2.0
    
    # 光路计算
    light_path_count: int = 10
    light_path_interval_km: float = 10
    
    # 评分权重 (日照金山 — 解耦后)
    golden_score_weights: dict = field(default_factory=lambda: {
        "light_path": 35,
        "target_visible": 40,
        "local_clear": 25
    })
    
    # 摘要生成
    summary_mode: str = "rule"
    
    # 分页
    default_page_size: int = 20
    max_page_size: int = 100
```

---

## 7.4 目录结构

```
gmp/
├── main.py                        # FastAPI 应用入口
├── config/
│   ├── engine_config.yaml         # 引擎配置 (阈值、权重、TTL)
│   └── viewpoints/
│       ├── niubei_gongga.yaml     # 牛背山观景台配置
│       ├── zheduo_gongga.yaml     # 折多山观景台配置
│       └── ...
├── core/
│   ├── scheduler.py               # GMP Scheduler 主调度器 (Plugin 驱动)
│   ├── pipeline.py                # AnalyzerPipeline
│   ├── models.py                  # 核心 dataclass (Viewpoint, DataContext, ...)
│   └── config_loader.py           # ViewpointConfig 加载器
├── fetcher/
│   ├── base.py                    # BaseFetcher (Protocol)
│   ├── meteo_fetcher.py           # MeteoFetcher (Open-Meteo 实现)
│   └── mock_fetcher.py            # MockFetcher (测试用)
├── astro/
│   ├── astro_utils.py             # AstroUtils (日出/日落/月相)
│   └── geo_utils.py               # GeoUtils (方位角/光路10点/距离)
├── analyzer/
│   ├── base.py                    # BaseAnalyzer (Protocol)
│   ├── local_analyzer.py          # LocalAnalyzer (L1 滤网)
│   └── remote_analyzer.py         # RemoteAnalyzer (L2 滤网)
├── scorer/
│   ├── engine.py                  # ScoreEngine (Plugin 注册中心)
│   ├── plugin.py                  # ScorerPlugin Protocol + DataRequirement
│   ├── golden_mountain.py         # GoldenMountainPlugin
│   ├── stargazing.py              # StargazingPlugin
│   ├── cloud_sea.py               # CloudSeaPlugin
│   └── frost.py                   # FrostPlugin
│   # 未来扩展: autumn_foliage.py, snow_play.py, ...
├── reporter/
│   ├── base.py                    # BaseReporter
│   ├── forecast_reporter.py       # ForecastReporter (JSON)
│   ├── timeline_reporter.py       # TimelineReporter (JSON)
│   ├── cli_formatter.py           # CLIFormatter (终端彩色输出)
│   └── summary_generator.py       # SummaryGenerator (规则/LLM)
├── cache/
│   ├── memory_cache.py            # MemoryCache (TTL 内存缓存)
│   ├── repository.py              # CacheRepository (SQLite 操作)
│   └── weather_cache.py           # WeatherCache (多级缓存门面)
├── api/
│   ├── routes.py                  # FastAPI 路由
│   ├── schemas.py                 # Pydantic 请求/响应模型
│   └── middleware.py              # 错误处理中间件
├── db/
│   ├── init_db.py                 # 数据库初始化脚本
│   └── gmp_cache.db          # SQLite 数据库文件
├── tests/
│   ├── unit/
│   │   ├── test_plugin_golden.py
│   │   ├── test_plugin_stargazing.py
│   │   ├── test_plugin_cloud_sea.py
│   │   ├── test_plugin_frost.py
│   │   ├── test_local_analyzer.py
│   │   ├── test_remote_analyzer.py
│   │   ├── test_astro_utils.py
│   │   ├── test_geo_utils.py
│   │   └── test_cache.py
│   ├── integration/
│   │   ├── test_pipeline.py
│   │   ├── test_api_endpoints.py
│   │   └── test_cache_sqlite.py
│   ├── e2e/
│   │   └── test_full_forecast.py
│   └── fixtures/
│       ├── weather_data_clear.json
│       ├── weather_data_rainy.json
│       └── viewpoint_niubei.yaml
└── requirements.txt
```
