"""GMP 配置加载器

- EngineConfig: 引擎全局配置 (从 engine_config.yaml 加载)
- ViewpointConfig: 观景台配置管理器 (从 viewpoints/*.yaml 加载)

字段定义遵循 design/07-code-interface.md §7.3。
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from gmp.core.exceptions import ViewpointNotFoundError
from gmp.core.models import Location, Target, Viewpoint


@dataclass
class EngineConfig:
    """引擎配置 — 对应 engine_config.yaml"""

    # 数据库
    db_path: str = "gmp_cache.db"

    # 缓存 TTL
    memory_cache_ttl_seconds: int = 300
    db_cache_ttl_seconds: int = 3600

    # 坐标精度
    coord_precision: int = 2

    # 安全阈值
    precip_threshold: float = 50.0
    visibility_threshold: float = 1000
    local_cloud_threshold: float = 30
    target_cloud_threshold: float = 30
    light_path_threshold: float = 50
    wind_threshold: float = 20
    frost_temp_threshold: float = 2.0

    # 树挂/冰挂 (SnowTree/IceIcicle)
    retention_max_temp: float = 2.5
    retention_max_sun_hours: int = 5
    retention_max_wind: float = 30.0

    # 光路计算
    light_path_count: int = 10
    light_path_interval_km: float = 10

    # 评分权重 (日照金山)
    golden_score_weights: dict = field(default_factory=lambda: {
        "light_path": 35,
        "target_visible": 40,
        "local_clear": 25,
    })

    # 观星评分配置 (来源: engine_config.yaml scoring.stargazing)
    stargazing_config: dict = field(default_factory=lambda: {
        "base_optimal": 100,
        "base_good": 90,
        "base_partial": 70,
        "cloud_penalty_factor": 0.8,
    })

    # L1 Analyzer 评分配置
    l1_base_score: int = 50
    l1_cloud_sea_bonus: int = 15
    l1_frost_bonus: int = 10
    l1_low_cloud_bonus: int = 15
    l1_low_cloud_mid_bonus: int = 8
    l1_low_cloud_threshold: int = 30
    l1_mid_cloud_threshold: int = 60
    l1_low_wind_bonus: int = 10
    l1_low_wind_mid_bonus: int = 5
    l1_low_wind_threshold: float = 20.0
    l1_mid_wind_threshold: float = 30.0

    # L2 Analyzer 评分配置
    l2_base_score: int = 20
    l2_light_path_max: int = 40
    l2_light_path_good_threshold: float = 25.0
    l2_target_primary_bonus: int = 25
    l2_target_primary_blocked_bonus: int = 5
    l2_target_secondary_max: int = 15

    # 调度器
    default_target_hour: int = 7

    # 置信度映射 (days_ahead 范围)
    confidence_high_days: list[int] = field(default_factory=lambda: [1, 2])
    confidence_medium_days: list[int] = field(default_factory=lambda: [3, 4])

    # Reporter 输出层阈值
    reporter_l1_precip_threshold: int = 30
    reporter_overcast_threshold: int = 60
    reporter_rain_threshold: int = 50

    # 摘要生成
    summary_mode: str = "rule"

    # 分页
    default_page_size: int = 20
    max_page_size: int = 100

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "console"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "EngineConfig":
        """从 YAML 文件加载引擎配置

        YAML 中的嵌套结构会被扁平化映射到 dataclass 字段。
        未指定的字段使用 dataclass 默认值。
        """
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            raw: dict[str, Any] = yaml.safe_load(f) or {}

        kwargs: dict[str, Any] = {}

        # cache 节
        cache = raw.get("cache", {})
        if "memory_ttl_seconds" in cache:
            kwargs["memory_cache_ttl_seconds"] = cache["memory_ttl_seconds"]
        if "db_ttl_seconds" in cache:
            kwargs["db_cache_ttl_seconds"] = cache["db_ttl_seconds"]
        if "db_path" in cache:
            kwargs["db_path"] = cache["db_path"]

        # coord_precision
        if "coord_precision" in raw:
            kwargs["coord_precision"] = raw["coord_precision"]

        # thresholds 节
        thresholds = raw.get("thresholds", {})
        threshold_mapping = {
            "precip_probability": "precip_threshold",
            "visibility_min": "visibility_threshold",
            "local_cloud_max": "local_cloud_threshold",
            "target_cloud_max": "target_cloud_threshold",
            "light_path_cloud_max": "light_path_threshold",
            "wind_speed_max": "wind_threshold",
            "frost_temperature": "frost_temp_threshold",
        }
        for yaml_key, attr_name in threshold_mapping.items():
            if yaml_key in thresholds:
                kwargs[attr_name] = float(thresholds[yaml_key])

        # light_path 节
        lp = raw.get("light_path", {})
        if "count" in lp:
            kwargs["light_path_count"] = lp["count"]
        if "interval_km" in lp:
            kwargs["light_path_interval_km"] = lp["interval_km"]

        # retention 节 (树挂/冰挂留存阈值)
        retention = raw.get("retention", {})
        retention_mapping = {
            "max_temp": "retention_max_temp",
            "max_sun_hours": "retention_max_sun_hours",
            "max_wind": "retention_max_wind",
        }
        for yaml_key, attr_name in retention_mapping.items():
            if yaml_key in retention:
                kwargs[attr_name] = retention[yaml_key]

        # scoring 节 — golden_mountain
        scoring = raw.get("scoring", {})
        gm = scoring.get("golden_mountain", {})
        if gm:
            kwargs["golden_score_weights"] = {
                k: v for k, v in gm.items() if k != "veto_threshold"
            }

        # scoring 节 — stargazing
        sg = scoring.get("stargazing", {})
        if sg:
            kwargs["stargazing_config"] = sg

        # analyzer_scoring 节 — L1/L2 评分配置
        analyzer_scoring = raw.get("analyzer_scoring", {})
        l1_scoring = analyzer_scoring.get("l1", {})
        l1_mapping = {
            "base_score": "l1_base_score",
            "cloud_sea_bonus": "l1_cloud_sea_bonus",
            "frost_bonus": "l1_frost_bonus",
            "low_cloud_bonus": "l1_low_cloud_bonus",
            "low_cloud_mid_bonus": "l1_low_cloud_mid_bonus",
            "low_cloud_threshold": "l1_low_cloud_threshold",
            "mid_cloud_threshold": "l1_mid_cloud_threshold",
            "low_wind_bonus": "l1_low_wind_bonus",
            "low_wind_mid_bonus": "l1_low_wind_mid_bonus",
            "low_wind_threshold": "l1_low_wind_threshold",
            "mid_wind_threshold": "l1_mid_wind_threshold",
        }
        for yaml_key, attr_name in l1_mapping.items():
            if yaml_key in l1_scoring:
                kwargs[attr_name] = l1_scoring[yaml_key]

        l2_scoring = analyzer_scoring.get("l2", {})
        l2_mapping = {
            "base_score": "l2_base_score",
            "light_path_max": "l2_light_path_max",
            "light_path_good_threshold": "l2_light_path_good_threshold",
            "target_primary_bonus": "l2_target_primary_bonus",
            "target_primary_blocked_bonus": "l2_target_primary_blocked_bonus",
            "target_secondary_max": "l2_target_secondary_max",
        }
        for yaml_key, attr_name in l2_mapping.items():
            if yaml_key in l2_scoring:
                kwargs[attr_name] = l2_scoring[yaml_key]

        # scheduler 节
        scheduler = raw.get("scheduler", {})
        if "default_target_hour" in scheduler:
            kwargs["default_target_hour"] = int(scheduler["default_target_hour"])

        # confidence 节
        confidence = raw.get("confidence", {})
        if "high" in confidence:
            kwargs["confidence_high_days"] = confidence["high"]
        if "medium" in confidence:
            kwargs["confidence_medium_days"] = confidence["medium"]

        # reporter 节
        reporter = raw.get("reporter", {})
        reporter_mapping = {
            "l1_precip_threshold": "reporter_l1_precip_threshold",
            "overcast_threshold": "reporter_overcast_threshold",
            "rain_threshold": "reporter_rain_threshold",
        }
        for yaml_key, attr_name in reporter_mapping.items():
            if yaml_key in reporter:
                kwargs[attr_name] = int(reporter[yaml_key])

        # summary 节
        summary = raw.get("summary", {})
        if "mode" in summary:
            kwargs["summary_mode"] = summary["mode"]

        # pagination 节
        pagination = raw.get("pagination", {})
        if "default_page_size" in pagination:
            kwargs["default_page_size"] = pagination["default_page_size"]
        if "max_page_size" in pagination:
            kwargs["max_page_size"] = pagination["max_page_size"]

        # logging 节
        logging_cfg = raw.get("logging", {})
        if "level" in logging_cfg:
            kwargs["log_level"] = logging_cfg["level"]
        if "format" in logging_cfg:
            kwargs["log_format"] = logging_cfg["format"]

        return cls(**kwargs)


class ViewpointConfig:
    """观景台配置管理器

    从 config/viewpoints/*.yaml 目录加载所有观景台配置，
    提供按 ID 查询和分页列表功能。
    """

    def __init__(self) -> None:
        self._viewpoints: dict[str, Viewpoint] = {}

    def load(self, config_dir: str | Path) -> None:
        """加载 config_dir/*.yaml 目录下所有观景台配置"""
        config_path = Path(config_dir)
        if not config_path.is_dir():
            return

        for yaml_file in sorted(config_path.glob("*.yaml")):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and "id" in data:
                vp = self._parse_viewpoint(data)
                self._viewpoints[vp.id] = vp

    def get(self, viewpoint_id: str) -> Viewpoint:
        """按 ID 获取观景台，不存在则抛出 ViewpointNotFoundError"""
        if viewpoint_id not in self._viewpoints:
            raise ViewpointNotFoundError(viewpoint_id)
        return self._viewpoints[viewpoint_id]

    def list_all(self, page: int = 1, page_size: int = 20) -> dict:
        """分页返回观景台列表

        Returns:
            {
                "viewpoints": [Viewpoint, ...],
                "pagination": {
                    "page": int,
                    "page_size": int,
                    "total": int,
                    "total_pages": int,
                }
            }
        """
        all_viewpoints = list(self._viewpoints.values())
        total = len(all_viewpoints)
        total_pages = max(1, math.ceil(total / page_size))

        start = (page - 1) * page_size
        end = start + page_size
        page_items = all_viewpoints[start:end]

        return {
            "viewpoints": page_items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        }

    @staticmethod
    def _parse_viewpoint(data: dict) -> Viewpoint:
        """将 YAML dict 解析为 Viewpoint 对象"""
        loc_data = data.get("location", {})
        location = Location(
            lat=loc_data["lat"],
            lon=loc_data["lon"],
            altitude=loc_data["altitude"],
        )

        targets = []
        for t in data.get("targets", []):
            targets.append(Target(
                name=t["name"],
                lat=t["lat"],
                lon=t["lon"],
                altitude=t["altitude"],
                weight=t.get("weight", "secondary"),
                applicable_events=t.get("applicable_events"),
            ))

        return Viewpoint(
            id=data["id"],
            name=data["name"],
            location=location,
            capabilities=data.get("capabilities", []),
            targets=targets,
        )
