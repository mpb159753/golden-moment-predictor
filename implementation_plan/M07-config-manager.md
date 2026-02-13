# M07: 配置管理

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现统一配置管理器，包括引擎配置 (`ConfigManager`)、观景台配置 (`ViewpointConfig`)、线路配置 (`RouteConfig`) 的加载与访问。

**依赖模块:** M02 (数据模型: `Viewpoint`, `Route`, `RouteStop`, `Location`, `Target`) — 注意 `EngineConfig` 定义在本模块 (`gmp/core/config_loader.py`) 中，不从 M02 导入。

---

## 背景

GMP 的配置分为三层：

1. **引擎配置** (`config/engine_config.yaml`): 全局参数 — 缓存策略、安全阈值、评分权重/阈值、光路参数、置信度映射
2. **观景台配置** (`config/viewpoints/*.yaml`): 各观景台的坐标、支持景观类型、目标山峰
3. **线路配置** (`config/routes/*.yaml`): 线路定义、停靠点列表

所有评分阈值和权重**必须来自配置文件**，代码中零魔法数字。

### 配置文件格式参考

**engine_config.yaml** — 完整结构见 [09-testing-config.md §9.5](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/09-testing-config.md)

关键部分摘要：
```yaml
cache:
  db_path: "data/gmp.db"
  freshness:
    forecast_valid_hours: 24
    archive_never_stale: true

safety:
  precip_threshold: 50
  visibility_threshold: 1000

light_path:
  count: 10
  interval_km: 10

scoring:
  golden_mountain:
    trigger: { max_cloud_cover: 80 }
    weights: { light_path: 35, target_visible: 40, local_clear: 25 }
    thresholds:
      light_path_cloud: [10, 20, 30, 50]
      target_cloud: [10, 20, 30, 50]
      local_cloud: [15, 30, 50]
    veto_threshold: 0
  # ... 其他 Plugin 详见设计文档 §9.5

confidence:
  high: [1, 2]
  medium: [3, 4]
  low: [5, 16]

summary:
  mode: "rule"
```

**viewpoints/niubei_gongga.yaml** — 见 [09-testing-config.md §9.6](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/09-testing-config.md)

```yaml
id: niubei_gongga
name: 牛背山
location: { lat: 29.75, lon: 102.35, altitude: 3660 }
capabilities: [sunrise, sunset, stargazing, cloud_sea, frost, snow_tree, ice_icicle]
targets:
  - name: 贡嘎主峰
    lat: 29.58
    lon: 101.88
    altitude: 7556
    weight: primary
    applicable_events: null
  - name: 雅拉神山
    lat: 30.15
    lon: 101.75
    altitude: 5820
    weight: secondary
    applicable_events: [sunset]
```

---

## Task 1: ConfigManager — 引擎配置加载

**Files:**
- Create: `gmp/core/config_loader.py` (ConfigManager 部分)
- Create: `config/engine_config.yaml`
- Test: `tests/unit/test_config_loader.py`

### 要实现的类

```python
@dataclass
class EngineConfig:
    """全局引擎配置 — 字段定义见设计文档 §7.3"""
    db_path: str = "data/gmp.db"
    output_dir: str = "public/data"
    archive_dir: str = "archive"
    log_level: str = "INFO"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    archive_api_base_url: str = "https://archive-api.open-meteo.com/v1/archive"
    forecast_days: int = 7
    light_path_count: int = 10
    light_path_interval_km: float = 10.0
    data_freshness: dict = field(default_factory=...)
    safety: dict = field(default_factory=...)
    scoring: dict = field(default_factory=...)
    confidence: dict = field(default_factory=...)
    summary_mode: str = "rule"
    backtest_max_history_days: int = 365

class ConfigManager:
    def __init__(self, config_path: str = "config/engine_config.yaml"):
        self.config: EngineConfig = self._load(config_path)

    def _load(self, path: str) -> EngineConfig:
        """加载 YAML → EngineConfig"""

    def get_plugin_config(self, event_type: str) -> dict:
        """获取指定 Plugin 的评分配置 (权重 + 阈值 + 触发条件)
        event_type 如 "golden_mountain", "cloud_sea" 等
        """

    def get_safety_config(self) -> dict:
        """返回安全阈值配置"""

    def get_light_path_config(self) -> dict:
        """返回光路计算配置"""

    def get_confidence_config(self) -> dict:
        """返回置信度映射配置"""

    def get_output_config(self) -> dict:
        """返回输出路径配置"""
```

