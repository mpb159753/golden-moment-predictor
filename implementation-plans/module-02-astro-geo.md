# Module 02: 天文计算与地理工具

## 模块背景

本模块实现系统的天文计算和地理工具功能。天文计算用于获取日出日落时间、方位角、月相等数据；地理工具用于计算方位角、光路检查点坐标、距离等。这些是日照金山评分和观星评分的核心依赖。

**在系统中的位置**: 数据获取层 (`gmp/astro/`) — 为 Scheduler 和评分插件提供天文/地理基础数据。

**前置依赖**: Module 01（数据模型 `Location`, `Target`, `SunEvents`, `MoonStatus`, `StargazingWindow`）

## 设计依据

- [01-architecture.md](../design/01-architecture.md): §1.4 整体架构 — AstroUtils, GeoUtils
- [04-data-flow-example.md](../design/04-data-flow-example.md): §Stage 2 天文计算输出
- [06-class-sequence.md](../design/06-class-sequence.md): §6.2 数据获取层类图
- [07-code-interface.md](../design/07-code-interface.md): §7.1 IAstroCalculator, IGeoCalculator Protocol

## 待创建文件列表

| 文件 | 说明 |
|------|------|
| `gmp/astro/__init__.py` | 包初始化 |
| `gmp/astro/astro_utils.py` | 天文计算（日出/日落/月相/观星窗口） |
| `gmp/astro/geo_utils.py` | 地理计算（方位角/光路/距离） |
| `tests/unit/__init__.py` | 测试包 |
| `tests/unit/test_astro_utils.py` | 天文计算测试 |
| `tests/unit/test_geo_utils.py` | 地理计算测试 |

## 代码接口定义

### `gmp/astro/astro_utils.py`

```python
from datetime import date, datetime
from gmp.core.models import SunEvents, MoonStatus, StargazingWindow

class AstroUtils:
    """天文计算工具"""
    
    def get_sun_events(self, lat: float, lon: float, target_date: date) -> SunEvents:
        """计算指定地点和日期的日出/日落信息
        
        返回:
            SunEvents: 包含 sunrise, sunset, sunrise_azimuth, sunset_azimuth,
                       astronomical_dawn, astronomical_dusk
        
        实现: 使用 ephem 或 skyfield 库
        """
    
    def get_moon_status(self, lat: float, lon: float, dt: datetime) -> MoonStatus:
        """计算指定时刻的月球状态
        
        返回:
            MoonStatus: 包含 phase(0-100), elevation, moonrise, moonset
        """
    
    def determine_stargazing_window(
        self, sun_events: SunEvents, moon_status: MoonStatus
    ) -> StargazingWindow:
        """根据日落/月相/月出月落确定最佳观星时间窗口
        
        判定逻辑（优先级从高到低）:
        1. optimal: 月亮在地平线下期间 → max(astro_dusk, moonset) ~ min(astro_dawn, moonrise)
        2. good: 月相 < 50% → astro_dusk ~ astro_dawn
        3. partial: 月相 ≥ 50% 但有月下时段 → moonset ~ astro_dawn
        4. poor: 满月整夜
        """
```

### `gmp/astro/geo_utils.py`

```python
class GeoUtils:
    """地理计算工具（全部为静态/类方法）"""
    
    @staticmethod
    def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间的方位角 (0°=北, 90°=东, 180°=南, 270°=西)
        
        公式: Haversine 初始方位角公式
        """
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间的地球表面距离 (km)
        
        公式: Haversine 距离公式
        """
    
    @staticmethod
    def calculate_destination(lat: float, lon: float, distance_km: float, bearing: float) -> tuple[float, float]:
        """给定起点、距离和方位角，计算终点坐标
        
        用途: 生成光路检查点坐标
        """
    
    @staticmethod
    def calculate_light_path_points(
        lat: float, lon: float, azimuth: float,
        count: int = 10, interval_km: float = 10
    ) -> list[tuple[float, float]]:
        """沿太阳方位角方向生成光路检查点
        
        参数:
            azimuth: 太阳方位角（日出/日落时）
            count: 检查点数量（默认 10）
            interval_km: 检查点间距（默认 10km）
        
        返回: [(lat1, lon1), (lat2, lon2), ...] 共 count 个点
        说明: 第 1 个点距起点 interval_km，第 N 个点距起点 N*interval_km
        """
    
    @staticmethod
    def is_opposite_direction(bearing_to_target: float, sun_azimuth: float) -> bool:
        """判断山峰是否在太阳的对面方向
        
        逻辑:
        - 计算太阳方位角的对面 = (sun_azimuth + 180) % 360
        - 若 bearing_to_target 与对面方向夹角 < 90°，则适配
        
        用途: 自动匹配 Target 适用于 sunrise 还是 sunset
        """
    
    @staticmethod
    def round_coords(lat: float, lon: float, precision: int = 2) -> tuple[float, float]:
        """坐标取整（用于缓存 key 生成）
        
        precision=2 → 约 1km 精度
        """
```

