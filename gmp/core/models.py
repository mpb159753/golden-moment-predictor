"""GMP 核心数据模型

所有数据结构均为纯 dataclass，不包含业务逻辑。
字段定义严格遵循 design/07-code-interface.md §7.1。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Location:
    """地理位置坐标 (WGS84)"""
    lat: float       # 纬度
    lon: float       # 经度
    altitude: int    # 海拔 (m)


@dataclass
class Target:
    """观测目标 (如山峰)"""
    name: str
    lat: float
    lon: float
    altitude: int
    weight: str  # "primary" | "secondary"
    applicable_events: Optional[list[str]] = None  # None = 自动计算


@dataclass
class Viewpoint:
    """观景台"""
    id: str
    name: str
    location: Location
    capabilities: list[str]  # ["sunrise", "sunset", "stargazing", ...]
    targets: list[Target] = field(default_factory=list)


@dataclass
class SunEvents:
    """日出日落事件"""
    sunrise: datetime
    sunset: datetime
    sunrise_azimuth: float   # 0-360
    sunset_azimuth: float    # 0-360
    astronomical_dawn: datetime
    astronomical_dusk: datetime


@dataclass
class MoonStatus:
    """月相状态"""
    phase: int                       # 0-100
    elevation: float                 # degrees, negative = below horizon
    moonrise: Optional[datetime] = None
    moonset: Optional[datetime] = None


@dataclass
class StargazingWindow:
    """观星窗口"""
    optimal_start: Optional[datetime] = None
    optimal_end: Optional[datetime] = None
    good_start: Optional[datetime] = None
    good_end: Optional[datetime] = None
    quality: str = "poor"  # "optimal" | "good" | "partial" | "poor"


@dataclass
class AnalysisResult:
    """分析结果 (L1/L2 滤网输出)"""
    passed: bool
    score: int          # 0-100
    reason: str
    details: dict = field(default_factory=dict)


@dataclass
class ScoreResult:
    """评分结果 (Plugin 输出)"""
    total_score: int
    status: str         # "Perfect" | "Recommended" | "Possible" | "Not Recommended"
    breakdown: dict = field(default_factory=dict)
    # breakdown: {"dimension": {"score": int, "max": int, "detail": str}}


@dataclass
class DataRequirement:
    """评分器的数据需求声明"""
    needs_l2_target: bool = False
    needs_l2_light_path: bool = False
    needs_astro: bool = False
    season_months: list[int] | None = None


@dataclass
class DataContext:
    """共享数据上下文 — 所有 Plugin 复用

    注意: pd.DataFrame 使用前向引用字符串，避免强制导入 pandas。
    """
    date: date
    viewpoint: "Viewpoint"
    local_weather: "pd.DataFrame"
    sun_events: "SunEvents | None" = None
    moon_status: "MoonStatus | None" = None
    stargazing_window: "StargazingWindow | None" = None
    target_weather: "dict[str, pd.DataFrame] | None" = None
    light_path_weather: "list[dict] | None" = None
    l2_result: "AnalysisResult | None" = None
