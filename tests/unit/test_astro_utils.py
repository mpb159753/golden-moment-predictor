"""tests/unit/test_astro_utils.py — AstroUtils 天文计算工具 单元测试"""

from datetime import date, datetime, timedelta, timezone

import pytest

from gmp.core.models import MoonStatus, StargazingWindow, SunEvents
from gmp.data.astro_utils import AstroUtils

# 牛背山坐标
NIUBEI_LAT = 29.6014
NIUBEI_LON = 102.3689

# UTC+8 时区
CST = timezone(timedelta(hours=8))


class TestGetSunEvents:
    """Task 1: get_sun_events — 日出日落+天文晨暮曦

    期望值基于 ephem 库天文计算 (horizon=-0:34, 含大气折射)。
    牛背山 (29.6014°N, 102.3689°E), 2026-02-11:
    - Sunrise ≈ 07:50 CST
    - Sunset  ≈ 19:00 CST
    - Dawn    ≈ 06:20 CST
    - Dusk    ≈ 20:30 CST
    """

    def test_sunrise_time_niubei_20260211(self) -> None:
        """牛背山 2026-02-11 日出 ≈ 07:50 CST (容差 ±10 min)"""
        result = AstroUtils.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        assert isinstance(result, SunEvents)
        expected_sunrise = datetime(2026, 2, 11, 7, 50, tzinfo=CST)
        delta = abs((result.sunrise - expected_sunrise).total_seconds())
        assert delta < 600, f"Sunrise {result.sunrise} 偏差 {delta}s > 600s"

    def test_sunset_time_niubei_20260211(self) -> None:
        """牛背山 2026-02-11 日落 ≈ 19:00 CST (容差 ±10 min)"""
        result = AstroUtils.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        expected_sunset = datetime(2026, 2, 11, 19, 0, tzinfo=CST)
        delta = abs((result.sunset - expected_sunset).total_seconds())
        assert delta < 600, f"Sunset {result.sunset} 偏差 {delta}s > 600s"

    def test_sunrise_azimuth_niubei_20260211(self) -> None:
        """牛背山 2026-02-11 日出方位角 ≈ 108.5° (东偏南, 容差 ±5°)"""
        result = AstroUtils.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        assert abs(result.sunrise_azimuth - 108.5) < 5, (
            f"Sunrise azimuth {result.sunrise_azimuth}° 偏差 > 5°"
        )

    def test_sunset_azimuth_niubei_20260211(self) -> None:
        """牛背山 2026-02-11 日落方位角 ≈ 251.5° (西偏南, 容差 ±5°)"""
        result = AstroUtils.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        assert abs(result.sunset_azimuth - 251.5) < 5, (
            f"Sunset azimuth {result.sunset_azimuth}° 偏差 > 5°"
        )

    def test_astronomical_dawn_before_sunrise(self) -> None:
        """天文晨曦应早于日出 (约 06:20 CST, 容差 ±20 min)"""
        result = AstroUtils.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        assert result.astronomical_dawn < result.sunrise, (
            "astronomical_dawn 应早于 sunrise"
        )
        expected_dawn = datetime(2026, 2, 11, 6, 20, tzinfo=CST)
        delta = abs((result.astronomical_dawn - expected_dawn).total_seconds())
        assert delta < 1200, f"Dawn {result.astronomical_dawn} 偏差 {delta}s > 1200s"

    def test_astronomical_dusk_after_sunset(self) -> None:
        """天文暮曦应晚于日落 (约 20:30 CST, 容差 ±20 min)"""
        result = AstroUtils.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))

        assert result.astronomical_dusk > result.sunset, (
            "astronomical_dusk 应晚于 sunset"
        )
        expected_dusk = datetime(2026, 2, 11, 20, 30, tzinfo=CST)
        delta = abs((result.astronomical_dusk - expected_dusk).total_seconds())
        assert delta < 1200, f"Dusk {result.astronomical_dusk} 偏差 {delta}s > 1200s"

    def test_return_type_is_sun_events(self) -> None:
        """返回类型应为 SunEvents dataclass"""
        result = AstroUtils.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))
        assert isinstance(result, SunEvents)

    def test_all_datetimes_are_timezone_aware(self) -> None:
        """所有返回的 datetime 应有时区信息"""
        result = AstroUtils.get_sun_events(NIUBEI_LAT, NIUBEI_LON, date(2026, 2, 11))
        for field_name in ["sunrise", "sunset", "astronomical_dawn", "astronomical_dusk"]:
            dt = getattr(result, field_name)
            assert dt.tzinfo is not None, f"{field_name} 缺少时区信息"