### 应测试的内容

- 加载有效 YAML 文件 → EngineConfig 属性正确
- `get_plugin_config("golden_mountain")` 返回正确的 weights/thresholds
- `get_plugin_config("不存在的plugin")` 返回空 dict 或 None
- `get_safety_config()` 返回 precip_threshold 和 visibility_threshold
- 文件不存在 → 合理错误提示
- YAML 格式错误 → 合理错误提示
- 使用默认值: 缺少某字段时使用 dataclass 默认值

---

## Task 2: ViewpointConfig — 观景台配置加载

**Files:**
- Modify: `gmp/core/config_loader.py` (添加 ViewpointConfig)
- Create: `config/viewpoints/niubei_gongga.yaml`
- Test: `tests/unit/test_viewpoint_config.py`

### 要实现的类

```python
class ViewpointConfig:
    def __init__(self):
        self._viewpoints: dict[str, Viewpoint] = {}

    def load(self, path: str) -> None:
        """加载目录下所有 *.yaml 文件为 Viewpoint 对象"""

    def get(self, viewpoint_id: str) -> Viewpoint:
        """按 ID 获取，不存在抛 ViewpointNotFoundError"""

    def list_all(self) -> list[Viewpoint]:
        """返回所有已加载的观景台"""
```

### YAML → Viewpoint 转换逻辑
- `location` → `Location(lat, lon, altitude)`
- `targets` → `list[Target]`
- `applicable_events: null` → `None` (自动计算)

### 应测试的内容

- 加载 `niubei_gongga.yaml` → Viewpoint 属性完整
- `get("niubei_gongga")` 返回正确对象
- `get("不存在")` → `ViewpointNotFoundError`
- `list_all()` 返回所有加载的观景台
- Target 的 `applicable_events=null` → `None`
- 加载空目录 → 空列表 (不报错)

---

## Task 3: RouteConfig — 线路配置加载

**Files:**
- Modify: `gmp/core/config_loader.py` (添加 RouteConfig)
- Create: `config/routes/lixiao.yaml`
- Test: `tests/unit/test_route_config.py`

### 线路 YAML 格式

```yaml
id: lixiao
name: 理小路
description: 理塘→小金/丹巴 经典自驾线路
stops:
  - viewpoint_id: zheduo_gongga
    order: 1
    stay_note: 建议日出前2小时到达
  - viewpoint_id: niubei_gongga
    order: 2
    stay_note: 推荐过夜，可同时观测金山+云海+星空
```

### 要实现的类

```python
class RouteConfig:
    def __init__(self):
        self._routes: dict[str, Route] = {}

    def load(self, path: str) -> None:
        """加载目录下所有 *.yaml 文件为 Route 对象"""

    def get(self, route_id: str) -> Route:
        """按 ID 获取，不存在抛 RouteNotFoundError"""

    def list_all(self) -> list[Route]:
        """返回所有已加载的线路"""
```

### 应测试的内容

- 加载 `lixiao.yaml` → Route 属性完整
- `stops` 按 `order` 排序
- `get("lixiao")` 正常访问
- `get("不存在")` → `RouteNotFoundError`
- `list_all()` 返回正确数量

---

## 验证命令

```bash
python -m pytest tests/unit/test_config_loader.py tests/unit/test_viewpoint_config.py tests/unit/test_route_config.py -v
```
