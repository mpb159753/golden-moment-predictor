"""gmp/data/geo_utils.py — 地理坐标计算工具类

纯计算工具类，所有方法为 @staticmethod，无状态。
服务于日照金山方位角判断、光路检查点生成、缓存坐标去重等场景。
"""

import math


_EARTH_RADIUS_KM = 6371.0


class GeoUtils:
    """地理计算工具 — 方位角、距离、目的地推算、光路检查点生成"""

    @staticmethod
    def calculate_bearing(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """计算从点1到点2的初始方位角 (0°=北, 90°=东, 180°=南, 270°=西)。

        使用 Haversine 公式的方位角变体。
        """
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        d_lon = math.radians(lon2 - lon1)

        x = math.sin(d_lon) * math.cos(lat2_r)
        y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(
            lat2_r
        ) * math.cos(d_lon)

        bearing = math.degrees(math.atan2(x, y))
        return bearing % 360

    @staticmethod
    def calculate_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """返回两点间距离（单位: km），使用 Haversine 公式。"""
        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(d_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return _EARTH_RADIUS_KM * c

    @staticmethod
    def calculate_destination(
        lat: float, lon: float, distance_km: float, bearing: float
    ) -> tuple[float, float]:
        """从起点沿给定方位角和距离推算目标点坐标。

        使用球面三角公式。返回 (lat, lon)。
        """
        lat_r = math.radians(lat)
        lon_r = math.radians(lon)
        bearing_r = math.radians(bearing)
        d = distance_km / _EARTH_RADIUS_KM  # 角距离

        new_lat = math.asin(
            math.sin(lat_r) * math.cos(d)
            + math.cos(lat_r) * math.sin(d) * math.cos(bearing_r)
        )
        new_lon = lon_r + math.atan2(
            math.sin(bearing_r) * math.sin(d) * math.cos(lat_r),
            math.cos(d) - math.sin(lat_r) * math.sin(new_lat),
        )

        return (math.degrees(new_lat), math.degrees(new_lon))

    @staticmethod
    def calculate_light_path_points(
        lat: float,
        lon: float,
        azimuth: float,
        count: int = 10,
        interval_km: float = 10,
    ) -> list[tuple[float, float]]:
        """沿方位角方向生成检查点坐标列表。

        从起点开始每隔 interval_km 生成一个点，共 count 个（不含起点）。
        每个坐标四舍五入到 2 位小数。
        """
        points: list[tuple[float, float]] = []
        for i in range(1, count + 1):
            dist = i * interval_km
            new_lat, new_lon = GeoUtils.calculate_destination(
                lat, lon, dist, azimuth
            )
            points.append(GeoUtils.round_coords(new_lat, new_lon))
        return points

    @staticmethod
    def is_opposite_direction(
        bearing_to_target: float, sun_azimuth: float
    ) -> bool:
        """判断目标方位角是否在太阳方位角的"对面"。

        日出场景: 光从太阳方向来 (azimuth)，照射对面 (azimuth+180°±90°) 的山峰。
        逻辑: |bearing_to_target - (sun_azimuth + 180)°| < 90°（考虑 360° 环绕）。
        """
        opposite = (sun_azimuth + 180) % 360
        diff = abs(bearing_to_target - opposite) % 360
        if diff > 180:
            diff = 360 - diff
        return diff < 90

    @staticmethod
    def round_coords(
        lat: float, lon: float, precision: int = 2
    ) -> tuple[float, float]:
        """将坐标四舍五入到指定小数位（默认 2 位 ≈ 1km 精度）。"""
        return (round(lat, precision), round(lon, precision))
