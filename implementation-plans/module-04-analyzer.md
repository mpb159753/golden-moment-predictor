# Module 04: 分析层 — L1 本地滤网 + L2 远程滤网

## 模块背景

分析层是系统的"过滤器"。L1 本地滤网使用观景台本地的天气数据进行安全检查和基础条件判定；L2 远程滤网使用目标山峰和光路检查点的天气数据进行精细判定。"先过滤，后获取"原则的核心实现。

**在系统中的位置**: 分析层 (`gmp/analyzer/`) — 在 Scheduler 调度流程中位于数据获取层和评分层之间。

**前置依赖**: 
- Module 01（数据模型 `AnalysisResult`, `DataContext`）  
- Module 02（`GeoUtils.calculate_light_path_points`）  
- Module 03（`MeteoFetcher` 获取远程天气数据）

## 设计依据

- [01-architecture.md](../design/01-architecture.md): §1.5 数据流架构 — L1/L2 滤网
- [03-scoring-plugins.md](../design/03-scoring-plugins.md): §3.3 Plugin DataRequirement 总览, §3.7-3.10 触发条件
- [04-data-flow-example.md](../design/04-data-flow-example.md): §Stage 4 L1/L2 滤网结果
- [06-class-sequence.md](../design/06-class-sequence.md): §6.3 分析层类图, §6.7-6.9 评分流程
- [07-code-interface.md](../design/07-code-interface.md): §7.1 IAnalyzer Protocol

## 待创建文件列表

| 文件 | 说明 |
|------|------|
| `gmp/analyzer/__init__.py` | 包初始化 |
| `gmp/analyzer/base.py` | BaseAnalyzer 抽象基类 |
| `gmp/analyzer/local_analyzer.py` | L1 本地滤网 |
| `gmp/analyzer/remote_analyzer.py` | L2 远程滤网 |
| `tests/unit/test_local_analyzer.py` | 本地滤网测试 |
| `tests/unit/test_remote_analyzer.py` | 远程滤网测试 |

## 代码接口定义

### `gmp/analyzer/base.py`

```python
from abc import ABC, abstractmethod
import pandas as pd
from gmp.core.models import AnalysisResult

class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, data: pd.DataFrame, context: dict) -> AnalysisResult:
        ...
```

### `gmp/analyzer/local_analyzer.py`

```python
class LocalAnalyzer(BaseAnalyzer):
    """L1 本地滤网 — 安全检查 + 各 Plugin 触发条件预判"""
    
    def __init__(self, config: EngineConfig):
        self._config = config
    
    def analyze(self, data: pd.DataFrame, context: dict) -> AnalysisResult:
        """分析本地天气数据
        
        检查项 (按顺序):
        1. 安全检查 (一票否决)
        2. 云海判定 (云底高度 vs 站点海拔)
        3. 雾凇判定 (温度 < 2°C)
        4. 树挂积雪判定 (近期降雪 + 当前晴朗)
        5. 冰挂判定 (有效水源 + 冻结)
        6. 汇总本地天气概要
        
        返回:
            AnalysisResult.details 结构:
            {
                "safety": {"passed": bool, "precip_prob": float, "visibility": float},
                "cloud_cover_total": int,
                "cloud_base_altitude": float,
                "site_altitude": int,
                "temperature_2m": float,
                "night_cloud_cover": float,  # 夜间(20:00-05:00)平均云量
                "wind_speed_10m": float,
                "matched_targets": [...],     # 方位角匹配的目标列表
                "weather_code": int,
                "precip_prob": int,
                
                # 树挂积雪派生指标
                "recent_snowfall_12h_cm": float,
                "recent_snowfall_24h_cm": float,
                "hours_since_last_snow": float,
                "snowfall_duration_h_24h": int,
                "subzero_hours_since_last_snow": int,
                "max_temp_since_last_snow": float,
                "max_wind_since_last_snow": float,
                "sunshine_hours_since_snow": float,
                
                # 冰挂派生指标
                "effective_water_input_12h_mm": float,
                "effective_water_input_24h_mm": float,
                "hours_since_last_water_input": float,
                "subzero_hours_since_last_water": int,
                "max_temp_since_last_water": float,
            }
        """
    
    def _check_safety(self, row: dict) -> bool:
        """安全检查: 降水概率 < 50% 且 能见度 > 1km"""
    
    def _check_cloud_sea(self, cloud_base: float, site_altitude: int) -> dict:
        """云海判定: 云底高度 < 站点海拔"""
    
    def _check_frost(self, temperature: float) -> dict:
        """雾凇判定: 温度 < 2°C"""
    
    def _compute_snow_tree_indicators(self, weather_history: pd.DataFrame) -> dict:
        """计算树挂积雪相关的派生指标
        
        从 24 小时天气历史中计算:
        - recent_snowfall_12h_cm: 近12小时累计降雪
        - recent_snowfall_24h_cm: 近24小时累计降雪
        - hours_since_last_snow: 距最后一次降雪的小时数
        - snowfall_duration_h_24h: 24小时内降雪小时数
        - subzero_hours_since_last_snow: 降雪后零下持续小时数
        - max_temp_since_last_snow: 降雪后最高温度
        - max_wind_since_last_snow: 降雪后最大风速
        - sunshine_hours_since_snow: 降雪后日照时数 (按云量加权)
        """
    
    def _compute_ice_icicle_indicators(self, weather_history: pd.DataFrame) -> dict:
        """计算冰挂相关的派生指标
        
        从 24 小时天气历史中计算:
        - effective_water_input_12h_mm: rain + showers + snowfall * 水当量系数
        - effective_water_input_24h_mm: 同上 24 小时
        - hours_since_last_water_input: 距最后有效水源的小时数
        - subzero_hours_since_last_water: 水源后零下持续小时数
        - max_temp_since_last_water: 水源后最高温度
        """
```

