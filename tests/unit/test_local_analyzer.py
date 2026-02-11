"""L1 本地滤网 (LocalAnalyzer) 单元测试

验证:
- 安全检查一票否决
- 云海判定
- 雾凇判定
- 夜间云量计算
- 树挂积雪 8 个派生指标
- 冰挂 5 个派生指标
"""

import pandas as pd
import pytest

from gmp.analyzer.local_analyzer import LocalAnalyzer
from gmp.core.config_loader import EngineConfig


@pytest.fixture
def config() -> EngineConfig:
    """默认引擎配置"""
    return EngineConfig()


@pytest.fixture
def analyzer(config: EngineConfig) -> LocalAnalyzer:
    """默认 LocalAnalyzer 实例"""
    return LocalAnalyzer(config)


def _make_hourly_df(hour: int = 7, **kwargs) -> pd.DataFrame:
    """创建单行天气数据 DataFrame"""
    row = {
        "forecast_hour": hour,
        "temperature_2m": 5.0,
        "cloud_cover_total": 20,
        "cloud_cover_low": 10,
        "cloud_cover_medium": 5,
        "cloud_cover_high": 5,
        "precipitation_probability": 10,
        "visibility": 35000,
        "wind_speed_10m": 8.0,
        "weather_code": 0,
        "snowfall": 0.0,
        "rain": 0.0,
        "showers": 0.0,
    }
    row.update(kwargs)
    return pd.DataFrame([row])


def _make_history_df(hours: int = 24, **overrides) -> pd.DataFrame:
    """创建多小时天气历史 DataFrame"""
    rows = []
    for h in range(hours):
        row = {
            "forecast_hour": h % 24,
            "temperature_2m": -2.0,
            "cloud_cover_total": 20,
            "cloud_cover_low": 10,
            "cloud_cover_medium": 5,
            "cloud_cover_high": 5,
            "precipitation_probability": 10,
            "visibility": 35000,
            "wind_speed_10m": 8.0,
            "weather_code": 0,
            "snowfall": 0.0,
            "rain": 0.0,
            "showers": 0.0,
        }
        # 应用每行覆盖
        for key, values in overrides.items():
            if isinstance(values, list) and h < len(values):
                row[key] = values[h]
            elif not isinstance(values, list):
                row[key] = values
        rows.append(row)
    return pd.DataFrame(rows)


# ============================================================
# 安全检查测试
# ============================================================


class TestSafetyCheck:
    """安全检查 (一票否决) 测试"""

    def test_safety_pass(self, analyzer: LocalAnalyzer):
        """降水0%, 能见度35km → passed=True"""
        data = _make_hourly_df(
            precipitation_probability=0,
            visibility=35000,
        )
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.passed is True
        assert result.details["safety"]["passed"] is True

    def test_safety_precip_veto(self, analyzer: LocalAnalyzer):
        """降水70% → passed=False (超过 50% 阈值)"""
        data = _make_hourly_df(
            precipitation_probability=70,
            visibility=35000,
        )
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.passed is False
        assert result.details["safety"]["passed"] is False
        assert result.score == 0
        assert "安全" in result.reason

    def test_safety_visibility_veto(self, analyzer: LocalAnalyzer):
        """能见度500m → passed=False (低于 1000m 阈值)"""
        data = _make_hourly_df(
            precipitation_probability=10,
            visibility=500,
        )
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.passed is False
        assert result.details["safety"]["passed"] is False
        assert result.score == 0

    def test_safety_borderline_precip(self, analyzer: LocalAnalyzer):
        """降水恰好50% (不 < 50) → passed=False"""
        data = _make_hourly_df(
            precipitation_probability=50,
            visibility=35000,
        )
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.passed is False

    def test_safety_missing_hour(self, analyzer: LocalAnalyzer):
        """目标小时不存在 → passed=False"""
        data = _make_hourly_df(hour=8)  # 只有 8 点数据
        context = {"site_altitude": 3660, "target_hour": 7}  # 需要 7 点
        result = analyzer.analyze(data, context)

        assert result.passed is False
        assert "无法获取" in result.reason


# ============================================================
# 云海判定测试
# ============================================================


