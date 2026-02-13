# M08: 评分引擎核心 (ScoreEngine + DataContext + Plugin 接口)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现评分引擎的核心框架：`ScoreEngine` Plugin 注册中心、`DataRequirement` / `DataContext` 数据模型、`ScorerPlugin` Protocol 接口。

**依赖模块:** M02 (数据模型: `ScoreResult`, `DataContext` 等), M07 (ConfigManager)

---

## 背景

ScoreEngine 是 GMP 评分系统的核心注册中心，职责：
1. 管理所有 Plugin 实例的注册
2. 按条件筛选活跃 Plugin (capabilities / season / events 过滤)
3. 聚合 Plugin 的数据需求 (`DataRequirement`)

### 架构要点 (设计文档 §3.2 + §6.3)

- **`ScorerPlugin` Protocol**: 定义 `event_type`, `display_name`, `data_requirement`, `score(ctx) -> ScoreResult | None`, `dimensions() -> list[str]` 接口
- **`ScoreEngine`**: 注册 Plugin, 按 event_type 索引, 聚合 requirements
- **`DataRequirement`**: Plugin 声明需要哪些数据 (L2 target, L2 light_path, astro, past_hours, season)
- **`DataContext`**: 一天内所有 Plugin 共享的数据上下文

### capability → event_type 映射 (设计文档 §3.2)

```python
_CAPABILITY_EVENT_MAP = {
    "sunrise": ["sunrise_golden_mountain"],
    "sunset":  ["sunset_golden_mountain"],
    "stargazing": ["stargazing"],
    "cloud_sea":  ["cloud_sea"],
    "frost":      ["frost"],
    "snow_tree":  ["snow_tree"],
    "ice_icicle": ["ice_icicle"],
}
```

---

## Task 1: 评分数据模型 (`gmp/scoring/models.py`)

**Files:**
- Create: `gmp/scoring/models.py`
- Test: `tests/unit/test_scoring_models.py`

### 要实现的 dataclass

```python
@dataclass
class DataRequirement:
    """评分器的数据需求声明"""
    needs_l2_target: bool = False
    needs_l2_light_path: bool = False
    needs_astro: bool = False
    past_hours: int = 0
    season_months: list[int] | None = None

@dataclass
class DataContext:
    """一天的共享数据上下文 — 所有 Plugin 复用"""
    date: date
    viewpoint: Viewpoint
    local_weather: pd.DataFrame
    sun_events: SunEvents | None = None
    moon_status: MoonStatus | None = None
    stargazing_window: StargazingWindow | None = None
    target_weather: dict[str, pd.DataFrame] | None = None
    light_path_weather: list[dict] | None = None
    data_freshness: str = "fresh"
```

> **注意**: `ScoreResult` 已在 M02 的 `gmp/core/models.py` 中定义。此处可考虑从 `core.models` 导入，或在此文件中补充评分专有的数据类。

### 应测试的内容

- `DataRequirement` 各默认值正确
- `DataContext` 构建: 必填字段 + 可选字段为 None
- `DataContext.data_freshness` 默认 "fresh"
- `DataRequirement.season_months` 为 None 表示全年

---

## Task 2: ScoreEngine — Plugin 注册中心

**Files:**
- Create: `gmp/scoring/engine.py`
- Test: `tests/unit/test_score_engine.py`

### 要实现的类

```python
class ScoreEngine:
    def __init__(self):
        self._plugins: dict[str, ScorerPlugin] = {}

    def register(self, plugin: ScorerPlugin) -> None:
        """注册一个评分 Plugin (按 event_type 索引)"""

    def all_plugins(self) -> list[ScorerPlugin]:
        """返回所有已注册 Plugin"""

    def get(self, event_type: str) -> ScorerPlugin | None:
        """按 event_type 获取"""

    def collect_requirements(self, plugins: list[ScorerPlugin]) -> DataRequirement:
        """聚合多个 Plugin 的数据需求
        - needs_l2_target = any(p.needs_l2_target for p)
        - needs_l2_light_path = any(p.needs_l2_light_path for p)
        - needs_astro = any(p.needs_astro for p)
        - past_hours = max(p.past_hours for p)
        """

    def filter_active_plugins(
        self,
        capabilities: list[str],
        target_date: date,
        events_filter: list[str] | None = None,
    ) -> list[ScorerPlugin]:
        """筛选活跃 Plugin:
        1. 将 capabilities 展开为 event_type 集合 (通过 _CAPABILITY_EVENT_MAP)
        2. 按 event_type 筛选 Plugin
        3. 应用 events_filter (用户指定仅评分某些事件)
        4. 按 season_months 过滤 (当月不在适用月份则跳过)
        """
```

### `_CAPABILITY_EVENT_MAP` 定义

此映射表应放在 `engine.py` 模块级别，或从配置中加载：

```python
_CAPABILITY_EVENT_MAP: dict[str, list[str]] = {
    "sunrise": ["sunrise_golden_mountain"],
    "sunset":  ["sunset_golden_mountain"],
    "stargazing": ["stargazing"],
    "cloud_sea":  ["cloud_sea"],
    "frost":      ["frost"],
    "snow_tree":  ["snow_tree"],
    "ice_icicle": ["ice_icicle"],
}
```

### 应测试的内容

**Plugin 注册:**
- 注册成功后 `all_plugins()` 包含该 Plugin
- `get("cloud_sea")` 返回注册的 Plugin
- `get("不存在")` 返回 None
- 重复注册同 event_type 覆盖旧的

**需求聚合:**
- 空列表 → 默认 DataRequirement (全 False, past_hours=0)
- 仅 CloudSea → needs_l2=False, needs_astro=False
- GoldenMountain + Stargazing → needs_l2_target=True, needs_astro=True
- SnowTree(past_hours=24) + Frost(past_hours=0) → past_hours=24

**Plugin 过滤:**
- capabilities=["sunrise", "cloud_sea"] → 仅 sunrise_golden_mountain 和 cloud_sea 的 Plugin
- events_filter=["cloud_sea"] → 仅保留 cloud_sea
- season_months=[10,11] + 日期为1月 → Plugin 被跳过
- season_months=None → Plugin 保留

---

## Task 3: 创建测试用 Stub Plugin

为测试 `ScoreEngine`，创建简单的 Stub Plugin 实现：

**Files:**
- Create: `tests/conftest.py` (或 `tests/helpers/stub_plugins.py`)

```python
class StubPlugin:
    """测试用最小 Plugin 实现"""
    def __init__(self, event_type, display_name="Stub", requirement=None):
        self._event_type = event_type
        self._display_name = display_name
        self._requirement = requirement or DataRequirement()

    @property
    def event_type(self): return self._event_type
    @property
    def display_name(self): return self._display_name
    @property
    def data_requirement(self): return self._requirement

    def score(self, context: DataContext) -> ScoreResult | None: return None
    def dimensions(self) -> list[str]: return []
```

---

## 验证命令

```bash
python -m pytest tests/unit/test_scoring_models.py tests/unit/test_score_engine.py -v
```
