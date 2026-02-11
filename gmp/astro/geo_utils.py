"""GMP 地理计算工具

基于 Haversine 公式实现方位角、距离、目的地坐标计算，
以及光路检查点生成和方向匹配逻辑。
设计依据: design/07-code-interface.md §7.1 IGeoCalculator
"""

import math

# 地球平均半径 (km)
EARTH_RADIUS_KM = 6371.0


class GeoUtils:
    """地理计算工具（全部为静态/类方法）"""

    @staticmethod
    def calculate_bearing(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """计算两点间的方位角 (0°=北, 90°=东, 180°=南, 270°=西)

        公式: Haversine 初始方位角公式
            θ = atan2(sin(Δlon)·cos(lat2),
                      cos(lat1)·sin(lat2) − sin(lat1)·cos(lat2)·cos(Δlon))

        Args:
            lat1: 起点纬度 (°)
            lon1: 起点经度 (°)
            lat2: 终点纬度 (°)
            lon2: 终点经度 (°)

        Returns:
            方位角，单位度，范围 [0, 360)
        """
        φ1 = math.radians(lat1)
        φ2 = math.radians(lat2)
        Δλ = math.radians(lon2 - lon1)

        x = math.sin(Δλ) * math.cos(φ2)
        y = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(Δλ)

        θ = math.atan2(x, y)
        return (math.degrees(θ) + 360) % 360

    @staticmethod
    def calculate_distance(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """计算两点间的地球表面距离 (km)

        公式: Haversine 距离公式
            a = sin²(Δφ/2) + cos(φ1)·cos(φ2)·sin²(Δλ/2)
            c = 2·atan2(√a, √(1−a))
            d = R·c

        Args:
            lat1: 起点纬度 (°)
            lon1: 起点经度 (°)
            lat2: 终点纬度 (°)
            lon2: 终点经度 (°)

        Returns:
            距离，单位 km
        """
        φ1 = math.radians(lat1)
        φ2 = math.radians(lat2)
        Δφ = math.radians(lat2 - lat1)
        Δλ = math.radians(lon2 - lon1)

        a = (
            math.sin(Δφ / 2) ** 2
            + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return EARTH_RADIUS_KM * c

    @staticmethod
    def calculate_destination(
        lat: float, lon: float, distance_km: float, bearing: float
    ) -> tuple[float, float]:
        """给定起点、距离和方位角，计算终点坐标

        公式: 正向大地测量
            φ2 = asin(sin(φ1)·cos(d/R) + cos(φ1)·sin(d/R)·cos(θ))
            λ2 = λ1 + atan2(sin(θ)·sin(d/R)·cos(φ1),
                            cos(d/R) − sin(φ1)·sin(φ2))

        Args:
            lat: 起点纬度 (°)
            lon: 起点经度 (°)
            distance_km: 距离 (km)
            bearing: 方位角 (°)

        Returns:
            (lat, lon) 终点坐标
        """
        φ1 = math.radians(lat)
        λ1 = math.radians(lon)
        θ = math.radians(bearing)
        δ = distance_km / EARTH_RADIUS_KM  # 角距离

        φ2 = math.asin(
            math.sin(φ1) * math.cos(δ) + math.cos(φ1) * math.sin(δ) * math.cos(θ)
        )
        λ2 = λ1 + math.atan2(
            math.sin(θ) * math.sin(δ) * math.cos(φ1),
            math.cos(δ) - math.sin(φ1) * math.sin(φ2),
        )

        return (math.degrees(φ2), math.degrees(λ2))

    @staticmethod
    def calculate_light_path_points(
        lat: float,
        lon: float,
        azimuth: float,
        count: int = 10,
        interval_km: float = 10,
    ) -> list[tuple[float, float]]:
        """沿太阳方位角方向生成光路检查点

        第 1 个点距起点 interval_km，第 N 个点距起点 N*interval_km。

        Args:
            lat: 起点纬度 (°)
            lon: 起点经度 (°)
            azimuth: 太阳方位角 (°)
            count: 检查点数量（默认 10）
            interval_km: 检查点间距（默认 10km）

        Returns:
            [(lat1, lon1), (lat2, lon2), ...] 共 count 个点
        """
        points: list[tuple[float, float]] = []
        for i in range(1, count + 1):
            distance = i * interval_km
            point = GeoUtils.calculate_destination(lat, lon, distance, azimuth)
            points.append(point)
        return points

    @staticmethod
    def is_opposite_direction(
        bearing_to_target: float, sun_azimuth: float
    ) -> bool:
        """判断山峰是否在太阳的对面方向

        逻辑:
        - 计算太阳方位角的对面 = (sun_azimuth + 180) % 360
        - 若 bearing_to_target 与对面方向夹角 < 90°，则适配

        注意: 正确处理角度环绕（如 350° 和 10° 的夹角是 20°）

        Args:
            bearing_to_target: 观景台到目标的方位角 (°)
            sun_azimuth: 太阳方位角 (°)

        Returns:
            True 如果目标在太阳对面
        """
        opposite = (sun_azimuth + 180) % 360
        diff = abs(bearing_to_target - opposite)
        # 处理角度环绕: 350° 和 10° 的夹角应为 20° 不是 340°
        if diff > 180:
            diff = 360 - diff
        return diff < 90

    @staticmethod
    def round_coords(
        lat: float, lon: float, precision: int = 2
    ) -> tuple[float, float]:
        """坐标取整（用于缓存 key 生成）

        Args:
            lat: 纬度
            lon: 经度
            precision: 小数位数（默认 2，约 1km 精度）

        Returns:
            (rounded_lat, rounded_lon)
        """
        return (round(lat, precision), round(lon, precision))
