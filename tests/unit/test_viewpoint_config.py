"""tests/unit/test_viewpoint_config.py — ViewpointConfig 单元测试

测试观景台配置目录的加载、查找、错误处理。
"""

import pytest
import yaml

from gmp.core.config_loader import ViewpointConfig
from gmp.core.exceptions import ViewpointNotFoundError
from gmp.core.models import Location, Target, Viewpoint


# ==================== Fixtures ====================


@pytest.fixture
def viewpoint_yaml() -> dict:
    """niubei_gongga 观景台配置。"""
    return {
        "id": "niubei_gongga",
        "name": "牛背山",
        "location": {"lat": 29.75, "lon": 102.35, "altitude": 3660},
        "capabilities": [
            "sunrise",
            "sunset",
            "stargazing",
            "cloud_sea",
            "frost",
            "snow_tree",
            "ice_icicle",
        ],
        "targets": [
            {
                "name": "贡嘎主峰",
                "lat": 29.58,
                "lon": 101.88,
                "altitude": 7556,
                "weight": "primary",
                "applicable_events": None,
            },
            {
                "name": "雅拉神山",
                "lat": 30.15,
                "lon": 101.75,
                "altitude": 5820,
                "weight": "secondary",
                "applicable_events": ["sunset"],
            },
        ],
    }


@pytest.fixture
def second_viewpoint_yaml() -> dict:
    """第二个观景台配置，用于多文件加载测试。"""
    return {
        "id": "zheduo_gongga",
        "name": "折多山",
        "location": {"lat": 30.05, "lon": 101.90, "altitude": 4298},
        "capabilities": ["sunrise", "sunset"],
        "targets": [
            {
                "name": "贡嘎主峰",
                "lat": 29.58,
                "lon": 101.88,
                "altitude": 7556,
                "weight": "primary",
                "applicable_events": None,
            },
        ],
    }


@pytest.fixture
def viewpoint_dir(viewpoint_yaml, second_viewpoint_yaml, tmp_path):
    """创建包含两个观景台 YAML 文件的临时目录。"""
    vp_dir = tmp_path / "viewpoints"
    vp_dir.mkdir()
    (vp_dir / "niubei_gongga.yaml").write_text(
        yaml.dump(viewpoint_yaml, allow_unicode=True)
    )
    (vp_dir / "zheduo_gongga.yaml").write_text(
        yaml.dump(second_viewpoint_yaml, allow_unicode=True)
    )
    return str(vp_dir)


@pytest.fixture
def single_viewpoint_dir(viewpoint_yaml, tmp_path):
    """只包含一个观景台的目录。"""
    vp_dir = tmp_path / "viewpoints"
    vp_dir.mkdir()
    (vp_dir / "niubei_gongga.yaml").write_text(
        yaml.dump(viewpoint_yaml, allow_unicode=True)
    )
    return str(vp_dir)


# ==================== 加载测试 ====================


class TestViewpointConfigLoad:
    """ViewpointConfig 加载测试。"""

    def test_load_viewpoint_attributes(self, single_viewpoint_dir):
        """加载 niubei_gongga.yaml → Viewpoint 属性完整。"""
        vpc = ViewpointConfig()
        vpc.load(single_viewpoint_dir)

        vp = vpc.get("niubei_gongga")
        assert isinstance(vp, Viewpoint)
        assert vp.id == "niubei_gongga"
        assert vp.name == "牛背山"
        assert isinstance(vp.location, Location)
        assert vp.location.lat == 29.75
        assert vp.location.lon == 102.35
        assert vp.location.altitude == 3660

    def test_load_capabilities(self, single_viewpoint_dir):
        """capabilities 正确加载。"""
        vpc = ViewpointConfig()
        vpc.load(single_viewpoint_dir)
        vp = vpc.get("niubei_gongga")
        assert "sunrise" in vp.capabilities
        assert "cloud_sea" in vp.capabilities
        assert len(vp.capabilities) == 7

    def test_load_targets(self, single_viewpoint_dir):
        """targets 正确转换为 Target 对象。"""
        vpc = ViewpointConfig()
        vpc.load(single_viewpoint_dir)
        vp = vpc.get("niubei_gongga")

        assert len(vp.targets) == 2
        gongga = vp.targets[0]
        assert isinstance(gongga, Target)
        assert gongga.name == "贡嘎主峰"
        assert gongga.lat == 29.58
        assert gongga.lon == 101.88
        assert gongga.altitude == 7556
        assert gongga.weight == "primary"

    def test_target_applicable_events_null(self, single_viewpoint_dir):
        """Target 的 applicable_events=null → None。"""
        vpc = ViewpointConfig()
        vpc.load(single_viewpoint_dir)
        vp = vpc.get("niubei_gongga")

        gongga = vp.targets[0]
        assert gongga.applicable_events is None

    def test_target_applicable_events_list(self, single_viewpoint_dir):
        """Target 的 applicable_events=["sunset"] → ["sunset"]。"""
        vpc = ViewpointConfig()
        vpc.load(single_viewpoint_dir)
        vp = vpc.get("niubei_gongga")

        yala = vp.targets[1]
        assert yala.applicable_events == ["sunset"]


# ==================== 查询测试 ====================


class TestViewpointConfigQuery:
    """ViewpointConfig 查询测试。"""

    def test_get_existing(self, viewpoint_dir):
        """get('niubei_gongga') 返回正确对象。"""
        vpc = ViewpointConfig()
        vpc.load(viewpoint_dir)
        vp = vpc.get("niubei_gongga")
        assert vp.id == "niubei_gongga"

    def test_get_not_found(self, viewpoint_dir):
        """get('不存在') → ViewpointNotFoundError。"""
        vpc = ViewpointConfig()
        vpc.load(viewpoint_dir)
        with pytest.raises(ViewpointNotFoundError):
            vpc.get("不存在")

    def test_list_all(self, viewpoint_dir):
        """list_all() 返回所有加载的观景台。"""
        vpc = ViewpointConfig()
        vpc.load(viewpoint_dir)
        all_vps = vpc.list_all()
        assert len(all_vps) == 2
        ids = {vp.id for vp in all_vps}
        assert ids == {"niubei_gongga", "zheduo_gongga"}


# ==================== 边界测试 ====================


class TestViewpointConfigEdgeCases:
    """ViewpointConfig 边界情况测试。"""

    def test_empty_directory(self, tmp_path):
        """加载空目录 → 空列表 (不报错)。"""
        empty_dir = tmp_path / "empty_viewpoints"
        empty_dir.mkdir()
        vpc = ViewpointConfig()
        vpc.load(str(empty_dir))
        assert vpc.list_all() == []
