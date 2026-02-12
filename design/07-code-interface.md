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
    capabilities: list[str]  # ["sunrise", "sunset", "stargazing", "cloud_sea", "frost", "snow_tree", "ice_icicle"]
    targets: list[Target]

@dataclass
class RouteStop:
    """线路上的一个停靠点"""
    viewpoint_id: str
    order: int               # 停靠顺序 (1-based)
    stay_note: str = ""      # 停留建议 (如 "建议日落前到达")

@dataclass
class Route:
    """旅行线路"""
    id: str                  # 如 "lixiao"
    name: str                # 如 "理小路"
    description: str = ""    # 线路简介
    stops: list[RouteStop] = field(default_factory=list)

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
class ScoreResult:
    total_score: int
    status: str             # "Perfect" | "Recommended" | "Possible" | "Not Recommended"
    breakdown: dict         # {"dimension": {"score": int, "max": int, "detail": str}}

@dataclass
class PipelineResult:
    """Scheduler 一次 run() 的完整输出"""
    viewpoint: Viewpoint
    forecast_days: list[dict]   # 每日预测结果
    meta: dict                  # cache_stats, generated_at 等

# ==================== Plugin 架构 ====================

@dataclass
class DataRequirement:
    """评分器的数据需求声明"""
    needs_l2_target: bool = False
    needs_l2_light_path: bool = False
    needs_astro: bool = False
    past_hours: int = 0                 # 需要多少小时的历史数据 (0=无需回看)
    season_months: list[int] | None = None

@dataclass
class DataContext:
    """一天的共享数据上下文，仅在单次 pipeline 执行内有效，不持久化"""
    date: date
    viewpoint: Viewpoint
    local_weather: pd.DataFrame
    sun_events: SunEvents | None = None
    moon_status: MoonStatus | None = None
    stargazing_window: StargazingWindow | None = None
    target_weather: dict[str, pd.DataFrame] | None = None
    light_path_weather: list[dict] | None = None
    data_freshness: str = "fresh"  # "fresh" | "stale" | "degraded"

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



class IScorerPlugin(Protocol):
    """可插拔评分器契约"""
    @property
    def event_type(self) -> str: ...
    @property
    def display_name(self) -> str: ...
    @property
    def data_requirement(self) -> DataRequirement: ...
    
    def score(self, context: DataContext) -> ScoreResult | None: ...  # None=未触发
    def dimensions(self) -> list[str]: ...

class IWeatherCache(Protocol):
    """Weather cache protocol"""
    def get(self, lat: float, lon: float, 
            date: date, hours: int = 24) -> pd.DataFrame | None: ...
    def set(self, lat: float, lon: float,
            date: date, data: pd.DataFrame) -> None: ...
    def is_fresh(self, fetched_at: datetime, data_source: str) -> bool: ...

class IReporter(Protocol):
    """报告生成器接口"""
    def generate(self, result: PipelineResult) -> str:
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

class RouteNotFoundError(GMPError):
    """线路未找到"""
    def __init__(self, route_id: str):
        self.route_id = route_id
        super().__init__(f"未找到线路: {route_id}")

class DataDegradedWarning(UserWarning):
    """数据降级警告"""
    pass

class InvalidDateError(GMPError):
    """日期无效 (回测场景)"""
    def __init__(self, date: date, reason: str):
        self.date = date
        super().__init__(f"日期无效: {date} ({reason})")
```

---

## 7.3 配置接口

```python
@dataclass
class EngineConfig:
    """全局引擎配置"""
    db_path: str = "data/gmp.db"
    output_dir: str = "public/data"
    archive_dir: str = "archive"
    log_level: str = "INFO"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    forecast_days: int = 7
    light_path_points: int = 10
    light_path_interval_km: float = 1.0
    
    # 数据新鲜度策略
    # forecast: 当日获取的数据视为有效
    # archive: 永不过期
    data_freshness_ttl_hours: dict[str, int] = field(default_factory=lambda: {
        "forecast": 24,
        "archive": 0, # 0 means never stale
    })

    # 安全阈值
    safety: dict = field(default_factory=lambda: {
        "precip_threshold": 50.0,
        "visibility_threshold": 1000,
    })
    
    # 评分配置 (每个 Plugin 的完整阈值和权重)
    scoring: dict = field(default_factory=lambda: {})
    
    # 摘要生成
    summary_mode: str = "rule"
    

