"""extract_weather_value 公共工具函数单元测试

覆盖: 正常提取、列不存在、空 DataFrame、全 NaN、多行取首行、非 DataFrame 输入
"""

import math

import pandas as pd
import pytest

from gmp.scorer.plugin import extract_weather_value


class TestExtractWeatherValue:
    """T1: 验证公共数据提取函数的各种边界情况."""

    def test_normal_extraction(self):
        """正常 DataFrame, 提取首行值."""
        df = pd.DataFrame({"temperature_2m": [-3.0, -2.5, -1.0]})
        assert extract_weather_value(df, "temperature_2m", 999) == -3.0

    def test_column_not_exist(self):
        """列不存在 → 返回默认值."""
        df = pd.DataFrame({"wind_speed_10m": [5.0]})
        assert extract_weather_value(df, "temperature_2m", 999) == 999

    def test_empty_dataframe(self):
        """空 DataFrame (无行) → 返回默认值."""
        df = pd.DataFrame({"temperature_2m": pd.Series([], dtype=float)})
        assert extract_weather_value(df, "temperature_2m", -99.0) == -99.0

    def test_all_nan(self):
        """列全为 NaN → 返回默认值."""
        df = pd.DataFrame({"visibility": [float("nan"), float("nan")]})
        assert extract_weather_value(df, "visibility", 50000) == 50000

    def test_nan_then_value(self):
        """首行 NaN, 后面有值 → 取首个非空值."""
        df = pd.DataFrame({"cloud_cover_low": [float("nan"), 45.0, 60.0]})
        assert extract_weather_value(df, "cloud_cover_low", 0) == 45.0

    def test_multi_row_takes_first(self):
        """多行数据 → 取第一个非空值."""
        df = pd.DataFrame({"wind_speed_10m": [8.0, 12.0, 20.0]})
        assert extract_weather_value(df, "wind_speed_10m", 0) == 8.0

    def test_non_dataframe_input(self):
        """非 DataFrame 输入 (如 dict) → 返回默认值."""
        data = {"temperature_2m": -3.0}
        assert extract_weather_value(data, "temperature_2m", 999) == 999

    def test_default_inf(self):
        """默认值为 inf 时正常返回."""
        df = pd.DataFrame({"other_col": [1.0]})
        result = extract_weather_value(df, "cloud_base_altitude", float("inf"))
        assert math.isinf(result)

    def test_zero_value(self):
        """提取值为 0 时不应被误判为空."""
        df = pd.DataFrame({"snowfall": [0.0, 1.5]})
        assert extract_weather_value(df, "snowfall", -1) == 0.0
