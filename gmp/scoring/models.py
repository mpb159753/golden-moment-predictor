"""gmp/scoring/models.py — 评分系统数据模型

DataRequirement: Plugin 的数据需求声明
DataContext: 一天的共享数据上下文
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

from gmp.core.models import (
    MoonStatus,
    StargazingWindow,
    SunEvents,
    Viewpoint,
)

if TYPE_CHECKING:
    pass


@dataclass
class DataRequirement:
    """评分器的数据需求声明"""

    needs_l2_target: bool = False
    needs_l2_light_path: bool = False
    needs_astro: bool = False
    past_hours: int = 0
    season_months: list[int] | None = None


@dataclass
class DataContext:
    """一天的共享数据上下文 — 所有 Plugin 复用"""

    date: date
    viewpoint: Viewpoint
    local_weather: pd.DataFrame

    # 按需获取的天文数据
    sun_events: SunEvents | None = None
    moon_status: MoonStatus | None = None
    stargazing_window: StargazingWindow | None = None

    # Phase 2: 按需获取的远程数据
    target_weather: dict[str, pd.DataFrame] | None = None
    light_path_weather: list[dict] | None = None

    # 数据质量标记
    data_freshness: str = "fresh"