class ConfigManager:
    """统一配置管理器 — 加载 YAML 并提供结构化访问"""
    
    def __init__(self, config_path: str = "config/engine_config.yaml"):
        self.config: EngineConfig = self._load(config_path)
    
    def _load(self, path: str) -> EngineConfig:
        """加载 YAML 配置并构建 EngineConfig"""
        ...
    
    def get_plugin_config(self, event_type: str) -> dict:
        """获取指定 Plugin 的评分配置 (阈值 + 权重)
        
        Returns:
            {
                "weights": {"light_path": 35, "target_visible": 40, ...},
                "thresholds": {
                    "light_path_cloud": [10, 20, 30, 50],
                    "target_cloud": [10, 20, 30, 50],
                    ...
                },
                "veto_threshold": 0,
            }
        """
        return self.config.scoring.get(event_type, {})
    
    def get_safety_config(self) -> dict:
        """获取安全阈值配置"""
        return self.config.safety
    
    def get_output_config(self) -> dict:
        """获取输出路径配置"""
        return {"output_dir": self.config.output_dir, "archive_dir": self.config.archive_dir}
```

---

## 7.4 目录结构

gmp/
├── __init__.py
├── main.py                        # CLI 入口
├── core/
│   ├── scheduler.py               # GMPScheduler (主调度器)
│   ├── config_loader.py           # ViewpointConfig + RouteConfig 加载
│   └── models.py                  # Viewpoint, Route, Location 等数据模型
├── data/
│   ├── meteo_fetcher.py           # MeteoFetcher (Open-Meteo API)
│   ├── astro_utils.py             # AstroUtils (天文计算)
│   └── geo_utils.py               # GeoUtils (地理计算)
├── cache/
│   ├── weather_cache.py           # WeatherCache (SQLite 缓存管理)
│   └── repository.py              # CacheRepository (DB 操作)
├── scoring/
│   ├── engine.py                  # ScoreEngine (Plugin 注册中心)
│   ├── models.py                  # DataContext, ScoreResult, DataRequirement
│   └── plugins/
│       ├── golden_mountain.py     # GoldenMountainPlugin (日照金山)
│       ├── stargazing.py          # StargazingPlugin (观星)
│       ├── cloud_sea.py           # CloudSeaPlugin (云海)
│       ├── frost.py               # FrostPlugin (雾凇)
│       ├── snow_tree.py           # SnowTreePlugin (树挂积雪)
│       └── ice_icicle.py          # IceIciclePlugin (冰挂)
├── output/
│   ├── forecast_reporter.py       # ForecastReporter (报告生成)
│   ├── timeline_reporter.py       # TimelineReporter (时间线)
│   ├── cli_formatter.py           # CLIFormatter (CLI 格式化)
│   ├── summary_generator.py       # SummaryGenerator (规则模板)
│   └── json_file_writer.py        # JSONFileWriter (JSON 写入)
├── backtest/
│   └── gmp_cache.db          # SQLite 数据库文件
├── tests/
│   ├── core/
│   │   └── test_exceptions.py     # 异常类测试
│   ├── unit/
│   │   ├── test_plugin_golden.py
│   │   ├── test_plugin_stargazing.py
│   │   ├── test_plugin_cloud_sea.py
│   │   ├── test_plugin_frost.py
│   │   ├── test_plugin_snow_tree.py
│   │   ├── test_plugin_ice_icicle.py
│   │   ├── test_astro_utils.py
│   │   ├── test_geo_utils.py
│   │   └── test_cache.py
│   ├── integration/
│   │   ├── test_pipeline.py
│   │   ├── test_json_writer.py
│   │   └── test_cache_sqlite.py
│   ├── backtest/
│   │   ├── test_backtester.py     # 回测引擎单元测试
│   │   └── test_historical_fetch.py # 历史数据获取测试
│   ├── e2e/
│   │   └── test_full_forecast.py
│   └── fixtures/
│       ├── weather_data_clear.json
│       ├── weather_data_rainy.json
│       ├── weather_data_historical.json  # 历史天气数据 fixture
│       └── viewpoint_niubei.yaml
└── requirements.txt               # httpx, pandas, ephem, click, pyyaml, structlog
```
