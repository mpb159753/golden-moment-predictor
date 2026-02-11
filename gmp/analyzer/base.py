"""BaseAnalyzer 抽象基类

定义分析器的统一接口。
接口定义遵循 design/07-code-interface.md §7.1 IAnalyzer Protocol。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from gmp.core.models import AnalysisResult


class BaseAnalyzer(ABC):
    """分析器抽象基类

    所有分析器（L1 本地滤网、L2 远程滤网）都必须实现此接口。
    """

    @abstractmethod
    def analyze(self, data: pd.DataFrame, context: dict) -> AnalysisResult:
        """分析天气数据并返回滤网结果

        Args:
            data: 天气数据 DataFrame
            context: 上下文信息字典

        Returns:
            AnalysisResult 包含 passed/score/reason/details
        """
        ...
