# M04: AstroUtils 天文计算工具

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现天文计算工具类，包括日出日落（含方位角）、天文晨暮曦、月相/月出月落、观星窗口判定。

**依赖模块:** M02 (数据模型: `SunEvents`, `MoonStatus`, `StargazingWindow`), M03 (GeoUtils)

---

## 背景

GMP 中的天文计算服务于：
1. **GoldenMountainPlugin**: 需要日出/日落时刻及方位角 (与 GeoUtils 联合判定目标匹配)
2. **StargazingPlugin**: 需要天文晨暮曦、月相、月出月落来确定最佳暗夜窗口

天文计算使用 `ephem` 库，所有计算基于观景台坐标和目标日期。

### 参考接口 (设计文档 07-code-interface.md)

```python
class IAstroCalculator(Protocol):
    def get_sun_events(self, lat: float, lon: float, target_date: date) -> SunEvents: ...
    def get_moon_status(self, lat: float, lon: float, dt: datetime) -> MoonStatus: ...
    def determine_stargazing_window(
        self, sun_events: SunEvents, moon_status: MoonStatus
    ) -> StargazingWindow: ...
```

### 关键数据类 (已在 M02 定义)

```python
@dataclass
class SunEvents:
    sunrise: datetime           # 日出时刻
    sunset: datetime            # 日落时刻
    sunrise_azimuth: float      # 日出方位角 0-360°
    sunset_azimuth: float       # 日落方位角 0-360°
    astronomical_dawn: datetime  # 天文晨曦 (太阳 -18°)
    astronomical_dusk: datetime  # 天文暮曦 (太阳 -18°)

@dataclass
class MoonStatus:
    phase: int          # 0-100 月照百分比
    elevation: float    # 月球仰角 (度)
    moonrise: Optional[datetime]
    moonset: Optional[datetime]

@dataclass
class StargazingWindow:
    optimal_start: Optional[datetime]
    optimal_end: Optional[datetime]
    good_start: Optional[datetime]
    good_end: Optional[datetime]
    quality: str        # "optimal" | "good" | "partial" | "poor"
```

---

## Task 1: `get_sun_events` — 日出日落计算

**Files:**
- Create: `gmp/data/astro_utils.py`
- Test: `tests/unit/test_astro_utils.py`

### 实现要点

使用 `ephem` 库计算：

```python
class AstroUtils:
    @staticmethod
    def get_sun_events(lat: float, lon: float, target_date: date) -> SunEvents:
        """计算指定坐标和日期的日出日落+天文晨暮曦"""
        # 1. 创建 ephem.Observer(lat, lon, elevation=0)
        # 2. observer.date = target_date (UTC)
        # 3. observer.horizon = '0' → sunrise/sunset
        # 4. observer.horizon = '-18' → astronomical_dawn/dusk
        # 5. 计算 sun azimuth at sunrise/sunset 时刻
        # 6. 返回 SunEvents (注意时区: ephem 使用 UTC)
```

> **时区注意**: 川西地区使用 UTC+8。ephem 返回 UTC 时间，需转换为本地时间。

### 应测试的内容

- 牛背山 2026-02-11: sunrise ≈ 07:28 CST, sunset ≈ 18:35 CST (与设计文档 Stage 2 对比)
- sunrise_azimuth ≈ 108.5° (东偏南)
- sunset_azimuth ≈ 251.5° (西偏南)
- astronomical_dawn 应早于 sunrise (约 05:55 CST)
- astronomical_dusk 应晚于 sunset (约 19:55 CST)
- 极端情况: 高纬度地区极昼/极夜处理（可选，川西不遇到）

---

## Task 2: `get_moon_status` — 月相月出月落

### 实现要点

```python
@staticmethod
def get_moon_status(lat: float, lon: float, dt: datetime) -> MoonStatus:
    """计算指定时刻的月球状态"""
    # 1. ephem.Moon() + observer 计算月相百分比
    # 2. moon.alt → elevation (度)
    # 3. observer.next_rising(moon) / observer.next_setting(moon) → moonrise/moonset
    #    需要也检查 previous_rising/previous_setting 来确保覆盖当天
    # 4. 月相: phase 0-100
```

### 应测试的内容

- 2026-02-11 牛背山: phase ≈ 35%, moonrise ≈ 03:15 CST, moonset ≈ 13:40 CST
- 满月时 phase ≈ 100
- 新月时 phase ≈ 0
- moonrise/moonset 可能为 None (极端情况)

---

## Task 3: `determine_stargazing_window` — 观星窗口判定

### 实现要点

观星窗口判定逻辑 (见设计文档 §3.6):

```python
@staticmethod
def determine_stargazing_window(
    sun_events: SunEvents, moon_status: MoonStatus
) -> StargazingWindow:
    """判定观星窗口质量和时间范围"""
    # 优先级判定:
    # 🥇 optimal: 月亮在地平线下 → max(dusk, moonset) ~ min(dawn, moonrise) = optimal 窗口
    # 🥈 good: 月相 < 50% → dusk ~ dawn = good 窗口
    # 🥉 partial: 月相 ≥ 50% 但月下时段可观 → moonset ~ dawn
    # ❌ poor: 满月整夜
```

### 时间窗口判定规则表

| 优先级 | 条件 | `optimal_start` | `optimal_end` | quality |
|--------|------|-----------------|---------------|---------|
| 🥇 | 月亮在夜间有下落时段 | `max(dusk, moonset)` | `min(dawn, moonrise)` | `"optimal"` |
| 🥈 | 月相 < 50% (弦月以下) | `dusk` | `dawn` | `"good"` |
| 🥉 | 月相 ≥ 50% 但月落在夜间 | `moonset` | `dawn` | `"partial"` |
| ❌ | 满月整夜 | None | None | `"poor"` |

### 应测试的内容

- **optimal 场景**: 月落白天 (13:40), 月相 35% → quality="optimal", optimal_start=19:55, optimal_end=03:15
- **good 场景**: 月相 40%, 月亮整夜在天 → quality="good", 全夜 dusk~dawn
- **partial 场景**: 月相 70%, 月落 02:00 → quality="partial", partial from moonset~dawn
- **poor 场景**: 月相 95%, 月亮整夜 → quality="poor"
- 边界: dawn/dusk 为 None (极端纬度) — 可选测试

---

## 验证命令

```bash
python -m pytest tests/unit/test_astro_utils.py -v
```