class TestCloudSea:
    """云海判定测试"""

    def test_cloud_sea_detected(self, analyzer: LocalAnalyzer):
        """云底2600m, 站点3660m → cloud_sea=True, gap=1060"""
        data = _make_hourly_df(cloud_base_altitude=2600)
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.passed is True
        cloud_sea = result.details["cloud_sea"]
        assert cloud_sea["detected"] is True
        assert cloud_sea["gap"] == 1060

    def test_cloud_sea_negative(self, analyzer: LocalAnalyzer):
        """云底5000m, 站点3660m → cloud_sea=False"""
        data = _make_hourly_df(cloud_base_altitude=5000)
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.passed is True
        cloud_sea = result.details["cloud_sea"]
        assert cloud_sea["detected"] is False
        assert cloud_sea["gap"] == 0

    def test_cloud_sea_estimated_high_low_cloud(self, analyzer: LocalAnalyzer):
        """低云量 70% → 云底估算约在站点以下 → 检测到云海"""
        data = _make_hourly_df(cloud_cover_low=70)
        # 去掉 cloud_base_altitude 字段
        data = data.drop(columns=["cloud_base_altitude"], errors="ignore")
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        # 低云量 70% → 云底约 3660 - (70-50)*20 = 3260m < 3660
        assert result.details["cloud_sea"]["detected"] is True


# ============================================================
# 雾凇判定测试
# ============================================================


class TestFrost:
    """雾凇判定测试"""

    def test_frost_detected(self, analyzer: LocalAnalyzer):
        """温度-3.8°C → frost=True"""
        data = _make_hourly_df(temperature_2m=-3.8)
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.passed is True
        frost = result.details["frost"]
        assert frost["detected"] is True
        assert frost["temperature"] == -3.8

    def test_frost_too_warm(self, analyzer: LocalAnalyzer):
        """温度5°C → frost=False"""
        data = _make_hourly_df(temperature_2m=5.0)
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        frost = result.details["frost"]
        assert frost["detected"] is False

    def test_frost_borderline(self, analyzer: LocalAnalyzer):
        """温度恰好2°C (不 < 2) → frost=False"""
        data = _make_hourly_df(temperature_2m=2.0)
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        frost = result.details["frost"]
        assert frost["detected"] is False


# ============================================================
# 夜间云量测试
# ============================================================


class TestNightCloudCover:
    """夜间 (20:00-05:00) 平均云量测试"""

    def test_night_cloud_cover(self, analyzer: LocalAnalyzer):
        """夜间平均云量正确计算"""
        # 创建 24 小时数据：夜间时段 (20-23, 0-5) 设定不同云量
        cloud_values = [0] * 24
        # 00-05: 设为 40
        for h in range(6):
            cloud_values[h] = 40
        # 20-23: 设为 60
        for h in range(20, 24):
            cloud_values[h] = 60

        data = _make_history_df(
            hours=24,
            cloud_cover_total=cloud_values,
        )
        context = {"site_altitude": 3660, "target_hour": 7}

        # 直接测试内部方法
        night_cloud = analyzer._compute_night_cloud_cover(data)

        # 夜间小时: 0,1,2,3,4,5 (值40) + 20,21,22,23 (值60)
        # 平均 = (6*40 + 4*60) / 10 = (240 + 240) / 10 = 48
        assert night_cloud == pytest.approx(48.0)


# ============================================================
# 树挂积雪派生指标测试
# ============================================================


