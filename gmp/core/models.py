from typing import Optional, Protocol
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
