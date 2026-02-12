# M03: GeoUtils 地理计算工具

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现地理坐标相关的纯计算工具类，包括方位角计算、距离计算、目的地推算、光路点生成。

**依赖模块:** M01 (项目初始化)

---

## 背景

GMP 中的地理计算主要服务于：
1. **日照金山 Plugin**: 计算观景台到目标山峰的**方位角 (bearing)**，判断与日出/日落方位的匹配
2. **光路检查**: 沿太阳方位角方向，每隔一定距离生成检查点坐标，用于获取沿途云量
3. **缓存去重**: 将坐标四舍五入到 2 位小数 (≈1km 精度)，相近坐标共享天气缓存

### 关键参数（来自配置）
- `light_path.count`: 光路检查点数量（默认 10）
- `light_path.interval_km`: 检查点间隔（默认 10km）

### 参考接口 (设计文档 07-code-interface.md)

```python
class IGeoCalculator(Protocol):
    def calculate_light_path_points(
        self, lat: float, lon: float, azimuth: float,
        count: int = 10, interval_km: float = 10
    ) -> list[tuple[float, float]]: ...
```

---

## Task 1: GeoUtils 静态方法实现

**Files:**
- Create: `gmp/data/geo_utils.py`
- Test: `tests/unit/test_geo_utils.py`

### 要实现的函数

所有函数均为 `@staticmethod`，无状态。

#### 1. `calculate_bearing(lat1, lon1, lat2, lon2) -> float`
- 计算从点1到点2的初始方位角 (0°=北, 90°=东, 180°=南, 270°=西)
- 使用 Haversine 公式的方位角变体
- 公式:
  ```
  Δlon = lon2 - lon1
  x = sin(Δlon) * cos(lat2)
  y = cos(lat1)*sin(lat2) - sin(lat1)*cos(lat2)*cos(Δlon)
  bearing = atan2(x, y) → 转换到 0-360°
  ```

#### 2. `calculate_distance(lat1, lon1, lat2, lon2) -> float`
- 返回两点间距离（单位: km）
- 使用 Haversine 公式
- 地球半径取 6371 km

#### 3. `calculate_destination(lat, lon, distance_km, bearing) -> tuple[float, float]`
- 从起点沿给定方位角和距离推算目标点坐标
- 使用 Vincenty 正算或球面三角简化公式
- 返回 `(lat, lon)`

#### 4. `calculate_light_path_points(lat, lon, azimuth, count, interval_km) -> list[tuple[float, float]]`
- 沿 `azimuth` 方位角方向，从起点开始每隔 `interval_km` 生成一个检查点
- 返回 `count` 个点的坐标列表 (不含起点)
- 每个坐标四舍五入到 2 位小数

#### 5. `is_opposite_direction(bearing_to_target, sun_azimuth) -> bool`
- 判断目标方位角是否在太阳方位角的"对面"
- 日出场景: 光从太阳方向来（azimuth），照射对面（azimuth+180°±90°）的山峰
- 逻辑: `|bearing_to_target - (sun_azimuth + 180)°| < 90°`（考虑 360° 环绕）
- 用于判断目标山峰是否适合当前日出/日落事件

#### 6. `round_coords(lat, lon, precision=2) -> tuple[float, float]`
- 将坐标四舍五入到指定小数位
- 默认 2 位 ≈ 1km 精度
- 用于缓存键生成

### 应测试的内容

**`test_calculate_bearing`:**
- 牛背山 (29.75, 102.35) → 贡嘎主峰 (29.58, 101.88)，方位角应 ≈ 245° (西南)
- 正北方向: (0, 0) → (1, 0) ≈ 0°
- 正东方向: (0, 0) → (0, 1) ≈ 90°
- 相同点: bearing 任意（不报错即可）

**`test_calculate_distance`:**
- 牛背山 → 贡嘎: ≈ 50-55km (已知地理距离)
- 同一点: 0km
- 赤道上经度相差1°: ≈ 111km

**`test_calculate_destination`:**
- 从 (0, 0) 向东走 111km ≈ (0, 1)
- 从牛背山沿 108.5° 走 10km，验证合理坐标范围

**`test_calculate_light_path_points`:**
- 方位角 108.5°，起点 (29.75, 102.35)，10点、间隔10km
- 返回恰好 10 个坐标
- 每个坐标到起点的距离依次约为 10km, 20km, ..., 100km
- 坐标已四舍五入到 2 位小数

**`test_is_opposite_direction`:**
- bearing=245°, azimuth=108.5° (108.5+180=288.5, |245-288.5|=43.5 < 90) → True (适配 sunrise)
- bearing=90°, azimuth=108.5° (反方向 288.5°, |90-288.5|=198.5 > 90) → False
- bearing=250°, azimuth=251.5° (对面 71.5°, |250-71.5|=178.5 > 90) → False（此场景是日落）

**`test_round_coords`:**
- (29.755, 102.349) → (29.76, 102.35)
- (29.751, 102.354) → (29.75, 102.35)
- 精度=0: (29.755, 102.349) → (30.0, 102.0)

---

## 验证命令

```bash
python -m pytest tests/unit/test_geo_utils.py -v
```
