"""BaseReporter — 输出层抽象基类

设计依据: design/06-class-sequence.md §6.4
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseReporter(ABC):
    """输出层基类

    所有 Reporter 都必须实现 generate 方法，
    接收 Scheduler 产出的结果 dict，输出格式化后的数据。
    """

    @abstractmethod
    def generate(self, scheduler_result: dict) -> Any:
        """将 Scheduler 结果转换为特定格式的输出

        Args:
            scheduler_result: GMPScheduler.run() 的返回值，结构:
                {
                    "viewpoint": str,
                    "forecast_days": [
                        {
                            "date": str,
                            "confidence": str,
                            "events": [
                                {
                                    "event_type": str,
                                    "display_name": str,
                                    "total_score": int,
                                    "status": str,
                                    "breakdown": dict,
                                }, ...
                            ],
                        }, ...
                    ],
                    "meta": {"api_calls": int, "cache_hits": int}
                }

        Returns:
            格式化后的输出 (dict / str)
        """
        ...