## 实现要点

### AstroUtils 实现细节

1. **推荐使用 `ephem` 库**: 轻量级、计算精确，适合日出日落和月相计算
2. **方位角计算**: `ephem` 可直接获取 `sun.az`（太阳方位角），需注意弧度/度转换
3. **天文晨暮曦**: 太阳低于地平线 18° 的时刻，`ephem` 通过设置 `observer.horizon = '-18'` 实现
4. **观星窗口判定**: 需注意月出月落可能为 `None`（极端情况，如月亮整夜在地平线上/下）

### GeoUtils 实现细节

1. **Haversine 公式**: 地球半径取 6371km
2. **方位角公式**: `atan2(sin(Δlon)*cos(lat2), cos(lat1)*sin(lat2) - sin(lat1)*cos(lat2)*cos(Δlon))`
3. **光路检查点**: 沿方位角方向等距生成，起点为观景台坐标
4. **`is_opposite_direction`**: 注意角度环绕（如 350° 和 10° 的夹角是 20°，不是 340°）

### 关于方向匹配逻辑

设计文档 `04-data-flow-example.md` Stage 2 中的示例：
- 牛背山→贡嘎方位角 = 245°
- 日出方位角 = 108.5°，对面 = 288.5°
- |245 - 288.5| = 43.5° < 90° → 贡嘎适配 sunrise ✅

## 测试计划

### 测试操作步骤

```bash
source venv/bin/activate
pip install ephem  # 或 skyfield
python -m pytest tests/unit/test_astro_utils.py tests/unit/test_geo_utils.py -v
```

### 具体测试用例

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `test_geo_utils.py` | `test_bearing_niubei_to_gongga` | 牛背山→贡嘎方位角 ≈ 245° (±5°) |
| `test_geo_utils.py` | `test_distance_niubei_to_gongga` | 距离 ≈ 51km (±5km) |
| `test_geo_utils.py` | `test_light_path_10points` | 方位角108.5°起点(29.75, 102.35) → 返回 10 个坐标，间隔约 10km |
| `test_geo_utils.py` | `test_destination_accuracy` | 已知起点+距离+方位角 → 终点坐标误差 < 0.01° |
| `test_geo_utils.py` | `test_is_opposite_true` | bearing=245°, azimuth=108.5° → True |
| `test_geo_utils.py` | `test_is_opposite_false` | bearing=100°, azimuth=108.5° → False |
| `test_geo_utils.py` | `test_round_coords` | (29.755, 102.349) → (29.76, 102.35) |
| `test_geo_utils.py` | `test_angle_wrap_around` | 角度环绕: 350° 和 10° 夹角 = 20° |
| `test_astro_utils.py` | `test_sun_events_niubei_feb11` | 2026-02-11 牛背山日出 ≈ 07:28, 日落 ≈ 18:35 (±15min) |
| `test_astro_utils.py` | `test_sunrise_azimuth_feb` | 2月日出方位角 ≈ 105°-115° (偏南) |
| `test_astro_utils.py` | `test_moon_phase_range` | moon_status.phase 在 0-100 之间 |
| `test_astro_utils.py` | `test_stargazing_optimal` | 月落在白天+残月 → quality="optimal" |
| `test_astro_utils.py` | `test_stargazing_poor` | 满月整夜 → quality="poor" |
| `test_astro_utils.py` | `test_astronomical_dawn_dusk` | 天文晨暮曦时太阳低于地平线18° |

## 验收标准

- [ ] 所有 `tests/unit/test_astro_utils.py` 和 `tests/unit/test_geo_utils.py` 测试通过
- [ ] 方位角计算精度 < 1°
- [ ] 光路10点坐标生成正确（首点距起点约10km，末点约100km）
- [ ] 观星窗口四个等级判定逻辑正确
- [ ] `is_opposite_direction` 正确处理角度环绕
