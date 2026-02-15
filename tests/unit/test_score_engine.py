"""tests/unit/test_score_engine.py — ScoreEngine 单元测试"""

from datetime import date

import pytest

from gmp.scoring.models import DataRequirement
from tests.conftest import StubPlugin


# ==================== Plugin 注册 ====================


class TestPluginRegistration:
    """Plugin 注册与查询"""

    def test_register_and_all_plugins(self):
        """注册后 all_plugins() 包含该 Plugin"""
        from gmp.scoring.engine import ScoreEngine

        engine = ScoreEngine()
        plugin = StubPlugin("cloud_sea", "云海")
        engine.register(plugin)
        assert plugin in engine.all_plugins()

    def test_get_existing(self):
        """get() 返回已注册的 Plugin"""
        from gmp.scoring.engine import ScoreEngine

        engine = ScoreEngine()
        plugin = StubPlugin("cloud_sea", "云海")
        engine.register(plugin)
        assert engine.get("cloud_sea") is plugin

    def test_get_nonexistent_returns_none(self):
        """get() 查询不存在的 event_type 返回 None"""
        from gmp.scoring.engine import ScoreEngine

        engine = ScoreEngine()
        assert engine.get("不存在") is None

    def test_duplicate_register_overwrites(self):
        """重复注册同 event_type 覆盖旧 Plugin"""
        from gmp.scoring.engine import ScoreEngine

        engine = ScoreEngine()
        old = StubPlugin("cloud_sea", "旧云海")
        new = StubPlugin("cloud_sea", "新云海")
        engine.register(old)
        engine.register(new)
        assert engine.get("cloud_sea") is new
        assert len(engine.all_plugins()) == 1


# ==================== 需求聚合 ====================


class TestCollectRequirements:
    """collect_requirements 聚合逻辑"""

    def test_empty_list_returns_defaults(self):
        """空列表 → 默认 DataRequirement"""
        from gmp.scoring.engine import ScoreEngine

        engine = ScoreEngine()
        req = engine.collect_requirements([])
        assert req.needs_l2_target is False
        assert req.needs_l2_light_path is False
        assert req.needs_astro is False
        assert req.past_hours == 0

    def test_cloud_sea_only(self):
        """CloudSea 不需要 L2/astro"""
        from gmp.scoring.engine import ScoreEngine

        engine = ScoreEngine()
        cs = StubPlugin("cloud_sea", requirement=DataRequirement())
        req = engine.collect_requirements([cs])
        assert req.needs_l2_target is False
        assert req.needs_astro is False

    def test_golden_mountain_plus_stargazing(self):
        """GoldenMountain + Stargazing → needs_l2_target=True, needs_astro=True"""
        from gmp.scoring.engine import ScoreEngine

        engine = ScoreEngine()
        gm = StubPlugin(
            "sunrise_golden_mountain",
            requirement=DataRequirement(
                needs_l2_target=True,
                needs_l2_light_path=True,
                needs_astro=True,
            ),
        )
        sg = StubPlugin(
            "stargazing",
            requirement=DataRequirement(needs_astro=True),
        )
        req = engine.collect_requirements([gm, sg])
        assert req.needs_l2_target is True
        assert req.needs_l2_light_path is True
        assert req.needs_astro is True
        assert req.past_hours == 0

    def test_past_hours_takes_max(self):
        """SnowTree(24) + Frost(0) → past_hours=24"""
        from gmp.scoring.engine import ScoreEngine

        engine = ScoreEngine()
        st = StubPlugin("snow_tree", requirement=DataRequirement(past_hours=24))
        fr = StubPlugin("frost", requirement=DataRequirement(past_hours=0))
        req = engine.collect_requirements([st, fr])
        assert req.past_hours == 24


# ==================== Plugin 过滤 ====================


class TestFilterActivePlugins:
    """filter_active_plugins 过滤逻辑"""

    def setup_method(self):
        from gmp.scoring.engine import ScoreEngine

        self.engine = ScoreEngine()
        # 注册完整 Plugin 集
        self.engine.register(StubPlugin("sunrise_golden_mountain"))
        self.engine.register(StubPlugin("cloud_sea"))
        self.engine.register(StubPlugin("frost"))
        self.engine.register(
            StubPlugin(
                "snow_tree",
                requirement=DataRequirement(season_months=[10, 11, 12, 1, 2]),
            )
        )

    def test_capabilities_filter(self):
        """capabilities=[sunrise, cloud_sea] → 仅对应 event_type 的 Plugin"""
        active = self.engine.filter_active_plugins(
            capabilities=["sunrise", "cloud_sea"],
            target_date=date(2026, 1, 15),
        )
        types = {p.event_type for p in active}
        assert types == {"sunrise_golden_mountain", "cloud_sea"}

    def test_events_filter(self):
        """events_filter 进一步限定"""
        active = self.engine.filter_active_plugins(
            capabilities=["sunrise", "cloud_sea"],
            target_date=date(2026, 1, 15),
            events_filter=["cloud_sea"],
        )
        types = {p.event_type for p in active}
        assert types == {"cloud_sea"}

    def test_season_filter_excludes(self):
        """season_months=[10,11,12,1,2] + 日期为6月 → snow_tree 被排除"""
        active = self.engine.filter_active_plugins(
            capabilities=["sunrise", "cloud_sea", "frost", "snow_tree"],
            target_date=date(2026, 6, 15),
        )
        types = {p.event_type for p in active}
        assert "snow_tree" not in types

    def test_season_filter_includes(self):
        """season_months=[10,11,12,1,2] + 日期为1月 → snow_tree 保留"""
        active = self.engine.filter_active_plugins(
            capabilities=["snow_tree"],
            target_date=date(2026, 1, 15),
        )
        types = {p.event_type for p in active}
        assert "snow_tree" in types

    def test_season_months_none_always_included(self):
        """season_months=None → 全年保留"""
        active = self.engine.filter_active_plugins(
            capabilities=["frost"],
            target_date=date(2026, 7, 15),
        )
        types = {p.event_type for p in active}
        assert "frost" in types