class TestGetMoonStatus:
    """Task 2: get_moon_status — 月相月出月落

    期望值基于 ephem 库天文计算。
    牛背山 (29.6014°N, 102.3689°E), 2026-02-11 00:00 CST:
    - phase ≈ 39-40%
    - moonrise ≈ 03:04 CST (当天)
    - moonset ≈ 13:10 CST (当天)
    """

    def test_phase_niubei_20260211(self) -> None:
        """2026-02-11 月相 ≈ 35-45% (下弦月前)"""
        dt = datetime(2026, 2, 11, 0, 0, 0, tzinfo=CST)
        result = AstroUtils.get_moon_status(NIUBEI_LAT, NIUBEI_LON, dt)

        assert isinstance(result, MoonStatus)
        assert 30 <= result.phase <= 50, f"Phase {result.phase}% 不在 30-50 范围"

    def test_elevation_at_midnight(self) -> None:
        """午夜月球仰角应为负值 (月球在地平线下)"""
        dt = datetime(2026, 2, 11, 0, 0, 0, tzinfo=CST)
        result = AstroUtils.get_moon_status(NIUBEI_LAT, NIUBEI_LON, dt)

        assert result.elevation < 0, f"Elevation {result.elevation}° 应 < 0 (午夜月球在地下)"

    def test_moonrise_time(self) -> None:
        """月出应在当天早晨 ≈ 03:04 CST (容差 ±30 min)"""
        dt = datetime(2026, 2, 11, 0, 0, 0, tzinfo=CST)
        result = AstroUtils.get_moon_status(NIUBEI_LAT, NIUBEI_LON, dt)

        assert result.moonrise is not None
        expected = datetime(2026, 2, 11, 3, 4, tzinfo=CST)
        delta = abs((result.moonrise - expected).total_seconds())
        assert delta < 1800, f"Moonrise {result.moonrise} 偏差 {delta}s > 1800s"

    def test_moonset_time(self) -> None:
        """月落应在当天下午 ≈ 13:10 CST (容差 ±30 min)"""
        dt = datetime(2026, 2, 11, 0, 0, 0, tzinfo=CST)
        result = AstroUtils.get_moon_status(NIUBEI_LAT, NIUBEI_LON, dt)

        assert result.moonset is not None
        expected = datetime(2026, 2, 11, 13, 10, tzinfo=CST)
        delta = abs((result.moonset - expected).total_seconds())
        assert delta < 1800, f"Moonset {result.moonset} 偏差 {delta}s > 1800s"

    def test_full_moon_phase(self) -> None:
        """满月 (2026-03-03) phase ≈ 100"""
        dt = datetime(2026, 3, 3, 12, 0, 0, tzinfo=CST)
        result = AstroUtils.get_moon_status(NIUBEI_LAT, NIUBEI_LON, dt)

        assert result.phase >= 95, f"Full moon phase {result.phase}% 应 >= 95"

    def test_new_moon_phase(self) -> None:
        """新月 (2026-02-17) phase ≈ 0"""
        dt = datetime(2026, 2, 17, 12, 0, 0, tzinfo=CST)
        result = AstroUtils.get_moon_status(NIUBEI_LAT, NIUBEI_LON, dt)

        assert result.phase <= 5, f"New moon phase {result.phase}% 应 <= 5"


