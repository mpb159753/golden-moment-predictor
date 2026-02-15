"""gmp/core/config_loader.py — 统一配置管理

提供 ConfigManager (引擎配置)、ViewpointConfig (观景台配置)、
RouteConfig (线路配置) 的加载与访问。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ==================== EngineConfig 数据类 ====================


def _default_data_freshness() -> dict:
    return {"forecast_valid_hours": 24, "archive_never_stale": True}


def _default_safety() -> dict:
    return {"precip_threshold": 50, "visibility_threshold": 1000}


def _default_scoring() -> dict:
    return {}


def _default_confidence() -> dict:
    return {"high": [1, 2], "medium": [3, 4], "low": [5, 16]}


@dataclass
class EngineConfig:
    """全局引擎配置 — 字段定义见设计文档 §7.3"""

    db_path: str = "data/gmp.db"
    output_dir: str = "public/data"
    archive_dir: str = "archive"
    log_level: str = "INFO"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    archive_api_base_url: str = (
        "https://archive-api.open-meteo.com/v1/archive"
    )
    forecast_days: int = 7
    light_path_count: int = 10
    light_path_interval_km: float = 10.0
    data_freshness: dict = field(default_factory=_default_data_freshness)
    safety: dict = field(default_factory=_default_safety)
    scoring: dict = field(default_factory=_default_scoring)
    confidence: dict = field(default_factory=_default_confidence)
    summary_mode: str = "rule"
    backtest_max_history_days: int = 365


# ==================== ConfigManager ====================


class ConfigManager:
    """引擎配置管理器 — 加载 engine_config.yaml 并提供便捷访问。"""

    def __init__(self, config_path: str = "config/engine_config.yaml") -> None:
        self.config: EngineConfig = self._load(config_path)

    def _load(self, path: str) -> EngineConfig:
        """加载 YAML → EngineConfig。"""
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        raw = filepath.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 解析错误: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"YAML 配置格式错误: 期望字典，收到 {type(data)}")

        return self._parse(data)

    def _parse(self, data: dict) -> EngineConfig:
        """将原始 dict 解析为 EngineConfig。"""
        cache = data.get("cache", {})
        light_path = data.get("light_path", {})
        summary = data.get("summary", {})
        backtest = data.get("backtest", {})

        return EngineConfig(
            db_path=cache.get("db_path", EngineConfig.db_path),
            output_dir=data.get("output_dir", EngineConfig.output_dir),
            archive_dir=data.get("archive_dir", EngineConfig.archive_dir),
            log_level=data.get("log_level", EngineConfig.log_level),
            open_meteo_base_url=data.get(
                "open_meteo_base_url", EngineConfig.open_meteo_base_url
            ),
            archive_api_base_url=backtest.get(
                "archive_api_base", EngineConfig.archive_api_base_url
            ),
            forecast_days=data.get(
                "forecast_days", EngineConfig.forecast_days
            ),
            light_path_count=light_path.get(
                "count", EngineConfig.light_path_count
            ),
            light_path_interval_km=light_path.get(
                "interval_km", EngineConfig.light_path_interval_km
            ),
            data_freshness=cache.get(
                "freshness", _default_data_freshness()
            ),
            safety=data.get("safety", _default_safety()),
            scoring=data.get("scoring", _default_scoring()),
            confidence=data.get("confidence", _default_confidence()),
            summary_mode=summary.get("mode", EngineConfig.summary_mode),
            backtest_max_history_days=backtest.get(
                "max_history_days", EngineConfig.backtest_max_history_days
            ),
        )

    # ---- 便捷访问方法 ----

    def get_plugin_config(self, event_type: str) -> dict:
        """获取指定 Plugin 的评分配置 (权重 + 阈值 + 触发条件)。

        Args:
            event_type: 如 "golden_mountain", "cloud_sea" 等。

        Returns:
            Plugin 配置字典，不存在则返回空 dict。
        """
        return self.config.scoring.get(event_type, {})

    def get_safety_config(self) -> dict:
        """返回安全阈值配置。"""
        return self.config.safety

    def get_light_path_config(self) -> dict:
        """返回光路计算配置。"""
        return {
            "count": self.config.light_path_count,
            "interval_km": self.config.light_path_interval_km,
        }

    def get_confidence_config(self) -> dict:
        """返回置信度映射配置。"""
        return self.config.confidence

    def get_output_config(self) -> dict:
        """返回输出路径配置。"""
        return {
            "output_dir": self.config.output_dir,
            "archive_dir": self.config.archive_dir,
        }


# ==================== ViewpointConfig ====================


class ViewpointConfig:
    """观景台配置管理器 — 加载目录下所有 viewpoint YAML 文件。"""

    def __init__(self) -> None:
        self._viewpoints: dict[str, "Viewpoint"] = {}

    def load(self, path: str) -> None:
        """加载目录下所有 *.yaml 文件为 Viewpoint 对象。"""
        from gmp.core.models import Location, Target, Viewpoint

        dir_path = Path(path)
        if not dir_path.is_dir():
            raise FileNotFoundError(f"观景台配置目录不存在: {path}")

        for yaml_file in sorted(dir_path.glob("*.yaml")):
            raw = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            if not isinstance(data, dict):
                continue

            # 解析 Location
            loc_data = data.get("location", {})
            location = Location(
                lat=loc_data["lat"],
                lon=loc_data["lon"],
                altitude=loc_data["altitude"],
            )

            # 解析 Targets
            targets = []
            for t in data.get("targets", []):
                targets.append(
                    Target(
                        name=t["name"],
                        lat=t["lat"],
                        lon=t["lon"],
                        altitude=t["altitude"],
                        weight=t["weight"],
                        applicable_events=t.get("applicable_events"),
                    )
                )

            vp = Viewpoint(
                id=data["id"],
                name=data["name"],
                location=location,
                capabilities=data.get("capabilities", []),
                targets=targets,
            )
            self._viewpoints[vp.id] = vp

    def get(self, viewpoint_id: str) -> "Viewpoint":
        """按 ID 获取，不存在抛 ViewpointNotFoundError。"""
        from gmp.core.exceptions import ViewpointNotFoundError

        if viewpoint_id not in self._viewpoints:
            raise ViewpointNotFoundError(viewpoint_id)
        return self._viewpoints[viewpoint_id]

    def list_all(self) -> list["Viewpoint"]:
        """返回所有已加载的观景台。"""
        return list(self._viewpoints.values())


# ==================== RouteConfig ====================


class RouteConfig:
    """线路配置管理器 — 加载目录下所有 route YAML 文件。"""

    def __init__(self) -> None:
        self._routes: dict[str, "Route"] = {}

    def load(self, path: str) -> None:
        """加载目录下所有 *.yaml 文件为 Route 对象。"""
        from gmp.core.models import Route, RouteStop

        dir_path = Path(path)
        if not dir_path.is_dir():
            raise FileNotFoundError(f"线路配置目录不存在: {path}")

        for yaml_file in sorted(dir_path.glob("*.yaml")):
            raw = yaml_file.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
            if not isinstance(data, dict):
                continue

            # 解析 Stops 并按 order 排序
            stops = []
            for s in data.get("stops", []):
                stops.append(
                    RouteStop(
                        viewpoint_id=s["viewpoint_id"],
                        order=s["order"],
                        stay_note=s.get("stay_note", ""),
                    )
                )
            stops.sort(key=lambda s: s.order)

            route = Route(
                id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                stops=stops,
            )
            self._routes[route.id] = route

    def get(self, route_id: str) -> "Route":
        """按 ID 获取，不存在抛 RouteNotFoundError。"""
        from gmp.core.exceptions import RouteNotFoundError

        if route_id not in self._routes:
            raise RouteNotFoundError(route_id)
        return self._routes[route_id]

    def list_all(self) -> list["Route"]:
        """返回所有已加载的线路。"""
        return list(self._routes.values())

