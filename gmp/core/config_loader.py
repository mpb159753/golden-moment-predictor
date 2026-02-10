import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

@dataclass
class EngineConfig:
    """引擎配置"""
    # 数据库
    db_path: str = "gmp_cache.db"
    
    # 缓存 TTL
    memory_cache_ttl_seconds: int = 300
    db_cache_ttl_seconds: int = 3600
    
    # 坐标精度
    coord_precision: int = 2
    
    # ==========================
    # 基础安全阈值
    # ==========================
    precip_threshold: float = 50.0
    visibility_threshold: float = 1000
    local_cloud_threshold: float = 30
    target_cloud_threshold: float = 30
    light_path_threshold: float = 50
    wind_threshold: float = 20
    frost_temp_threshold: float = 2.0
    
    # ==========================
    # 1. 日照金山 (Golden Mountain)
    # ==========================
    golden_trigger_cloud: float = 80.0
    golden_score_weights: dict = field(default_factory=lambda: {
        "light_path": 35,
        "target_visible": 40,
        "local_clear": 25
    })
    # [10%, 20%, 30%, 50%] 对应分数在代码逻辑中映射
    golden_light_path_tiers: list[int] = field(default_factory=lambda: [10, 20, 30, 50])
    golden_target_tiers: list[int] = field(default_factory=lambda: [10, 20, 30])
    
    # ==========================
    # 2. 观星 (Stargazing)
    # ==========================
    stargazing_trigger_cloud: float = 70.0
    stargazing_cloud_penalty_ratio: float = 0.8
    stargazing_wind_thresholds: list[float] = field(default_factory=lambda: [20.0, 40.0])
    stargazing_wind_penalties: list[int] = field(default_factory=lambda: [10, 30])

    # ==========================
    # 3. 云海 (Cloud Sea)
    # ==========================
    cloud_sea_gap_tiers: list[int] = field(default_factory=lambda: [200, 500, 800])
    cloud_sea_density_tiers: list[int] = field(default_factory=lambda: [30, 50, 80])
    cloud_sea_mid_cloud_thresholds: list[int] = field(default_factory=lambda: [30, 60])
    cloud_sea_mid_cloud_factors: list[float] = field(default_factory=lambda: [1.0, 0.7, 0.3])
    
    # ==========================
    # 4. 雾凇 (Frost)
    # ==========================
    frost_optimal_temp_range: list[float] = field(default_factory=lambda: [-5.0, -1.0])
    frost_visibility_tiers: list[int] = field(default_factory=lambda: [5, 10, 20])
    frost_wind_thresholds: list[float] = field(default_factory=lambda: [3.0, 5.0, 10.0])

    # ==========================
    # 5. 树挂/冰挂 (SnowTree/IceIcicle)
    # ==========================
    # 触发阈值
    snow_trigger_fresh_depth: float = 0.2     # cm/12h
    snow_trigger_retention_depth: float = 1.5 # cm/24h
    ice_trigger_fresh_water: float = 0.4      # mm/12h
    ice_trigger_retention_water: float = 2.0  # mm/24h
    
    # 留存限制
    retention_max_temp: float = 2.5     # 留存期最高允许气温
    retention_max_sun_hours: int = 5    # 留存期最大允许日照时数
    retention_sun_deduction_hours: list[int] = field(default_factory=lambda: [2, 5, 8])
    retention_max_wind: float = 30.0    # 留存期最大允许风速
    
    # ==========================
    # 光路计算
    # ==========================
    light_path_count: int = 10
    light_path_interval_km: float = 10
    
    # ==========================
    # 其他
    # ==========================
    summary_mode: str = "rule"
    default_page_size: int = 20
    max_page_size: int = 100

def load_engine_config(config_path: str | Path) -> EngineConfig:
    """
    加载引擎配置，如果文件不存在或解析失败，抛出异常或返回默认值。
    这里设计为：如果文件存在则覆盖默认值；如果不存在则使用默认值并打印警告（或可视情况抛出）。
    由于 Plan 中提到 'normal loading, default fallback', 我们实现合并逻辑。
    """
    path = Path(config_path)
    if not path.exists():
        # 如果没有配置文件，直接返回默认配置
        return EngineConfig()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # 使用 dataclass 的字段来过滤和转换类型 (简单实现)
    # 对于嵌套字典 (golden_score_weights) 需要特别处理，这里直接覆盖
    
    config = EngineConfig()
    
    for key, value in data.items():
        if hasattr(config, key):
            # 做简单的类型转换检查可以增强健壮性，这里暂时直接赋值
            setattr(config, key, value)
            
    return config
