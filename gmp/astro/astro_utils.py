"""GMP 天文计算工具

使用 ephem 库实现日出/日落、月相、观星窗口计算。
设计依据: design/07-code-interface.md §7.1 IAstroCalculator
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

import ephem

from gmp.core.models import MoonStatus, StargazingWindow, SunEvents

# UTC+8 北京时间
_CST = timezone(timedelta(hours=8))


class AstroUtils:
    """天文计算工具"""

    @staticmethod
    def _make_observer(
        lat: float, lon: float, dt: date | datetime
    ) -> ephem.Observer:
        """创建 ephem Observer 对象

        Args:
            lat: 纬度 (°)
            lon: 经度 (°)
            dt: 日期或日期时间

        Returns:
            配置好的 Observer
        """
        obs = ephem.Observer()
        obs.lat = str(lat)
        obs.lon = str(lon)
        obs.pressure = 0  # 忽略大气折射修正（天文计算标准）
        if isinstance(dt, datetime):
            obs.date = ephem.Date(dt.astimezone(timezone.utc))
        else:
            # 对于 date 对象，设置为该日 UTC 前夜 (前一天 20:00 UTC = 当天 04:00 CST)
            # 确保 next_rising 能捕获当天的日出
            obs.date = ephem.Date(
                datetime(dt.year, dt.month, dt.day, 0, 0, 0)
                - timedelta(hours=4)
            )
        return obs

    @staticmethod
    def _ephem_to_datetime(ephem_date: ephem.Date) -> datetime:
        """将 ephem.Date 转换为 CST datetime

        Args:
            ephem_date: ephem 日期对象 (UTC)

        Returns:
            北京时间 datetime
        """
        utc_dt = ephem.Date(ephem_date).datetime().replace(tzinfo=timezone.utc)
        return utc_dt.astimezone(_CST)

    def get_sun_events(
        self, lat: float, lon: float, target_date: date
    ) -> SunEvents:
        """计算指定地点和日期的日出/日落信息

        Args:
            lat: 纬度 (°)
            lon: 经度 (°)
            target_date: 目标日期

        Returns:
            SunEvents: 包含 sunrise, sunset, sunrise_azimuth, sunset_azimuth,
                       astronomical_dawn, astronomical_dusk
        """
        # ---- 日出/日落 ----
        obs = self._make_observer(lat, lon, target_date)
        sun = ephem.Sun()

        sunrise_ephem = obs.next_rising(sun, use_center=True)
        # 计算日出方位角：将 observer 时间设为日出时刻
        obs_az = self._make_observer(lat, lon, target_date)
        obs_az.date = sunrise_ephem
        sun_az = ephem.Sun()
        sun_az.compute(obs_az)
        sunrise_azimuth = math.degrees(float(sun_az.az))

        # 日落：从日出之后开始搜索
        obs_set = self._make_observer(lat, lon, target_date)
        obs_set.date = sunrise_ephem  # 从日出后开始找日落
        sun_set = ephem.Sun()
        sunset_ephem = obs_set.next_setting(sun_set, use_center=True)
        obs_set.date = sunset_ephem
        sun_set.compute(obs_set)
        sunset_azimuth = math.degrees(float(sun_set.az))

        # ---- 天文晨暮曦 (太阳低于地平线 18°) ----
        obs_astro = self._make_observer(lat, lon, target_date)
        obs_astro.horizon = "-18"
        sun_astro = ephem.Sun()

        # 天文晨光：日出前太阳从 -18° 升起的时刻
        astronomical_dawn_ephem = obs_astro.next_rising(
            sun_astro, use_center=True
        )
        # 天文暮曦：日落后太阳降到 -18° 的时刻
        astronomical_dusk_ephem = obs_astro.next_setting(
            sun_astro, use_center=True
        )

        return SunEvents(
            sunrise=self._ephem_to_datetime(sunrise_ephem),
            sunset=self._ephem_to_datetime(sunset_ephem),
            sunrise_azimuth=sunrise_azimuth,
            sunset_azimuth=sunset_azimuth,
            astronomical_dawn=self._ephem_to_datetime(astronomical_dawn_ephem),
            astronomical_dusk=self._ephem_to_datetime(astronomical_dusk_ephem),
        )

    def get_moon_status(
        self, lat: float, lon: float, dt: datetime
    ) -> MoonStatus:
        """计算指定时刻的月球状态

        Args:
            lat: 纬度 (°)
            lon: 经度 (°)
            dt: 指定时刻 (带时区)

        Returns:
            MoonStatus: 包含 phase(0-100), elevation, moonrise, moonset
        """
        obs = self._make_observer(lat, lon, dt)
        moon = ephem.Moon()
        moon.compute(obs)

        # 月相: ephem.phase 返回 0-100
        phase = int(round(moon.phase))
        # 月球仰角 (°)
        elevation = math.degrees(float(moon.alt))

        # 月出/月落 —— 可能抛出 NeverUpError / AlwaysUpError
        moonrise = None
        moonset = None
        try:
            mr = obs.next_rising(ephem.Moon())
            moonrise = self._ephem_to_datetime(mr)
        except (ephem.NeverUpError, ephem.AlwaysUpError):
            pass

        try:
            ms = obs.next_setting(ephem.Moon())
            moonset = self._ephem_to_datetime(ms)
        except (ephem.NeverUpError, ephem.AlwaysUpError):
            pass

        return MoonStatus(
            phase=phase,
            elevation=elevation,
            moonrise=moonrise,
            moonset=moonset,
        )

    def determine_stargazing_window(
        self, sun_events: SunEvents, moon_status: MoonStatus
    ) -> StargazingWindow:
        """根据日落/月相/月出月落确定最佳观星时间窗口

        判定逻辑（优先级从高到低）:
        1. optimal: 月亮在地平线下期间
            → max(astro_dusk, moonset) ~ min(astro_dawn, moonrise)
        2. good: 月相 < 50%
            → astro_dusk ~ astro_dawn
        3. partial: 月相 ≥ 50% 但有月下时段
            → moonset ~ astro_dawn
        4. poor: 满月整夜

        Args:
            sun_events: 日出日落事件数据
            moon_status: 月球状态数据

        Returns:
            StargazingWindow: 观星窗口信息
        """
        astro_dusk = sun_events.astronomical_dusk
        astro_dawn = sun_events.astronomical_dawn
        moonrise = moon_status.moonrise
        moonset = moon_status.moonset
        phase = moon_status.phase

        # Case 1: optimal — 月相较小且月亮在夜间有「不在天上」的时段
        if phase < 50 and moonset is not None and moonrise is not None:
            # 月亮在 dusk 之前已落 或 在 dusk~dawn 间有落/升
            optimal_start = max(astro_dusk, moonset) if moonset > astro_dusk else astro_dusk
            optimal_end = min(astro_dawn, moonrise) if moonrise < astro_dawn else astro_dawn

            # 只有当窗口有效（start < end）时才算 optimal
            if optimal_start < optimal_end:
                return StargazingWindow(
                    optimal_start=optimal_start,
                    optimal_end=optimal_end,
                    good_start=astro_dusk,
                    good_end=astro_dawn,
                    quality="optimal",
                )

        # Case 2: good — 月相 < 50%，即使没有最佳无月窗口
        if phase < 50:
            return StargazingWindow(
                good_start=astro_dusk,
                good_end=astro_dawn,
                quality="good",
            )

        # Case 3: partial — 月相 ≥ 50% 但有月落时段
        if moonset is not None and moonset > astro_dusk:
            # 月落后到天亮前是无月时段
            if moonset < astro_dawn:
                return StargazingWindow(
                    optimal_start=moonset,
                    optimal_end=astro_dawn,
                    quality="partial",
                )

        # Case 4: poor — 满月整夜
        return StargazingWindow(quality="poor")
