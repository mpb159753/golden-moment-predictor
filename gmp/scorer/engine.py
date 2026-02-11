"""ScoreEngine — Plugin 注册中心

设计依据: design/03-scoring-plugins.md §3.11
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gmp.core.models import DataRequirement

if TYPE_CHECKING:
    from gmp.core.models import IScorerPlugin  # Protocol


class ScoreEngine:
    """Plugin 注册中心

    职责:
      - 注册 / 获取 ScorerPlugin
      - 聚合多个 Plugin 的 DataRequirement
    """

    def __init__(self) -> None:
        self._plugins: dict[str, object] = {}

    # ------------------------------------------------------------------
    # 注册 & 查询
    # ------------------------------------------------------------------

    def register(self, plugin: object) -> None:
        """注册一个评分器 Plugin (duck-typing: 需有 event_type 属性)."""
        event_type = getattr(plugin, "event_type", None)
        if event_type is None:
            raise ValueError("Plugin 必须包含 event_type 属性")
        self._plugins[event_type] = plugin

    def all_plugins(self) -> list:
        """返回所有已注册的 Plugin."""
        return list(self._plugins.values())

    def get(self, event_type: str) -> object | None:
        """按事件类型获取 Plugin."""
        return self._plugins.get(event_type)

    # ------------------------------------------------------------------
    # 需求聚合
    # ------------------------------------------------------------------

    def collect_requirements(self, plugins: list) -> DataRequirement:
        """聚合多个 Plugin 的数据需求。

        任一 Plugin 需要某项数据 → 整体就需要该数据。
        """
        return DataRequirement(
            needs_l2_target=any(
                getattr(p, "data_requirement", DataRequirement()).needs_l2_target
                for p in plugins
            ),
            needs_l2_light_path=any(
                getattr(p, "data_requirement", DataRequirement()).needs_l2_light_path
                for p in plugins
            ),
            needs_astro=any(
                getattr(p, "data_requirement", DataRequirement()).needs_astro
                for p in plugins
            ),
        )
