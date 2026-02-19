"""gmp/scoring/engine.py — ScoreEngine Plugin 注册中心

负责 Plugin 注册、查询、数据需求聚合、活跃 Plugin 过滤。
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from gmp.scoring.models import DataRequirement

if TYPE_CHECKING:
    from gmp.core.models import ScoreResult
    from gmp.scoring.models import DataContext


# capability → event_type 映射表
_CAPABILITY_EVENT_MAP: dict[str, list[str]] = {
    "clear_sky": ["clear_sky"],
    "sunrise": ["sunrise_golden_mountain"],
    "sunset": ["sunset_golden_mountain"],
    "stargazing": ["stargazing"],
    "cloud_sea": ["cloud_sea"],
    "frost": ["frost"],
    "snow_tree": ["snow_tree"],
    "ice_icicle": ["ice_icicle"],
}

# 通用能力 — 所有观景台自动注入，无需手动配置
_UNIVERSAL_CAPABILITIES: list[str] = [
    "clear_sky",    # 晴天（基底）
    "stargazing",   # 观星（基底）
    "frost",        # 雾凇（通用）
    "snow_tree",    # 雪挂树（通用）
    "ice_icicle",   # 冰挂（通用）
]


@runtime_checkable
class ScorerPlugin(Protocol):
    """可插拔评分器契约"""

    @property
    def event_type(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def data_requirement(self) -> DataRequirement: ...

    def score(self, context: DataContext) -> ScoreResult | None: ...

    def dimensions(self) -> list[str]: ...


class ScoreEngine:
    """Plugin 注册中心"""

    def __init__(self) -> None:
        self._plugins: dict[str, ScorerPlugin] = {}

    def register(self, plugin: ScorerPlugin) -> None:
        """注册一个评分 Plugin（按 event_type 索引）"""
        self._plugins[plugin.event_type] = plugin

    def all_plugins(self) -> list[ScorerPlugin]:
        """返回所有已注册 Plugin"""
        return list(self._plugins.values())

    @property
    def display_names(self) -> dict[str, str]:
        """返回 event_type → 中文显示名称 的映射 (由 Plugin.display_name 驱动)"""
        return {
            et: plugin.display_name for et, plugin in self._plugins.items()
        }

    def get(self, event_type: str) -> ScorerPlugin | None:
        """按 event_type 获取 Plugin"""
        return self._plugins.get(event_type)

    def collect_requirements(
        self, plugins: list[ScorerPlugin]
    ) -> DataRequirement:
        """聚合多个 Plugin 的数据需求"""
        return DataRequirement(
            needs_l2_target=any(
                p.data_requirement.needs_l2_target for p in plugins
            ),
            needs_l2_light_path=any(
                p.data_requirement.needs_l2_light_path for p in plugins
            ),
            needs_astro=any(
                p.data_requirement.needs_astro for p in plugins
            ),
            past_hours=max(
                (p.data_requirement.past_hours for p in plugins), default=0
            ),
        )

    def filter_active_plugins(
        self,
        capabilities: list[str],
        target_date: date,
        events_filter: list[str] | None = None,
    ) -> list[ScorerPlugin]:
        """筛选活跃 Plugin

        1. 将 capabilities 展开为 event_type 集合
        2. 按 event_type 筛选
        3. 应用 events_filter
        4. 按 season_months 过滤
        """
        # 合并通用能力后展开 capabilities → event_types
        all_caps = list(set(capabilities + _UNIVERSAL_CAPABILITIES))
        allowed: set[str] = set()
        for cap in all_caps:
            mapped = _CAPABILITY_EVENT_MAP.get(cap, [cap])
            allowed.update(mapped)

        active: list[ScorerPlugin] = []
        for plugin in self._plugins.values():
            if plugin.event_type not in allowed:
                continue
            if events_filter and plugin.event_type not in events_filter:
                continue
            season = plugin.data_requirement.season_months
            if season and target_date.month not in season:
                continue
            active.append(plugin)

        return active