class TestSnowTreeIndicators:
    """树挂积雪派生指标计算测试"""

    def test_snow_tree_indicators(self, analyzer: LocalAnalyzer):
        """已知降雪历史 → 正确计算派生指标"""
        # 24 小时数据：第 10-14 小时有降雪，之后转晴零下
        snowfall = [0.0] * 24
        snowfall[10] = 2.0  # 10:00 降雪 2cm
        snowfall[11] = 3.0  # 11:00 降雪 3cm
        snowfall[12] = 1.5  # 12:00 降雪 1.5cm
        snowfall[13] = 0.5  # 13:00 降雪 0.5cm
        snowfall[14] = 1.0  # 14:00 降雪 1.0cm

        temp = [0.0] * 24
        for i in range(24):
            temp[i] = -5.0 if i < 15 else -3.0  # 降雪后持续零下
        temp[20] = 1.0  # 20:00 短暂升温

        wind = [5.0] * 24
        wind[18] = 15.0  # 18:00 风速峰值

        cloud = [80] * 24
        for i in range(15, 24):
            cloud[i] = 5  # 降雪后转晴 (< 10 → sunshine += 2)

        data = _make_history_df(
            hours=24,
            snowfall=snowfall,
            temperature_2m=temp,
            wind_speed_10m=wind,
            cloud_cover_total=cloud,
        )

        indicators = analyzer._compute_snow_tree_indicators(data)

        # 近 12 小时 (12-23): 1.5 + 0.5 + 1.0 = 3.0
        assert indicators["recent_snowfall_12h_cm"] == pytest.approx(3.0)

        # 近 24 小时: 2.0 + 3.0 + 1.5 + 0.5 + 1.0 = 8.0
        assert indicators["recent_snowfall_24h_cm"] == pytest.approx(8.0)

        # 最后降雪 idx=14, 当前 idx=23 → hours_since = 23 - 14 - 1 = 8 (不对，应是 n-idx-1 = 24-14-1 = 9)
        assert indicators["hours_since_last_snow"] == pytest.approx(9.0)

        # 24 小时内降雪小时数: 5
        assert indicators["snowfall_duration_h_24h"] == 5

        # 降雪后 (idx 15-23) 零下小时数: temp 都 < 0 除了 idx 20 (1.0°C)
        # idx 15-19: -3, -3, -3, -3, -3 → 5 个零下
        # idx 20: 1.0 → 不零下
        # idx 21-23: -3, -3, -3 → 3 个零下
        # 总计 8 个零下
        assert indicators["subzero_hours_since_last_snow"] == 8

        # 降雪后最高温度: 1.0 (idx 20)
        assert indicators["max_temp_since_last_snow"] == pytest.approx(1.0)

        # 降雪后最大风速: 15.0 (idx 18)
        assert indicators["max_wind_since_last_snow"] == pytest.approx(15.0)

        # 日照时数: idx 15-23 云量都是 5 (< 10 → +2 each)
        # 9 小时 * 2 = 18
        assert indicators["sunshine_hours_since_snow"] == pytest.approx(18.0)

    def test_snow_tree_no_snowfall(self, analyzer: LocalAnalyzer):
        """无降雪历史 → 默认值"""
        data = _make_history_df(hours=24)
        indicators = analyzer._compute_snow_tree_indicators(data)

        assert indicators["recent_snowfall_12h_cm"] == 0.0
        assert indicators["recent_snowfall_24h_cm"] == 0.0
        assert indicators["hours_since_last_snow"] == 999.0

    def test_snow_tree_recent_snow(self, analyzer: LocalAnalyzer):
        """最后一行就是降雪 → hours_since = 0"""
        snowfall = [0.0] * 24
        snowfall[23] = 5.0  # 最后一小时降雪

        data = _make_history_df(hours=24, snowfall=snowfall)
        indicators = analyzer._compute_snow_tree_indicators(data)

        assert indicators["hours_since_last_snow"] == 0.0
        assert indicators["recent_snowfall_12h_cm"] == pytest.approx(5.0)


# ============================================================
# 冰挂派生指标测试
# ============================================================


class TestIceIcicleIndicators:
    """冰挂派生指标计算测试"""

    def test_ice_icicle_indicators(self, analyzer: LocalAnalyzer):
        """已知降水+冻结 → 正确计算派生指标"""
        rain = [0.0] * 24
        rain[8] = 2.0   # 08:00 降雨 2mm
        rain[9] = 1.5   # 09:00 降雨 1.5mm

        showers = [0.0] * 24
        showers[10] = 0.5  # 10:00 阵雨 0.5mm

        snowfall = [0.0] * 24
        snowfall[11] = 1.0  # 11:00 降雪 1cm (= 1mm 水当量)

        temp = [0.0] * 24
        for i in range(24):
            temp[i] = -2.0  # 全天零下
        temp[15] = 0.5  # 15:00 短暂升温

        data = _make_history_df(
            hours=24,
            rain=rain,
            showers=showers,
            snowfall=snowfall,
            temperature_2m=temp,
        )

        indicators = analyzer._compute_ice_icicle_indicators(data)

        # 有效水源 24h: rain(2+1.5) + showers(0.5) + snowfall(1.0*1.0) = 5.0
        assert indicators["effective_water_input_24h_mm"] == pytest.approx(5.0)

        # 有效水源 12h (12-23): 无降水 → 0
        assert indicators["effective_water_input_12h_mm"] == pytest.approx(0.0)

        # 最后有效水源 idx=11, n=24 → hours_since = 24 - 11 - 1 = 12
        assert indicators["hours_since_last_water_input"] == pytest.approx(12.0)

        # 水源后 (idx 12-23) 零下: 全部 -2 除 idx 15 (0.5)
        # 12 个小时中 11 个零下
        assert indicators["subzero_hours_since_last_water"] == 11

        # 水源后最高温: 0.5 (idx 15)
        assert indicators["max_temp_since_last_water"] == pytest.approx(0.5)

    def test_ice_icicle_no_water(self, analyzer: LocalAnalyzer):
        """无水源输入 → 默认值"""
        data = _make_history_df(hours=24)
        indicators = analyzer._compute_ice_icicle_indicators(data)

        assert indicators["effective_water_input_12h_mm"] == 0.0
        assert indicators["effective_water_input_24h_mm"] == 0.0
        assert indicators["hours_since_last_water_input"] == 999.0


# ============================================================
# 综合评分测试
# ============================================================


