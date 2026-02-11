"""GoldenMountainPlugin — 日照金山评分插件

设计依据:
  - design/03-scoring-plugins.md §3.5 GoldenMountainPlugin
  - design/04-data-flow-example.md §Stage 5
  - implementation-plans/module-06-scorer-complex.md

评分公式:
  Score = S_light + S_target + S_local

维度一票否决:
  任一维度得 0 → 总分置 0
"""

from __future__ import annotations

from gmp.core.models import DataContext, DataRequirement, ScoreResult
from gmp.scorer.plugin import score_to_status, step_score


class GoldenMountainPlugin:
    """日照金山评分插件

    支持 sunrise / sunset 双模式，通过构造函数指定 event_type。
    注册时分别注册两个实例:
        engine.register(GoldenMountainPlugin("sunrise_golden_mountain"))
        engine.register(GoldenMountainPlugin("sunset_golden_mountain"))
    """

    display_name = "日照金山"
    data_requirement = DataRequirement(
        needs_l2_target=True,
        needs_l2_light_path=True,
        needs_astro=True,
    )

    def __init__(self, event_type: str = "sunrise_golden_mountain") -> None:
        self._event_type = event_type

    @property
    def event_type(self) -> str:
        return self._event_type

    # ------------------------------------------------------------------
    # 触发条件
    # ------------------------------------------------------------------

    def check_trigger(self, l1_data: dict) -> bool:
        """触发条件: 总云量 < 80% 且有匹配 Target"""
        # 使用 .get() 提供安全默认值，避免 KeyError（正向偏差于设计文档）
        return (
            l1_data.get("cloud_cover_total", 100) < 80
            and len(l1_data.get("matched_targets", [])) > 0
        )

    # ------------------------------------------------------------------
    # 评分
    # ------------------------------------------------------------------

    def score(self, context: DataContext) -> ScoreResult:
        """计算日照金山综合评分 (0-100).

        Score = S_light + S_target + S_local
        任一维度为 0 → 总分直接置 0。
        """
        s_light, detail_light = self._score_light_path(
            context.light_path_weather or []
        )
        s_target, detail_target = self._score_target_visible(context)
        s_local, detail_local = self._score_local_clear(context)

        # 一票否决
        if s_light == 0 or s_target == 0 or s_local == 0:
            total = 0
        else:
            total = s_light + s_target + s_local

        # 限制 0-100
        total = max(0, min(100, total))

        return ScoreResult(
            total_score=total,
            status=score_to_status(total),
            breakdown={
                "light_path": {
                    "score": s_light,
                    "max": 35,
                    "detail": detail_light,
                },
                "target_visible": {
                    "score": s_target,
                    "max": 40,
                    "detail": detail_target,
                },
                "local_clear": {
                    "score": s_local,
                    "max": 25,
                    "detail": detail_local,
                },
            },
        )

    # ------------------------------------------------------------------
    # 私有评分维度
    # ------------------------------------------------------------------

    def _score_light_path(self, light_path_data: list[dict]) -> tuple[int, str]:
        """光路通畅分数 (满分 35).

        计算 10 个检查点 combined (low_cloud + mid_cloud) 的算术均值，
        按阶梯映射:
          ≤10%: 35 | 10-20%: 30 | 20-30%: 20 | 30-50%: 10 | >50%: 0
        """
        if not light_path_data:
            return 0, "无光路数据"

        avg = sum(
            p.get("combined", p.get("low_cloud", 0) + p.get("mid_cloud", 0))
            for p in light_path_data
        ) / len(light_path_data)

        # 阶梯映射 — 值越小分越高 (ascending=False 即 ≤ 阈值即命中)
        thresholds: list[tuple[float, int]] = [
            (10, 35),
            (20, 30),
            (30, 20),
            (50, 10),
        ]
        s = step_score(avg, thresholds, ascending=False)
        if avg > 50:
            s = 0

        detail = f"10点均值云量{avg:.0f}%"
        if s == 35:
            detail += ", ≤10%满分"
        elif s == 0:
            detail += ", >50%否决"
        else:
            detail += f", {self._range_label(avg, thresholds)}区间"

        return s, detail

    def _score_target_visible(self, context: DataContext) -> tuple[int, str]:
        """目标可见分数 (满分 40).

        从 primary 权重的 target 获取高+中云量，按阶梯映射:
          ≤10%: 40 | 10-20%: 32 | 20-30%: 22 | >30%: 0
        """
        targets = context.viewpoint.targets if context.viewpoint else []
        target_weather = context.target_weather or {}

        primary_target = None
        for t in targets:
            if t.weight == "primary":
                primary_target = t
                break

        if primary_target is None:
            return 0, "无 primary 目标"

        tw = target_weather.get(primary_target.name)
        if tw is None or (hasattr(tw, "empty") and tw.empty):
            return 0, f"{primary_target.name}无天气数据"

        # 从 target weather 提取 high_cloud + mid_cloud
        if hasattr(tw, "iloc"):
            # DataFrame — 取第一行 (日出/日落时刻)
            row = tw.iloc[0] if len(tw) > 0 else {}
            high = float(row.get("high_cloud", row.get("cloud_cover_high", 0)))
            mid = float(row.get("mid_cloud", row.get("cloud_cover_mid", 0)))
        elif isinstance(tw, dict):
            high = float(tw.get("high_cloud", tw.get("cloud_cover_high", 0)))
            mid = float(tw.get("mid_cloud", tw.get("cloud_cover_mid", 0)))
        else:
            return 0, "目标天气数据格式异常"

        combined = high + mid

        thresholds: list[tuple[float, int]] = [
            (10, 40),
            (20, 32),
            (30, 22),
        ]
        s = step_score(combined, thresholds, ascending=False)
        if combined > 30:
            s = 0

        detail = f"{primary_target.name}高+中云{combined:.0f}%"
        if s == 40:
            detail += ", ≤10%满分"
        elif s == 0:
            detail += ", >30%否决"
        else:
            detail += f", {self._range_label(combined, thresholds)}区间"

        return s, detail

    def _score_local_clear(self, context: DataContext) -> tuple[int, str]:
        """本地通透分数 (满分 25).

        从本地天气获取总云量，按阶梯映射:
          ≤15%: 25 | 15-30%: 20 | 30-50%: 12 | 50-80%: 5 | >80%: 0
        """
        lw = context.local_weather
        if lw is None or (hasattr(lw, "empty") and lw.empty):
            return 0, "无本地天气数据"

        # 取总云量 — 尝试从 DataFrame 或 dict 中提取
        if hasattr(lw, "iloc"):
            row = lw.iloc[0] if len(lw) > 0 else {}
            total_cloud = float(row.get("cloud_cover_total", row.get("cloud_cover", 0)))
        elif isinstance(lw, dict):
            total_cloud = float(lw.get("cloud_cover_total", lw.get("cloud_cover", 0)))
        else:
            return 0, "本地天气数据格式异常"

        # 阶梯映射 — 与 _score_light_path / _score_target_visible 保持一致
        thresholds: list[tuple[float, int]] = [
            (15, 25),
            (30, 20),
            (50, 12),
            (80, 5),
        ]
        s = step_score(total_cloud, thresholds, ascending=False)
        if total_cloud > 80:
            s = 0

        detail = f"本地总云{total_cloud:.0f}%"
        if s == 25:
            detail += ", ≤15%满分"
        elif s == 0:
            detail += ", >80%否决"
        else:
            detail += f", {self._range_label(total_cloud, thresholds)}区间"

        return s, detail

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _range_label(value: float, thresholds: list[tuple[float, int]]) -> str:
        """根据阶梯表生成区间标签, 例如 '10-20%'."""
        prev = 0
        for t, _ in thresholds:
            if value <= t:
                return f"{prev}-{t}%"
            prev = t
        return f">{thresholds[-1][0]}%"

    def dimensions(self) -> list[str]:
        return ["light_path", "target_visible", "local_clear"]
