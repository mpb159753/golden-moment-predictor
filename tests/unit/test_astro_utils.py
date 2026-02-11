"""AstroUtils 天文计算工具单元测试

测试基于牛背山 (29.75°N, 102.35°E) 的真实天文数据验证。
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from gmp.astro.astro_utils import AstroUtils
from gmp.core.exceptions import InvalidCoordinateError
from gmp.core.models import MoonStatus, StargazingWindow, SunEvents

# ---- 固定测试数据 ----
NIUBEI_LAT, NIUBEI_LON = 29.75, 102.35
CST = timezone(timedelta(hours=8))


@pytest.fixture
def astro():
    """AstroUtils 实例 fixture"""
    return AstroUtils()


class TestGetSunEvents:
    """日出/日落计算测试"""

    def test_sun_events_niubei_feb11(self, astro):
        """2026-02-11 牛背山日出 ≈ 07:28, 日落 ≈ 18:35 (±15min)"""
        events = astro.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        # 日出时间应在 07:00 ~ 08:00 CST
        assert events.sunrise.hour in (7,), (
            f"日出时间 {events.sunrise} 不在预期范围"
        )

        # 日落时间应在 18:00 ~ 19:00 CST
        assert events.sunset.hour in (18, 19), (
            f"日落时间 {events.sunset} 不在预期范围"
        )

        # 日出应早于日落
        assert events.sunrise < events.sunset

    def test_sunrise_azimuth_feb(self, astro):
        """2月日出方位角 ≈ 105°-115° (偏南)"""
        events = astro.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        assert 100 <= events.sunrise_azimuth <= 120, (
            f"日出方位角 {events.sunrise_azimuth}° 不在 100-120° 范围"
        )

    def test_sunset_azimuth_feb(self, astro):
        """2月日落方位角 ≈ 240°-260° (偏西南)"""
        events = astro.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        assert 240 <= events.sunset_azimuth <= 260, (
            f"日落方位角 {events.sunset_azimuth}° 不在 240-260° 范围"
        )

    def test_astronomical_dawn_dusk(self, astro):
        """天文晨暮曦应满足: dawn < sunrise < sunset < dusk"""
        events = astro.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        assert events.astronomical_dawn < events.sunrise, (
            f"天文晨光 {events.astronomical_dawn} 应早于日出 {events.sunrise}"
        )
        assert events.sunset < events.astronomical_dusk, (
            f"日落 {events.sunset} 应早于天文暮曦 {events.astronomical_dusk}"
        )


class TestGetMoonStatus:
    """月球状态测试"""

    def test_moon_phase_range(self, astro):
        """moon_status.phase 在 0-100 之间"""
        dt = datetime(2026, 2, 11, 20, 0, 0, tzinfo=CST)
        status = astro.get_moon_status(NIUBEI_LAT, NIUBEI_LON, dt)

        assert 0 <= status.phase <= 100, (
            f"月相 {status.phase} 不在 0-100 范围"
        )

    def test_moon_elevation_range(self, astro):
        """月球仰角应在合理范围内"""
        dt = datetime(2026, 2, 11, 20, 0, 0, tzinfo=CST)
        status = astro.get_moon_status(NIUBEI_LAT, NIUBEI_LON, dt)

        assert -90 <= status.elevation <= 90, (
            f"月球仰角 {status.elevation}° 不在 -90~90° 范围"
        )


class TestDetermineStargazingWindow:
    """观星窗口判定测试"""

    def test_stargazing_optimal(self, astro):
        """残月 + 夜间有无月窗口 → quality="optimal"

        构造场景: 月相 20%（残月），月落在白天(14:00)，月出在次日 02:00
        → dusk(20:10) 到 moonrise(02:00) 整段无月 → "optimal"
        """
        sun_events = SunEvents(
            sunrise=datetime(2026, 2, 11, 7, 28, tzinfo=CST),
            sunset=datetime(2026, 2, 11, 18, 35, tzinfo=CST),
            sunrise_azimuth=108.5,
            sunset_azimuth=251.0,
            astronomical_dawn=datetime(2026, 2, 12, 5, 50, tzinfo=CST),
            astronomical_dusk=datetime(2026, 2, 11, 20, 10, tzinfo=CST),
        )
        # 残月，月出在次日 02:00，月落在当天 14:00（白天）
        moon_status = MoonStatus(
            phase=20,
            elevation=-30.0,
            moonrise=datetime(2026, 2, 12, 2, 0, tzinfo=CST),
            moonset=datetime(2026, 2, 11, 14, 0, tzinfo=CST),
        )

        window = astro.determine_stargazing_window(sun_events, moon_status)
        assert window.quality == "optimal", (
            f"残月+夜间无月应为 optimal，实际 {window.quality}"
        )
        # 验证窗口时间: max(dusk=20:10, moonset=14:00)=20:10 ~ min(dawn=05:50, moonrise=02:00)=02:00
        assert window.optimal_start == datetime(2026, 2, 11, 20, 10, tzinfo=CST)
        assert window.optimal_end == datetime(2026, 2, 12, 2, 0, tzinfo=CST)

    def test_stargazing_good(self, astro):
        """月相 < 50% 但无有效 optimal 窗口 → quality="good"

        构造场景: 月相 30%，月出在 19:00（dusk 之前），月落在 05:00（dawn 之后）
        → 月亮整夜在天上，但月相低 → 没有有效 optimal 窗口 → "good"
        """
        sun_events = SunEvents(
            sunrise=datetime(2026, 2, 11, 7, 28, tzinfo=CST),
            sunset=datetime(2026, 2, 11, 18, 35, tzinfo=CST),
            sunrise_azimuth=108.5,
            sunset_azimuth=251.0,
            astronomical_dawn=datetime(2026, 2, 12, 5, 50, tzinfo=CST),
            astronomical_dusk=datetime(2026, 2, 11, 20, 10, tzinfo=CST),
        )
        # 月相 30%，月出 19:00（dusk前），月落次日 06:00（dawn后）
        # → optimal_start = max(20:10, 06:00(次日)) → 06:00(次日)
        # → optimal_end = min(05:50(次日), 19:00) → 这里 moonrise=19:00 < dusk=20:10
        #   实际上 moonset 在次日 06:00 > dawn 05:50，所以
        #   optimal_start = max(dusk=20:10, moonset=次日06:00) = 次日06:00
        #   optimal_end = min(dawn=次日05:50, moonrise=19:00) = 19:00
        #   start(06:00) > end(19:00 当天) → 窗口无效 → fallback to "good"
        moon_status = MoonStatus(
            phase=30,
            elevation=25.0,
            moonrise=datetime(2026, 2, 11, 19, 0, tzinfo=CST),
            moonset=datetime(2026, 2, 12, 6, 0, tzinfo=CST),
        )

        window = astro.determine_stargazing_window(sun_events, moon_status)
        assert window.quality == "good", (
            f"月相低但整夜有月应为 good，实际 {window.quality}"
        )
        assert window.good_start == datetime(2026, 2, 11, 20, 10, tzinfo=CST)
        assert window.good_end == datetime(2026, 2, 12, 5, 50, tzinfo=CST)

    def test_stargazing_poor(self, astro):
        """满月整夜 → quality="poor"

        构造场景: 月相 98%（满月），月出在日落前、月落在日出后
        → 整夜有满月 → "poor"
        """
        sun_events = SunEvents(
            sunrise=datetime(2026, 2, 11, 7, 28, tzinfo=CST),
            sunset=datetime(2026, 2, 11, 18, 35, tzinfo=CST),
            sunrise_azimuth=108.5,
            sunset_azimuth=251.0,
            astronomical_dawn=datetime(2026, 2, 11, 5, 50, tzinfo=CST),
            astronomical_dusk=datetime(2026, 2, 11, 20, 10, tzinfo=CST),
        )
        # 满月整夜: 月出 17:00（日落前），月落次日 07:30（日出后）
        moon_status = MoonStatus(
            phase=98,
            elevation=45.0,
            moonrise=datetime(2026, 2, 11, 17, 0, tzinfo=CST),
            moonset=datetime(2026, 2, 12, 7, 30, tzinfo=CST),
        )

        window = astro.determine_stargazing_window(sun_events, moon_status)
        assert window.quality == "poor", (
            f"满月整夜应为 poor，实际 {window.quality}"
        )

    def test_stargazing_partial(self, astro):
        """月相 ≥ 50% 但有月落在夜间 → quality="partial"

        构造场景: 月相 75%，月落在 01:00（夜间），月出在前一天
        → 01:00 到天文晨光之间无月 → "partial"
        """
        sun_events = SunEvents(
            sunrise=datetime(2026, 2, 11, 7, 28, tzinfo=CST),
            sunset=datetime(2026, 2, 11, 18, 35, tzinfo=CST),
            sunrise_azimuth=108.5,
            sunset_azimuth=251.0,
            astronomical_dawn=datetime(2026, 2, 12, 5, 50, tzinfo=CST),
            astronomical_dusk=datetime(2026, 2, 11, 20, 10, tzinfo=CST),
        )
        # 月相 75%, 月落 01:00 (在 dusk 之后, dawn 之前)
        moon_status = MoonStatus(
            phase=75,
            elevation=30.0,
            moonrise=datetime(2026, 2, 11, 15, 0, tzinfo=CST),
            moonset=datetime(2026, 2, 12, 1, 0, tzinfo=CST),
        )

        window = astro.determine_stargazing_window(sun_events, moon_status)
        assert window.quality == "partial", (
            f"月相 75% 月落夜间应为 partial，实际 {window.quality}"
        )


class TestInputValidation:
    """输入参数校验测试"""

    def test_invalid_latitude(self, astro):
        """纬度超出 [-90, 90] 应抛出 InvalidCoordinateError"""
        with pytest.raises(InvalidCoordinateError):
            astro.get_sun_events(91.0, 102.35, date(2026, 2, 11))

    def test_invalid_longitude(self, astro):
        """经度超出 [-180, 180] 应抛出 InvalidCoordinateError"""
        with pytest.raises(InvalidCoordinateError):
            astro.get_sun_events(29.75, 181.0, date(2026, 2, 11))

    def test_invalid_coords_moon_status(self, astro):
        """get_moon_status 同样应校验坐标"""
        dt = datetime(2026, 2, 11, 20, 0, 0, tzinfo=CST)
        with pytest.raises(InvalidCoordinateError):
            astro.get_moon_status(-95.0, 102.35, dt)
