"""gmp/core/models.py — 核心领域数据模型与工具函数

所有 dataclass 模型和工具函数定义，供各模块共享使用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional


# ==================== 领域模型 ====================


@dataclass
class Location:
    """地理位置 (WGS84)"""

    lat: float  # 纬度
    lon: float  # 经度
    altitude: int  # 海拔 m


@dataclass
class Target:
    """观测目标"""

    name: str
    lat: float
    lon: float
    altitude: int
    weight: Literal["primary", "secondary"]
    applicable_events: Optional[list[str]]  # None = 自动计算

    def __post_init__(self) -> None:
        if self.weight not in ("primary", "secondary"):
            raise ValueError(
                f"weight 必须为 'primary' 或 'secondary', 收到: {self.weight}"
            )


@dataclass
class Viewpoint:
    """观景台"""

    id: str
    name: str
    location: Location
    capabilities: list[str]  # ["sunrise", "sunset", "stargazing", ...]
    targets: list[Target]


@dataclass
class RouteStop:
    """线路停靠点"""

    viewpoint_id: str
    order: int  # 停靠顺序 (1-based)
    stay_note: str = ""


@dataclass
class Route:
    """旅行线路"""

    id: str
    name: str
    description: str = ""
    stops: list[RouteStop] = field(default_factory=list)


# ==================== 天文模型 ====================


@dataclass
class SunEvents:
    """太阳事件"""

    sunrise: datetime
    sunset: datetime
    sunrise_azimuth: float  # 0-360
    sunset_azimuth: float  # 0-360
    astronomical_dawn: datetime
    astronomical_dusk: datetime


@dataclass
class MoonStatus:
    """月亮状态"""

    phase: int  # 0-100
    elevation: float  # degrees, 负 = 地平线下
    moonrise: Optional[datetime]
    moonset: Optional[datetime]


@dataclass
class StargazingWindow:
    """观星窗口"""

    optimal_start: Optional[datetime]
    optimal_end: Optional[datetime]
    good_start: Optional[datetime]
    good_end: Optional[datetime]
    quality: str  # "optimal" | "good" | "partial" | "poor"


# ==================== 评分模型 ====================


@dataclass
class ScoreResult:
    """单项评分结果"""

    event_type: str
    total_score: int  # 0-100
    status: str  # "Perfect" | "Recommended" | "Possible" | "Not Recommended"
    breakdown: dict  # {"dimension": {"score": int, "max": int, "detail": str}}
    time_window: str = ""  # "07:15 - 07:45"
    confidence: str = ""  # "High" | "Medium" | "Low"
    highlights: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class ForecastDay:
    """单日预测结果"""

    date: str  # YYYY-MM-DD
    summary: str  # 由 SummaryGenerator 生成
    best_event: ScoreResult | None
    events: list[ScoreResult]
    confidence: str  # "High" | "Medium" | "Low"


@dataclass
class PipelineResult:
    """Scheduler 一次 run() 的完整输出"""

    viewpoint: Viewpoint
    forecast_days: list[ForecastDay]
    meta: dict
    # meta 字段说明:
    #   generated_at: str (ISO datetime)
    #   engine_version: str
    #   cache_stats: dict (缓存命中/未命中统计)
    #   data_freshness: str ("fresh" | "degraded")


# ==================== 工具函数 ====================

# 默认状态阈值
_DEFAULT_THRESHOLDS = {"perfect": 95, "recommended": 80, "possible": 50}


def score_to_status(
    score: int,
    *,
    thresholds: dict[str, int] | None = None,
) -> str:
    """根据分数返回状态字符串。

    Args:
        score: 0-100 的评分值
        thresholds: 可选阈值覆盖，key 为 perfect/recommended/possible
    """
    t = thresholds or _DEFAULT_THRESHOLDS
    if score >= t["perfect"]:
        return "Perfect"
    elif score >= t["recommended"]:
        return "Recommended"
    elif score >= t["possible"]:
        return "Possible"
    else:
        return "Not Recommended"


# 默认置信度区间配置
_DEFAULT_CONFIDENCE_CONFIG = {"high": [1, 2], "medium": [3, 4], "low": [5, 16]}


def days_ahead_to_confidence(
    days_ahead: int,
    config: dict[str, list[int]] | None = None,
) -> str:
    """根据预测提前天数返回置信度。

    Args:
        days_ahead: 距今天数
        config: 可选区间配置覆盖，如 {"high": [1, 2], "medium": [3, 4], "low": [5, 16]}
    """
    c = config or _DEFAULT_CONFIDENCE_CONFIG
    for level, (lo, hi) in c.items():
        if lo <= days_ahead <= hi:
            return level.capitalize()
    return "Low"
