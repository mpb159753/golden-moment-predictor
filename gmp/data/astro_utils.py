"""gmp/data/astro_utils.py — 天文计算工具类

使用 ephem 库进行日出日落、月相、观星窗口等天文计算。
所有方法为 @staticmethod，无状态。
"""

from datetime import date, datetime, timedelta, timezone

import ephem

from gmp.core.models import MoonStatus, StargazingWindow, SunEvents

# UTC+8 时区
_CST = timezone(timedelta(hours=8))


class AstroUtils:
    """天文计算工具 — 日出日落、月相、观星窗口"""

    @staticmethod
    def get_sun_events(lat: float, lon: float, target_date: date) -> SunEvents:
        """计算指定坐标和日期的日出日落+天文晨暮曦。

        Args:
            lat: 纬度
            lon: 经度
            target_date: 目标日期（本地日期）

        Returns:
            SunEvents 包含日出/日落时刻及方位角、天文晨暮曦
        """
        observer = ephem.Observer()
        observer.lat = str(lat)
        observer.lon = str(lon)
        observer.elevation = 0
        # 设置日期为目标日期的 UTC 零点（即 CST 当天 00:00 - 8h = 前一天 16:00 UTC）
        observer.date = ephem.Date(datetime(target_date.year, target_date.month,
                                            target_date.day, 0, 0, 0) - timedelta(hours=8))

        sun = ephem.Sun()

        # 标准地平线 + 大气折射 → 日出/日落
        observer.horizon = "-0:34"
        sunrise_utc = observer.next_rising(sun).datetime()
        observer.date = ephem.Date(datetime(target_date.year, target_date.month,
                                            target_date.day, 0, 0, 0) - timedelta(hours=8))
        sunset_utc = observer.next_setting(sun).datetime()

        # 计算日出方位角: 将 observer 时间设为日出时刻然后计算
        observer.date = sunrise_utc
        sun.compute(observer)
        sunrise_azimuth = float(sun.az) * 180.0 / 3.141592653589793

        # 计算日落方位角
        observer.date = sunset_utc
        sun.compute(observer)
        sunset_azimuth = float(sun.az) * 180.0 / 3.141592653589793

        # 天文晨暮曦 (太阳 -18°)
        observer.horizon = "-18"
        observer.date = ephem.Date(datetime(target_date.year, target_date.month,
                                            target_date.day, 0, 0, 0) - timedelta(hours=8))
        dawn_utc = observer.next_rising(sun, use_center=True).datetime()
        observer.date = ephem.Date(datetime(target_date.year, target_date.month,
                                            target_date.day, 0, 0, 0) - timedelta(hours=8))
        dusk_utc = observer.next_setting(sun, use_center=True).datetime()

        return SunEvents(
            sunrise=sunrise_utc.replace(tzinfo=timezone.utc).astimezone(_CST),
            sunset=sunset_utc.replace(tzinfo=timezone.utc).astimezone(_CST),
            sunrise_azimuth=sunrise_azimuth,
            sunset_azimuth=sunset_azimuth,
            astronomical_dawn=dawn_utc.replace(tzinfo=timezone.utc).astimezone(_CST),
            astronomical_dusk=dusk_utc.replace(tzinfo=timezone.utc).astimezone(_CST),
        )

    @staticmethod
    def get_moon_status(lat: float, lon: float, dt: datetime) -> MoonStatus:
        """计算指定时刻的月球状态。

        Args:
            lat: 纬度
            lon: 经度
            dt: 目标时刻（须含时区信息）

        Returns:
            MoonStatus 包含月相百分比、仰角、月出/月落时刻
        """
        observer = ephem.Observer()
        observer.lat = str(lat)
        observer.lon = str(lon)
        observer.elevation = 0
        # 转换为 UTC
        dt_utc = dt.astimezone(timezone.utc)
        observer.date = dt_utc.strftime("%Y/%m/%d %H:%M:%S")

        moon = ephem.Moon(observer)

        phase = int(round(moon.phase))
        elevation = float(moon.alt) * 180.0 / 3.141592653589793

        # 查找当天的月出/月落
        # 从 CST 当天 00:00 开始搜索，找 next_rising/next_setting
        day_start_cst = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end_cst = day_start_cst + timedelta(days=1)
        day_start_utc = day_start_cst.astimezone(timezone.utc)

        moonrise = None
        moonset = None

        observer.date = day_start_utc.strftime("%Y/%m/%d %H:%M:%S")
        try:
            mr = observer.next_rising(moon)
            mr_dt = mr.datetime().replace(tzinfo=timezone.utc).astimezone(_CST)
            if mr_dt < day_end_cst:
                moonrise = mr_dt
        except ephem.NeverUpError:
            pass
        except ephem.AlwaysUpError:
            pass

        observer.date = day_start_utc.strftime("%Y/%m/%d %H:%M:%S")
        try:
            ms = observer.next_setting(moon)
            ms_dt = ms.datetime().replace(tzinfo=timezone.utc).astimezone(_CST)
            if ms_dt < day_end_cst:
                moonset = ms_dt
        except ephem.NeverUpError:
            pass
        except ephem.AlwaysUpError:
            pass

        return MoonStatus(
            phase=phase,
            elevation=round(elevation, 2),
            moonrise=moonrise,
            moonset=moonset,
        )

    @staticmethod
    def determine_stargazing_window(
        sun_events: SunEvents, moon_status: MoonStatus,
    ) -> StargazingWindow:
        """判定观星窗口质量和时间范围。

        优先级判定:
        🥇 optimal: 暗夜期间有无月时段
        🥈 good: 月相 < 50% (弦月以下) → 月光影响有限
        🥉 partial: 月相 ≥ 50% 但月落在夜间 → 月落后可观
        ❌ poor: 高月相 + 月亮整夜在天

        Args:
            sun_events: 日出日落信息（含天文晨暮曦）
            moon_status: 月球状态

        Returns:
            StargazingWindow 包含窗口时间和质量等级
        """
        dusk = sun_events.astronomical_dusk
        dawn = sun_events.astronomical_dawn
        phase = moon_status.phase

        # 只考虑夜间 (dusk~dawn) 范围内的月出/月落事件
        moonrise_night = moon_status.moonrise if (
            moon_status.moonrise and dusk < moon_status.moonrise < dawn
        ) else None
        moonset_night = moon_status.moonset if (
            moon_status.moonset and dusk < moon_status.moonset < dawn
        ) else None

        # 判断月亮是否在暗夜前已落下 (moonset <= dusk)
        moon_down_before_dusk = (
            moon_status.moonset is not None and moon_status.moonset <= dusk
        )

        # 确定无月暗夜时段
        if moonset_night is None and moonrise_night is None:
            if moon_down_before_dusk:
                # 月亮在暗夜前落下，整夜无月 → optimal
                return StargazingWindow(
                    optimal_start=dusk,
                    optimal_end=dawn,
                    good_start=dusk,
                    good_end=dawn,
                    quality="optimal",
                )
            # 月亮整夜在天（或无事件信息）
            if phase < 50:
                return StargazingWindow(
                    optimal_start=None,
                    optimal_end=None,
                    good_start=dusk,
                    good_end=dawn,
                    quality="good",
                )
            return StargazingWindow(
                optimal_start=None,
                optimal_end=None,
                good_start=None,
                good_end=None,
                quality="poor",
            )

        # 有夜间月落/月出 → 计算无月时段
        if moonset_night and moonrise_night:
            # 月出和月落都在夜间
            if moonset_night < moonrise_night:
                # 月落先 → moonset~moonrise 无月
                dark_start, dark_end = moonset_night, moonrise_night
            else:
                # 月出先 → dusk~moonrise 和 moonset~dawn 两段，取较长
                seg1 = (dusk, moonrise_night)
                seg2 = (moonset_night, dawn)
                dark_start, dark_end = max(
                    [seg1, seg2], key=lambda s: (s[1] - s[0]).total_seconds()
                )
        elif moonset_night:
            # 只有月落在夜间 → moonset ~ dawn
            dark_start, dark_end = moonset_night, dawn
        else:
            # 只有月出在夜间 → dusk ~ moonrise
            dark_start, dark_end = dusk, moonrise_night  # type: ignore[assignment]

        if phase < 50:
            return StargazingWindow(
                optimal_start=dark_start,
                optimal_end=dark_end,
                good_start=dusk,
                good_end=dawn,
                quality="optimal",
            )
        else:
            return StargazingWindow(
                optimal_start=None,
                optimal_end=None,
                good_start=dark_start,
                good_end=dark_end,
                quality="partial",
            )
