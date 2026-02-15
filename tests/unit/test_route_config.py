"""tests/unit/test_route_config.py — RouteConfig 单元测试

测试线路配置目录的加载、排序、查找、错误处理。
"""

import pytest
import yaml

from gmp.core.config_loader import RouteConfig
from gmp.core.exceptions import RouteNotFoundError
from gmp.core.models import Route, RouteStop


# ==================== Fixtures ====================


@pytest.fixture
def route_yaml() -> dict:
    """lixiao 线路配置。"""
    return {
        "id": "lixiao",
        "name": "理小路",
        "description": "理塘→小金/丹巴 经典自驾线路",
        "stops": [
            {
                "viewpoint_id": "niubei_gongga",
                "order": 2,
                "stay_note": "推荐过夜，可同时观测金山+云海+星空",
            },
            {
                "viewpoint_id": "zheduo_gongga",
                "order": 1,
                "stay_note": "建议日出前2小时到达",
            },
        ],
    }


@pytest.fixture
def second_route_yaml() -> dict:
    """第二条线路配置。"""
    return {
        "id": "chuanxi",
        "name": "川西环线",
        "description": "成都→康定→稻城 环线",
        "stops": [
            {
                "viewpoint_id": "niubei_gongga",
                "order": 1,
                "stay_note": "第一站",
            },
        ],
    }


@pytest.fixture
def route_dir(route_yaml, second_route_yaml, tmp_path):
    """创建包含两条线路 YAML 文件的临时目录。"""
    rt_dir = tmp_path / "routes"
    rt_dir.mkdir()
    (rt_dir / "lixiao.yaml").write_text(
        yaml.dump(route_yaml, allow_unicode=True)
    )
    (rt_dir / "chuanxi.yaml").write_text(
        yaml.dump(second_route_yaml, allow_unicode=True)
    )
    return str(rt_dir)


@pytest.fixture
def single_route_dir(route_yaml, tmp_path):
    """只包含一条线路的目录。"""
    rt_dir = tmp_path / "routes"
    rt_dir.mkdir()
    (rt_dir / "lixiao.yaml").write_text(
        yaml.dump(route_yaml, allow_unicode=True)
    )
    return str(rt_dir)


# ==================== 加载测试 ====================


class TestRouteConfigLoad:
    """RouteConfig 加载测试。"""

    def test_load_route_attributes(self, single_route_dir):
        """加载 lixiao.yaml → Route 属性完整。"""
        rc = RouteConfig()
        rc.load(single_route_dir)

        route = rc.get("lixiao")
        assert isinstance(route, Route)
        assert route.id == "lixiao"
        assert route.name == "理小路"
        assert route.description == "理塘→小金/丹巴 经典自驾线路"

    def test_load_stops(self, single_route_dir):
        """stops 正确转换为 RouteStop 对象。"""
        rc = RouteConfig()
        rc.load(single_route_dir)

        route = rc.get("lixiao")
        assert len(route.stops) == 2
        for stop in route.stops:
            assert isinstance(stop, RouteStop)

    def test_stops_sorted_by_order(self, single_route_dir):
        """stops 按 order 排序。"""
        rc = RouteConfig()
        rc.load(single_route_dir)

        route = rc.get("lixiao")
        assert route.stops[0].order == 1
        assert route.stops[0].viewpoint_id == "zheduo_gongga"
        assert route.stops[1].order == 2
        assert route.stops[1].viewpoint_id == "niubei_gongga"


# ==================== 查询测试 ====================


class TestRouteConfigQuery:
    """RouteConfig 查询测试。"""

    def test_get_existing(self, route_dir):
        """get('lixiao') 正常访问。"""
        rc = RouteConfig()
        rc.load(route_dir)
        route = rc.get("lixiao")
        assert route.id == "lixiao"

    def test_get_not_found(self, route_dir):
        """get('不存在') → RouteNotFoundError。"""
        rc = RouteConfig()
        rc.load(route_dir)
        with pytest.raises(RouteNotFoundError):
            rc.get("不存在")

    def test_list_all(self, route_dir):
        """list_all() 返回正确数量。"""
        rc = RouteConfig()
        rc.load(route_dir)
        all_routes = rc.list_all()
        assert len(all_routes) == 2
        ids = {r.id for r in all_routes}
        assert ids == {"lixiao", "chuanxi"}


# ==================== 边界测试 ====================


class TestRouteConfigEdgeCases:
    """RouteConfig 边界情况测试。"""

    def test_empty_directory(self, tmp_path):
        """加载空目录 → 空列表 (不报错)。"""
        empty_dir = tmp_path / "empty_routes"
        empty_dir.mkdir()
        rc = RouteConfig()
        rc.load(str(empty_dir))
        assert rc.list_all() == []
