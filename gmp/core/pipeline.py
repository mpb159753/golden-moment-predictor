"""AnalyzerPipeline — L1 → L2 分析管线

将 LocalAnalyzer 和 RemoteAnalyzer 串联为统一管线。
L1 不通过时直接短路，不触发任何 L2 远程调用。

设计依据:
- implementation-plans/module-07-scheduler.md
- design/01-architecture.md §1.5 数据流架构
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from gmp.core.models import AnalysisResult

if TYPE_CHECKING:
    from gmp.analyzer.local_analyzer import LocalAnalyzer
    from gmp.analyzer.remote_analyzer import RemoteAnalyzer


class AnalyzerPipeline:
    """L1 → L2 分析管线

    职责:
      - 串联 LocalAnalyzer + RemoteAnalyzer
      - L1 不通过时短路返回，确保不发起不必要的远程请求
    """

    def __init__(
        self,
        local_analyzer: "LocalAnalyzer",
        remote_analyzer: "RemoteAnalyzer",
    ) -> None:
        self._local = local_analyzer
        self._remote = remote_analyzer

    def run(
        self,
        local_weather: pd.DataFrame,
        context: dict,
        need_l2: bool = False,
    ) -> dict:
        """运行分析管线

        Args:
            local_weather: 本地天气 DataFrame
            context: 上下文信息 dict，需包含:
                - site_altitude: int — 观景台海拔
                - target_hour: int — 目标分析小时
                以及 (当 need_l2=True 时):
                - target_weather: {name: DataFrame}
                - light_path_weather: [dict]
                - target_weights: {name: weight}
            need_l2: 是否需要运行 L2 远程滤网

        Returns:
            {
                "l1": AnalysisResult,
                "l2": AnalysisResult | None,  # 仅当 need_l2=True 且 L1 通过时
            }
        """
        # ---- L1 本地滤网 ----
        l1_result = self._local.analyze(local_weather, context)

        if not l1_result.passed or not need_l2:
            return {"l1": l1_result, "l2": None}

        # ---- L2 远程滤网 ----
        l2_result = self._remote.analyze(pd.DataFrame(), context)

        return {"l1": l1_result, "l2": l2_result}
