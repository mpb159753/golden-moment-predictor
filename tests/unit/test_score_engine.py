"""ScoreEngine 单元测试

测试用例来自 implementation-plans/module-05-scorer-simple.md
"""

import pytest

from gmp.core.models import DataRequirement
from gmp.scorer.engine import ScoreEngine
from gmp.scorer.cloud_sea import CloudSeaPlugin
from gmp.scorer.frost import FrostPlugin
from gmp.scorer.snow_tree import SnowTreePlugin
from gmp.scorer.ice_icicle import IceIciclePlugin


@pytest.fixture
def engine():
    return ScoreEngine()


@pytest.fixture
def loaded_engine():
    """预装 4 个简单 Plugin 的 Engine."""
    e = ScoreEngine()
    e.register(CloudSeaPlugin())
    e.register(FrostPlugin())
    e.register(SnowTreePlugin())
    e.register(IceIciclePlugin())
    return e


# ==================== 注册 & 获取 ====================


class TestRegisterAndGet:
    def test_register_and_get(self, engine):
        """注册后可按 event_type 获取."""
        plugin = CloudSeaPlugin()
        engine.register(plugin)
        assert engine.get("cloud_sea") is plugin

    def test_get_nonexistent(self, engine):
        """获取不存在的 event_type → None."""
        assert engine.get("nonexistent") is None

    def test_register_overwrites(self, engine):
        """重复注册同一 event_type → 覆盖."""
        p1 = CloudSeaPlugin()
        p2 = CloudSeaPlugin()
        engine.register(p1)
        engine.register(p2)
        assert engine.get("cloud_sea") is p2


class TestAllPlugins:
    def test_all_plugins(self, loaded_engine):
        """返回所有已注册 Plugin."""
        plugins = loaded_engine.all_plugins()
        assert len(plugins) == 4
        types = {getattr(p, "event_type") for p in plugins}
        assert types == {"cloud_sea", "frost", "snow_tree", "ice_icicle"}

    def test_empty_engine(self, engine):
        """空 Engine → 空列表."""
        assert engine.all_plugins() == []


class TestCollectRequirements:
    def test_simple_plugins_no_l2(self, loaded_engine):
        """4 个简单 Plugin 均不需要 L2, 聚合结果应无 L2 需求."""
        plugins = loaded_engine.all_plugins()
        req = loaded_engine.collect_requirements(plugins)
        assert req.needs_l2_target is False
        assert req.needs_l2_light_path is False
        assert req.needs_astro is False

    def test_mixed_requirements(self, engine):
        """混入需要 L2 的自定义 Plugin → 聚合结果包含 L2."""

        class MockGoldenPlugin:
            event_type = "sunrise_golden_mountain"
            display_name = "日照金山"
            data_requirement = DataRequirement(
                needs_l2_target=True,
                needs_l2_light_path=True,
                needs_astro=True,
            )

        engine.register(CloudSeaPlugin())
        engine.register(MockGoldenPlugin())
        plugins = engine.all_plugins()
        req = engine.collect_requirements(plugins)
        assert req.needs_l2_target is True
        assert req.needs_l2_light_path is True
        assert req.needs_astro is True


class TestRegisterNewPlugin:
    def test_register_custom_plugin(self, engine):
        """注册自定义 Plugin."""

        class AutumnFoliagePlugin:
            event_type = "autumn_foliage"
            display_name = "秋叶"
            data_requirement = DataRequirement(season_months=[9, 10, 11])

            def check_trigger(self, l1_data: dict) -> bool:
                return True

            def dimensions(self) -> list[str]:
                return ["color"]

        plugin = AutumnFoliagePlugin()
        engine.register(plugin)
        assert engine.get("autumn_foliage") is plugin
        assert engine.get("autumn_foliage").display_name == "秋叶"


class TestEventsFilter:
    def test_events_filter(self, loaded_engine):
        """结合 capabilities 过滤 Plugin."""
        # 模拟 Scheduler 过滤逻辑
        capabilities = {"cloud_sea", "frost"}
        events_filter = ["cloud_sea"]

        active = [
            p
            for p in loaded_engine.all_plugins()
            if getattr(p, "event_type") in capabilities
            and getattr(p, "event_type") in events_filter
        ]
        assert len(active) == 1
        assert active[0].event_type == "cloud_sea"

    def test_no_filter(self, loaded_engine):
        """无过滤 → 按 capabilities 全量返回."""
        capabilities = {"cloud_sea", "frost", "snow_tree", "ice_icicle"}
        active = [
            p
            for p in loaded_engine.all_plugins()
            if getattr(p, "event_type") in capabilities
        ]
        assert len(active) == 4


class TestErrorHandling:
    def test_register_invalid_plugin(self, engine):
        """注册无 event_type 属性的对象 → ValueError."""

        class Invalid:
            pass

        with pytest.raises(ValueError, match="event_type"):
            engine.register(Invalid())
