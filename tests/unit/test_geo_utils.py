"""tests/unit/test_geo_utils.py — GeoUtils 地理计算工具 单元测试"""

import math

import pytest

from gmp.data.geo_utils import GeoUtils


# ==================== test_calculate_bearing ====================


class TestCalculateBearing:
    """方位角计算测试"""

    def test_niubeishan_to_gongga(self):
        """牛背山 → 贡嘎主峰，方位角应 ≈ 245° (西南方向)"""
        bearing = GeoUtils.calculate_bearing(29.75, 102.35, 29.58, 101.88)
        assert 240 <= bearing <= 250, f"期望 ≈245°, 实际 {bearing:.1f}°"

    def test_due_north(self):
        """正北方向: (0, 0) → (1, 0) ≈ 0°"""
        bearing = GeoUtils.calculate_bearing(0, 0, 1, 0)
        assert bearing == pytest.approx(0, abs=0.1)

    def test_due_east(self):
        """正东方向: (0, 0) → (0, 1) ≈ 90°"""
        bearing = GeoUtils.calculate_bearing(0, 0, 0, 1)
        assert bearing == pytest.approx(90, abs=0.1)

    def test_same_point(self):
        """相同点: 不报错即可"""
        bearing = GeoUtils.calculate_bearing(29.75, 102.35, 29.75, 102.35)
        assert 0 <= bearing <= 360 or bearing == 0


# ==================== test_calculate_distance ====================


class TestCalculateDistance:
    """两点间距离计算测试"""

    def test_niubeishan_to_gongga(self):
        """牛背山 → 贡嘎: ≈ 50-55km"""
        distance = GeoUtils.calculate_distance(29.75, 102.35, 29.58, 101.88)
        assert 45 <= distance <= 60, f"期望 50-55km, 实际 {distance:.1f}km"

    def test_same_point(self):
        """同一点: 0km"""
        distance = GeoUtils.calculate_distance(29.75, 102.35, 29.75, 102.35)
        assert distance == pytest.approx(0, abs=0.01)

    def test_equator_one_degree(self):
        """赤道上经度相差1°: ≈ 111km"""
        distance = GeoUtils.calculate_distance(0, 0, 0, 1)
        assert distance == pytest.approx(111, abs=2)


# ==================== test_calculate_destination ====================


class TestCalculateDestination:
    """目标点推算测试"""

    def test_east_from_origin(self):
        """从 (0, 0) 向东走 111km ≈ (0, 1)"""
        lat, lon = GeoUtils.calculate_destination(0, 0, 111, 90)
        assert lat == pytest.approx(0, abs=0.1)
        assert lon == pytest.approx(1, abs=0.1)

    def test_from_niubeishan(self):
        """从牛背山沿 108.5° 走 10km，验证坐标在合理范围"""
        lat, lon = GeoUtils.calculate_destination(29.75, 102.35, 10, 108.5)
        # 向东偏南走 10km，纬度略减，经度略增
        assert 29.6 <= lat <= 29.8
        assert 102.35 <= lon <= 102.50


# ==================== test_calculate_light_path_points ====================


class TestCalculateLightPathPoints:
    """光路检查点生成测试"""

    def test_returns_correct_count(self):
        """返回恰好 count 个坐标"""
        points = GeoUtils.calculate_light_path_points(
            29.75, 102.35, azimuth=108.5, count=10, interval_km=10
        )
        assert len(points) == 10

    def test_distances_are_incremental(self):
        """每个坐标到起点的距离依次约为 10km, 20km, ..., 100km"""
        points = GeoUtils.calculate_light_path_points(
            29.75, 102.35, azimuth=108.5, count=10, interval_km=10
        )
        for i, (lat, lon) in enumerate(points, start=1):
            expected_km = i * 10
            actual_km = GeoUtils.calculate_distance(29.75, 102.35, lat, lon)
            assert actual_km == pytest.approx(
                expected_km, abs=2
            ), f"第{i}个点距离应 ≈{expected_km}km, 实际 {actual_km:.1f}km"

    def test_coords_are_rounded(self):
        """坐标已四舍五入到 2 位小数"""
        points = GeoUtils.calculate_light_path_points(
            29.75, 102.35, azimuth=108.5, count=5, interval_km=10
        )
        for lat, lon in points:
            assert lat == round(lat, 2), f"纬度 {lat} 未四舍五入到 2 位小数"
            assert lon == round(lon, 2), f"经度 {lon} 未四舍五入到 2 位小数"


# ==================== test_is_opposite_direction ====================


class TestIsOppositeDirection:
    """方向对面判断测试"""

    def test_sunrise_matching(self):
        """bearing=245°, azimuth=108.5° → True (目标在日出对面)"""
        assert GeoUtils.is_opposite_direction(245, 108.5) is True

    def test_same_side_as_sun(self):
        """bearing=90°, azimuth=108.5° → False (目标在太阳同侧)"""
        assert GeoUtils.is_opposite_direction(90, 108.5) is False

    def test_sunset_not_matching(self):
        """bearing=250°, azimuth=251.5° → False (日落场景不匹配)"""
        assert GeoUtils.is_opposite_direction(250, 251.5) is False


# ==================== test_round_coords ====================


class TestRoundCoords:
    """坐标精度截取测试"""

    def test_default_precision(self):
        """默认精度 2 位"""
        assert GeoUtils.round_coords(29.756, 102.349) == (29.76, 102.35)

    def test_round_down(self):
        """向下取整"""
        assert GeoUtils.round_coords(29.751, 102.354) == (29.75, 102.35)

    def test_precision_zero(self):
        """精度 0"""
        assert GeoUtils.round_coords(29.755, 102.349, precision=0) == (30.0, 102.0)
