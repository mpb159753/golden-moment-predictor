# M03 - 天文与地理计算能力

## 1. 模块目标

为评分系统提供可复用的时间/方位基础能力：

- 日出日落与方位角
- 月相/月出月落
- 观星窗口判定
- 光路 10 点坐标计算

---

## 2. 背景上下文

- 参考：`design/03-scoring-plugins.md`、`design/04-data-flow-example.md`、`design/09-testing-config.md`
- 关键规则：
  - 光路点：沿方位角每 10km 取 1 点，共 10 点
  - `is_opposite_direction`：目标方向与太阳反方向夹角 < 90° 视为匹配
  - 观星窗口按“月亮高度+月相”分为 optimal/good/partial/poor

---

## 3. 交付范围

### 本模块要做

1. `astro/geo_utils.py`
2. `astro/astro_utils.py`
3. 可直接被 Scheduler 与 Plugin 调用的 API

### 本模块不做

- 不做天气获取（M02）
- 不做评分计算（M05）

---

## 4. 输入与输出契约

### 输入

- 站点坐标、目标日期/时间
- `EngineConfig.light_path` 配置（点数、间隔）

### 输出

- `SunEvents`、`MoonStatus`、`StargazingWindow`
- 光路点坐标列表 `list[(lat, lon)]`

---

## 5. 实施任务清单

1. 在 `geo_utils.py` 实现：
   - `calculate_bearing(p1, p2)`
   - `calculate_distance(p1, p2)`
   - `calculate_destination(lat, lon, distance_km, bearing_deg)`
   - `round_coords(lat, lon, precision)`
   - `is_opposite_direction(bearing_to_target, sun_azimuth)`
   - `calculate_light_path_points(...)`
2. 在 `astro_utils.py` 实现：
   - `get_sun_events(...)`：含日出/日落/晨暮曦与方位角
   - `get_moon_status(...)`：相位、月出月落、仰角
   - `determine_stargazing_window(...)`
3. 对外接口保持稳定，避免与具体评分插件耦合。

---

## 6. 验收标准

1. 方位角结果可复现示例：牛背山→贡嘎约 245°；
2. 光路点数量和间距满足 10 点、约 10km；
3. 观星窗口质量分级符合设计表；
4. 方法对极端输入（高纬、月出/月落缺失）有可预期行为。

---

## 7. 测试清单

- `tests/unit/test_geo_utils.py`
  - `test_bearing_gongga`
  - `test_light_path_10pts`
  - `test_opposite_direction`
  - `test_coord_rounding`
- `tests/unit/test_astro_utils.py`
  - `test_sun_events_fields_complete`
  - `test_stargazing_window_optimal`
  - `test_stargazing_window_poor`

---

## 8. 新会话启动提示词

```text
请根据 implementation_plan/module-03-astro-geo.md 完成 M03：
实现 GeoUtils 与 AstroUtils，包括方位角、光路点、日月事件与观星窗口判定。
要求：可通过文档给出的关键测试样例（bearing≈245°, 10点光路, optimal/poor窗口）。
完成后汇报关键函数签名与单测结果。
```