class TestDetermineStargazingWindow:
    """Task 3: determine_stargazing_window — 观星窗口判定

    使用构造的 SunEvents + MoonStatus 测试不同场景。
    规则:
    - optimal: 月亮在夜间有下落时段 → max(dusk, moonset) ~ min(dawn, moonrise)
    - good: 月相 < 50% (弦月以下) → dusk ~ dawn
    - partial: 月相 ≥ 50% 但月落在夜间 → moonset ~ dawn
    - poor: 满月整夜
    """

    def _make_sun_events(
        self,
        dusk_hour: int = 20,
        dusk_min: int = 0,
        dawn_hour: int = 6,
        dawn_min: int = 0,
    ) -> SunEvents:
        """构造 SunEvents 辅助方法"""
        return SunEvents(
            sunrise=datetime(2026, 2, 11, 7, 50, tzinfo=CST),
            sunset=datetime(2026, 2, 11, 19, 0, tzinfo=CST),
            sunrise_azimuth=108.0,
            sunset_azimuth=252.0,
            astronomical_dawn=datetime(2026, 2, 12, dawn_hour, dawn_min, tzinfo=CST),
            astronomical_dusk=datetime(2026, 2, 11, dusk_hour, dusk_min, tzinfo=CST),
        )

    def test_optimal_moon_sets_during_daytime(self) -> None:
        """月落白天 (13:40), 月相 35% → quality='optimal'

        月亮在日落前就落下，整个暗夜无月干扰。
        optimal_start = dusk (20:00), optimal_end = dawn (06:00)
        """
        sun = self._make_sun_events(dusk_hour=20, dawn_hour=6)
        moon = MoonStatus(
            phase=35,
            elevation=-20.0,
            moonrise=datetime(2026, 2, 11, 3, 15, tzinfo=CST),
            moonset=datetime(2026, 2, 11, 13, 40, tzinfo=CST),
        )

        result = AstroUtils.determine_stargazing_window(sun, moon)

        assert isinstance(result, StargazingWindow)
        assert result.quality == "optimal"
        assert result.optimal_start is not None
        assert result.optimal_end is not None

    def test_good_low_phase_moon_all_night(self) -> None:
        """月相 40%, 月亮整夜在天 (moonset=None) → quality='good'

        弦月以下，虽有月光但影响有限。
        good_start = dusk, good_end = dawn
        """
        sun = self._make_sun_events(dusk_hour=20, dawn_hour=6)
        moon = MoonStatus(
            phase=40,
            elevation=30.0,
            moonrise=None,
            moonset=None,
        )

        result = AstroUtils.determine_stargazing_window(sun, moon)

        assert result.quality == "good"
        assert result.good_start is not None
        assert result.good_end is not None

    def test_partial_high_phase_moonset_at_night(self) -> None:
        """月相 70%, 月落 02:00 → quality='partial'

        月亮占了前半夜，但后半夜月落后可观。
        """
        sun = self._make_sun_events(dusk_hour=20, dawn_hour=6)
        moon = MoonStatus(
            phase=70,
            elevation=40.0,
            moonrise=datetime(2026, 2, 11, 15, 0, tzinfo=CST),
            moonset=datetime(2026, 2, 12, 2, 0, tzinfo=CST),
        )

        result = AstroUtils.determine_stargazing_window(sun, moon)

        assert result.quality == "partial"

    def test_poor_full_moon_all_night(self) -> None:
        """月相 95%, 月亮整夜 → quality='poor'"""
        sun = self._make_sun_events(dusk_hour=20, dawn_hour=6)
        moon = MoonStatus(
            phase=95,
            elevation=50.0,
            moonrise=None,
            moonset=None,
        )

        result = AstroUtils.determine_stargazing_window(sun, moon)

        assert result.quality == "poor"
        assert result.optimal_start is None
        assert result.optimal_end is None