class TestLocalScore:
    """L1 综合评分测试"""

    def test_high_score_conditions(self, analyzer: LocalAnalyzer):
        """云海+雾凇+低云+低风 → 高分"""
        data = _make_hourly_df(
            cloud_base_altitude=2600,
            temperature_2m=-5.0,
            cloud_cover_total=10,
            wind_speed_10m=5.0,
        )
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        # 50 (基础) + 15 (云海) + 10 (雾凇) + 15 (低云) + 10 (低风) = 100
        assert result.score == 100

    def test_moderate_score(self, analyzer: LocalAnalyzer):
        """无云海无雾凇 → 中等分"""
        data = _make_hourly_df(
            cloud_base_altitude=5000,
            temperature_2m=10.0,
            cloud_cover_total=20,
            wind_speed_10m=8.0,
        )
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        # 50 + 0 + 0 + 15 + 10 = 75
        assert result.score == 75


# ============================================================
# T3 云底估算分支覆盖测试
# ============================================================


class TestCloudBaseEstimation:
    """测试 _estimate_cloud_base_altitude 的三个分支 (T3)"""

    def test_cloud_sea_estimated_low_low_cloud(self, analyzer: LocalAnalyzer):
        """低云量 10% (<20%) → 云底远高于站点 → 无云海

        估算: site_altitude + 2000 = 3660 + 2000 = 5660m > 3660m
        """
        data = _make_hourly_df(cloud_cover_low=10)
        data = data.drop(columns=["cloud_base_altitude"], errors="ignore")
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.details["cloud_sea"]["detected"] is False

    def test_cloud_sea_estimated_mid_low_cloud(self, analyzer: LocalAnalyzer):
        """低云量 35% (20-50%线性插值) → 云底在站点以上 → 无云海

        估算: ratio = (50-35)/30 = 0.5 → 3660 + 0.5*2000 = 4660m > 3660m
        """
        data = _make_hourly_df(cloud_cover_low=35)
        data = data.drop(columns=["cloud_base_altitude"], errors="ignore")
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.details["cloud_sea"]["detected"] is False
        # 验证估算值: cloud_base ≈ 4660
        assert result.details["cloud_base_altitude"] == pytest.approx(4660, abs=1)


# ============================================================
# T1 matched_targets 方位角匹配测试
# ============================================================


class TestMatchedTargets:
    """测试 matched_targets 字段输出 (T1)"""

    def test_matched_targets_with_sun_events(self, analyzer: LocalAnalyzer):
        """提供 viewpoint + sun_events → 方位角匹配返回 matched_targets"""
        from dataclasses import dataclass
        from gmp.core.models import Location, Target, Viewpoint

        @dataclass
        class FakeSunEvents:
            sunrise_azimuth: float = 108.5
            sunset_azimuth: float = 251.5

        viewpoint = Viewpoint(
            id="test",
            name="牛背山",
            location=Location(lat=29.75, lon=102.35, altitude=3660),
            capabilities=["sunrise"],
            targets=[
                Target(
                    name="贡嘎主峰", lat=29.58, lon=101.88,
                    altitude=7556, weight="primary",
                    applicable_events=None,
                ),
            ],
        )

        data = _make_hourly_df()
        context = {
            "site_altitude": 3660,
            "target_hour": 7,
            "viewpoint": viewpoint,
            "sun_events": FakeSunEvents(),
        }
        result = analyzer.analyze(data, context)

        matched = result.details["matched_targets"]
        assert len(matched) > 0
        # 贡嘎在西南方(~245°), 日出对面是~288.5°, |245-288.5|=43.5° < 90° → 匹配 sunrise
        assert any(
            "sunrise_golden_mountain" in m["matched_events"]
            for m in matched
        )

    def test_matched_targets_no_sun_events(self, analyzer: LocalAnalyzer):
        """不提供 sun_events → matched_targets 为空列表"""
        from gmp.core.models import Location, Target, Viewpoint

        viewpoint = Viewpoint(
            id="test", name="牛背山",
            location=Location(lat=29.75, lon=102.35, altitude=3660),
            capabilities=["sunrise"],
            targets=[
                Target(
                    name="贡嘎主峰", lat=29.58, lon=101.88,
                    altitude=7556, weight="primary",
                    applicable_events=None,
                ),
            ],
        )

        data = _make_hourly_df()
        context = {
            "site_altitude": 3660,
            "target_hour": 7,
            "viewpoint": viewpoint,
            # 没有 sun_events
        }
        result = analyzer.analyze(data, context)

        # 无天文数据 → 自动计算的 matched_events 为空 → 不加入 results
        assert result.details["matched_targets"] == []

    def test_matched_targets_no_viewpoint(self, analyzer: LocalAnalyzer):
        """不提供 viewpoint → matched_targets 为空列表"""
        data = _make_hourly_df()
        context = {"site_altitude": 3660, "target_hour": 7}
        result = analyzer.analyze(data, context)

        assert result.details["matched_targets"] == []