### `gmp/analyzer/remote_analyzer.py`

```python
class RemoteAnalyzer(BaseAnalyzer):
    """L2 远程滤网 — 目标可见性 + 光路通畅度"""
    
    def analyze(self, data: pd.DataFrame, context: dict) -> AnalysisResult:
        """分析远程天气数据（目标山峰 + 光路检查点）
        
        context 包含:
        - target_weather: {target_name: DataFrame}
        - light_path_weather: [{point_name: str, low_cloud: int, mid_cloud: int, combined: int}]
        - viewpoint: Viewpoint (含 targets 列表)
        - sun_events: SunEvents (含日出/日落方位角)
        
        返回:
            AnalysisResult.details 结构:
            {
                "targets": [
                    {"name": str, "visible": bool, "combined_cloud": float, "status": str}
                ],
                "light_path": {
                    "clear": bool,
                    "avg_combined_cloud": float,
                    "max_combined_cloud": float,
                    "status": str,
                }
            }
        """
    
    def _check_target_visibility(self, target_data: pd.DataFrame, 
                                  hour: int) -> dict:
        """检查目标山峰可见性: 高云+中云 < 30%"""
    
    def _check_light_path(self, light_points_data: list[dict]) -> dict:
        """检查光路通畅度: 10点 (low+mid) 均值 < 50%"""
```

## 实现要点

### L1 安全检查（一票否决）

```python
def _check_safety(self, row: dict) -> bool:
    precip_ok = row.get("precipitation_probability", 100) < self._config.precip_threshold  # 50
    visibility_ok = row.get("visibility", 0) > self._config.visibility_threshold  # 1000m
    return precip_ok and visibility_ok
```

### 树挂积雪派生指标计算

```python
# 计算近 12/24 小时降雪量
recent_snowfall_12h_cm = weather_history.tail(12)["snowfall"].sum()

# 距离最后一次降雪的小时数
last_snow_idx = weather_history[weather_history["snowfall"] > 0].index
hours_since_last_snow = len(weather_history) - last_snow_idx[-1] - 1 if len(last_snow_idx) > 0 else 999

# 降雪后零下持续时间
since_last_snow = weather_history.iloc[last_snow_idx[-1]+1:]
subzero_hours = (since_last_snow["temperature_2m"] < 0).sum()

# 日照时数估算 (按云量加权)
# 云量 < 30% → 1小时日照; 云量 < 10% → 2分日照(强晒)
sunshine = 0
for _, row in since_last_snow.iterrows():
    if row["cloud_cover_total"] < 10:
        sunshine += 2
    elif row["cloud_cover_total"] < 30:
        sunshine += 1
```

### L2 目标可见性

高云+中云(cloud_cover_high + cloud_cover_medium) < 30% 视为可见。primary 目标不可见时影响日照金山评分，secondary 目标不可见仅作为忽略 warning。

### L2 光路通畅度

10个检查点的 (low_cloud + mid_cloud) 算术平均值 < 50% 视为光路通畅。

## 测试计划

### 测试操作步骤

```bash
source venv/bin/activate
python -m pytest tests/unit/test_local_analyzer.py tests/unit/test_remote_analyzer.py -v
```

### 具体测试用例

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `test_local_analyzer.py` | `test_safety_pass` | 降水0%, 能见度35km → passed=True |
| `test_local_analyzer.py` | `test_safety_precip_veto` | 降水70% → passed=False |
| `test_local_analyzer.py` | `test_safety_visibility_veto` | 能见度500m → passed=False |
| `test_local_analyzer.py` | `test_cloud_sea_detected` | 云底2600m, 站点3660m → cloud_sea=True, gap=1060 |
| `test_local_analyzer.py` | `test_cloud_sea_negative` | 云底5000m, 站点3660m → cloud_sea=False |
| `test_local_analyzer.py` | `test_frost_detected` | 温度-3.8°C → frost=True |
| `test_local_analyzer.py` | `test_frost_too_warm` | 温度5°C → frost=False |
| `test_local_analyzer.py` | `test_snow_tree_indicators` | 已知降雪历史 → 正确计算派生指标 |
| `test_local_analyzer.py` | `test_ice_icicle_indicators` | 已知降水+冻结 → 正确计算派生指标 |
| `test_local_analyzer.py` | `test_night_cloud_cover` | 夜间20-05点平均云量正确计算 |
| `test_remote_analyzer.py` | `test_target_visible` | 高+中云13% < 30% → visible=True |
| `test_remote_analyzer.py` | `test_target_obscured` | 高+中云85% → visible=False |
| `test_remote_analyzer.py` | `test_light_path_clear` | 10点均值8% → clear=True |
| `test_remote_analyzer.py` | `test_light_path_blocked` | 10点均值60% → clear=False |

## 验收标准

- [ ] L1 安全检查一票否决逻辑正确
- [ ] 云海/雾凇/树挂/冰挂触发条件预判正确
- [ ] 树挂积雪 8 个派生指标计算正确
- [ ] 冰挂 5 个派生指标计算正确
- [ ] L2 目标可见性判定正确
- [ ] L2 光路通畅度 10 点均值计算正确
- [ ] 所有测试通过
