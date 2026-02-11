"""GeoUtils 地理计算工具单元测试

测试基于牛背山→贡嘎的真实数据验证：
  - 牛背山坐标: (29.75, 102.35), 海拔 3660m
  - 贡嘎主峰坐标: (29.58, 101.88), 海拔 7556m
  - 预期方位角: ≈ 245° (±5°)
  - 预期距离: ≈ 51km (±5km)
"""

import pytest

from gmp.astro.geo_utils import GeoUtils

# ---- 固定测试数据 ----
NIUBEI_LAT, NIUBEI_LON = 29.75, 102.35
GONGGA_LAT, GONGGA_LON = 29.58, 101.88
FEB_SUNRISE_AZIMUTH = 108.5  # 2月日出方位角 (°)


class TestCalculateBearing:
    """方位角计算测试"""

    def test_bearing_niubei_to_gongga(self):
        """牛背山→贡嘎方位角 ≈ 245° (±5°)"""
        bearing = GeoUtils.calculate_bearing(
            NIUBEI_LAT, NIUBEI_LON, GONGGA_LAT, GONGGA_LON
        )
        assert 240 <= bearing <= 250, f"方位角 {bearing}° 不在 240-250° 范围"

    def test_bearing_range(self):
        """方位角应在 [0, 360) 范围"""
        bearing = GeoUtils.calculate_bearing(0, 0, 1, 1)
        assert 0 <= bearing < 360


class TestCalculateDistance:
    """距离计算测试"""

    def test_distance_niubei_to_gongga(self):
        """牛背山到贡嘎距离 ≈ 51km (±5km)"""
        distance = GeoUtils.calculate_distance(
            NIUBEI_LAT, NIUBEI_LON, GONGGA_LAT, GONGGA_LON
        )
        assert 46 <= distance <= 56, f"距离 {distance}km 不在 46-56km 范围"


class TestCalculateDestination:
    """终点坐标计算测试"""

    def test_destination_accuracy(self):
        """已知起点+距离+方位角 → 终点坐标误差 < 0.01°"""
        # 从牛背山出发，向东（90°）走 100km，验证反向计算一致性
        dest_lat, dest_lon = GeoUtils.calculate_destination(
            NIUBEI_LAT, NIUBEI_LON, 100, 90
        )
        # 反向计算距离应约为 100km
        reverse_dist = GeoUtils.calculate_distance(
            NIUBEI_LAT, NIUBEI_LON, dest_lat, dest_lon
        )
        assert abs(reverse_dist - 100) < 0.5, f"反向距离 {reverse_dist}km 误差过大"

        # 反向方位角应约为 90°
        reverse_bearing = GeoUtils.calculate_bearing(
            NIUBEI_LAT, NIUBEI_LON, dest_lat, dest_lon
        )
        assert abs(reverse_bearing - 90) < 1, f"反向方位角 {reverse_bearing}° 误差过大"


class TestLightPathPoints:
    """光路检查点生成测试"""

    def test_light_path_10points(self):
        """方位角108.5°起点(29.75, 102.35) → 返回 10 个坐标，间隔约 10km"""
        points = GeoUtils.calculate_light_path_points(
            NIUBEI_LAT, NIUBEI_LON, FEB_SUNRISE_AZIMUTH, count=10, interval_km=10
        )
        assert len(points) == 10

        # 第 1 个点距起点约 10km
        dist_first = GeoUtils.calculate_distance(
            NIUBEI_LAT, NIUBEI_LON, points[0][0], points[0][1]
        )
        assert 9 <= dist_first <= 11, f"首点距离 {dist_first}km 不在 9-11km 范围"

        # 最后一个点距起点约 100km
        dist_last = GeoUtils.calculate_distance(
            NIUBEI_LAT, NIUBEI_LON, points[-1][0], points[-1][1]
        )
        assert 99 <= dist_last <= 101, f"末点距离 {dist_last}km 不在 99-101km 范围"


class TestIsOppositeDirection:
    """方向匹配测试"""

    def test_is_opposite_true(self):
        """bearing=245°, azimuth=108.5° → True (贡嘎适配 sunrise)"""
        result = GeoUtils.is_opposite_direction(245, FEB_SUNRISE_AZIMUTH)
        assert result is True

    def test_is_opposite_false(self):
        """bearing=100°, azimuth=108.5° → False"""
        result = GeoUtils.is_opposite_direction(100, FEB_SUNRISE_AZIMUTH)
        assert result is False

    def test_angle_wrap_around(self):
        """角度环绕: 350° 和 10° 对面方向(190°) → 夹角 = 160°，不匹配"""
        # bearing=350°, sun_azimuth=10° → opposite=190°
        # |350 - 190| = 160° > 90° → False
        result = GeoUtils.is_opposite_direction(350, 10)
        assert result is False

        # bearing=5°, sun_azimuth=10° → opposite=190°
        # |5 - 190| = 185° → 360-185 = 175° > 90° → False
        result2 = GeoUtils.is_opposite_direction(5, 10)
        assert result2 is False

        # bearing=200°, sun_azimuth=10° → opposite=190°
        # |200 - 190| = 10° < 90° → True
        result3 = GeoUtils.is_opposite_direction(200, 10)
        assert result3 is True


class TestRoundCoords:
    """坐标取整测试"""

    def test_round_coords(self):
        """(29.756, 102.344) → (29.76, 102.34)"""
        lat, lon = GeoUtils.round_coords(29.756, 102.344)
        assert lat == 29.76
        assert lon == 102.34

    def test_round_coords_custom_precision(self):
        """自定义精度"""
        lat, lon = GeoUtils.round_coords(29.755, 102.349, precision=1)
        assert lat == 29.8
        assert lon == 102.3
