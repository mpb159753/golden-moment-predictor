"""评分插件公共工具

提供评分等级映射、DataFrame 数据提取、阶梯查表等辅助函数，供所有 Plugin 复用。
重导出 DataRequirement / DataContext / ScoreResult 方便引用。
"""

from gmp.core.models import DataContext, DataRequirement, ScoreResult


def score_to_status(score: int) -> str:
    """将 0-100 分映射为建议等级。

    分段规则（design/03-scoring-plugins.md §3.4）:
      95-100  → Perfect
      80-94   → Recommended
      50-79   → Possible
       0-49   → Not Recommended
    """
    if score >= 95:
        return "Perfect"
    if score >= 80:
        return "Recommended"
    if score >= 50:
        return "Possible"
    return "Not Recommended"


def extract_weather_value(weather, column: str, default: float) -> float:
    """从 DataFrame 中提取单一代表值 (首个非空值)。

    Args:
        weather: pandas DataFrame, 逐时天气数据
        column: 要提取的列名
        default: 列不存在或全为空时的默认值

    Returns:
        首行非空值, 或 default
    """
    if hasattr(weather, "columns") and column in weather.columns:
        vals = weather[column].dropna()
        if len(vals) > 0:
            return float(vals.iloc[0])
    return default


def step_score(value: float, thresholds: list[tuple[float, int]], *, ascending: bool = True) -> int:
    """通用阶梯查表函数。

    Args:
        value: 待评价的数值
        thresholds: [(阈值, 得分), ...] 按阈值从严到松排列
        ascending: True = 值越大得分越高 (>=阈值即命中)
                   False = 值越小得分越高 (<=阈值即命中)
    Returns:
        命中的得分，若不命中任何阶梯则返回最后一项得分
    """
    for threshold, points in thresholds:
        if ascending and value >= threshold:
            return points
        if not ascending and value <= threshold:
            return points
    return thresholds[-1][1] if thresholds else 0


__all__ = [
    "DataContext",
    "DataRequirement",
    "ScoreResult",
    "score_to_status",
    "extract_weather_value",
    "step_score",
]
