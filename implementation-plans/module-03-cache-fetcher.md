# Module 03: 缓存层与气象数据获取

## 模块背景

本模块实现系统的数据持久化（SQLite 缓存）和气象数据获取（Open-Meteo API 客户端）。采用三级缓存架构：内存缓存（TTL 5min）→ SQLite 持久化 → 外部 API。确保同一坐标的天气数据不重复请求。

**在系统中的位置**: 数据获取层 (`gmp/fetcher/`) + 缓存层 (`gmp/cache/`) + 数据库初始化 (`gmp/db/`)

**前置依赖**: Module 01（`EngineConfig`, `Location`, 异常类）

## 设计依据

- [01-architecture.md](../design/01-architecture.md): §1.6 缓存架构设计
- [02-data-model.md](../design/02-data-model.md): §2.2 数据库表结构, §2.3 记录示例
- [06-class-sequence.md](../design/06-class-sequence.md): §6.2 数据获取层类图, §6.6 缓存与降级流程
- [07-code-interface.md](../design/07-code-interface.md): §7.1 IFetcher, ICacheRepository Protocol
- [08-operations.md](../design/08-operations.md): §8.2 降级策略, §8.3 超时配置, §8.7 并发, §8.9 请求合并
- [09-testing-config.md](../design/09-testing-config.md): §9.4 Mock 数据策略

## 待创建文件列表

| 文件 | 说明 |
|------|------|
| `gmp/cache/__init__.py` | 包初始化 |
| `gmp/cache/memory_cache.py` | 内存缓存（TTL 过期） |
| `gmp/cache/repository.py` | SQLite CRUD 操作 |
| `gmp/cache/weather_cache.py` | 多级缓存门面（Memory → SQLite → API） |
| `gmp/db/__init__.py` | 包初始化 |
| `gmp/db/init_db.py` | 数据库建表脚本 |
| `gmp/fetcher/__init__.py` | 包初始化 |
| `gmp/fetcher/base.py` | BaseFetcher 抽象基类 |
| `gmp/fetcher/meteo_fetcher.py` | Open-Meteo API 实现 |
| `gmp/fetcher/mock_fetcher.py` | Mock 实现（测试用） |
| `tests/unit/test_cache.py` | 缓存层单元测试 |
| `tests/integration/__init__.py` | 集成测试包 |
| `tests/integration/test_cache_sqlite.py` | SQLite 集成测试 |
| `tests/fixtures/weather_data_clear.json` | 晴天天气数据 fixture |
| `tests/fixtures/weather_data_rainy.json` | 雨天天气数据 fixture |

## 代码接口定义

### `gmp/db/init_db.py`

```python
import sqlite3

def init_database(db_path: str) -> None:
    """初始化数据库，创建表结构"""
    # 创建 weather_cache 表
    # 创建 prediction_history 表
    # 创建索引
```

**SQL 建表语句** (来自设计文档 §2.2):

```sql
CREATE TABLE IF NOT EXISTS weather_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat_rounded REAL NOT NULL,
    lon_rounded REAL NOT NULL,
    forecast_date DATE NOT NULL,
    forecast_hour INTEGER NOT NULL,
    fetched_at DATETIME NOT NULL,
    api_source TEXT DEFAULT 'open-meteo',
    raw_response_json TEXT,
    temperature_2m REAL,
    cloud_cover_total INTEGER,
    cloud_cover_low INTEGER,
    cloud_cover_medium INTEGER,
    cloud_cover_high INTEGER,
    cloud_base_altitude REAL,
    precipitation_probability INTEGER,
    visibility REAL,
    wind_speed_10m REAL,
    snowfall REAL,
    rain REAL,
    showers REAL,
    weather_code INTEGER,
    UNIQUE(lat_rounded, lon_rounded, forecast_date, forecast_hour)
);

CREATE TABLE IF NOT EXISTS prediction_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    viewpoint_id TEXT NOT NULL,
    prediction_date DATE NOT NULL,
    target_date DATE NOT NULL,
    event_type TEXT NOT NULL,
    predicted_score INTEGER,
    predicted_status TEXT,
    confidence TEXT,
    conditions_json TEXT,
    actual_result TEXT,
    user_feedback TEXT,
    feedback_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `gmp/cache/memory_cache.py`

```python
from datetime import datetime, timedelta
import pandas as pd

class MemoryCache:
    """TTL 内存缓存"""
    
    def __init__(self, ttl_seconds: int = 300):
        self._storage: dict[str, tuple[pd.DataFrame, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> pd.DataFrame | None:
        """获取缓存，过期返回 None"""
    
    def set(self, key: str, data: pd.DataFrame) -> None:
        """写入缓存 + 时间戳"""
    
    def invalidate(self, key: str) -> None:
        """手动失效"""
    
    @staticmethod
    def make_key(lat: float, lon: float, date_str: str) -> str:
        """生成缓存 key: "29.75_102.35_2026-02-11" """
```

### `gmp/cache/repository.py`

```python
class CacheRepository:
    """SQLite 数据操作层"""
    
    def __init__(self, db_path: str):
        self._db_path = db_path
    
    def query(self, lat: float, lon: float, 
              target_date: date, hours: list[int]) -> list[dict] | None:
        """查询天气缓存"""
    
    def upsert(self, lat: float, lon: float,
               target_date: date, hour: int, data: dict) -> None:
        """插入或更新天气缓存 (INSERT OR REPLACE)"""
    
    def save_prediction(self, prediction: dict) -> None:
        """保存预测历史记录"""
    
    def get_history(self, viewpoint_id: str, 
                    date_range: tuple[date, date]) -> list[dict]:
        """查询预测历史"""
```

### `gmp/cache/weather_cache.py`

```python
class WeatherCache:
    """多级缓存门面"""
    
    def __init__(self, memory_cache: MemoryCache, 
                 repository: CacheRepository,
                 ttl_db_seconds: int = 3600):
        ...
    
    def get(self, lat: float, lon: float, target_date: date,
            hours: list[int], ignore_ttl: bool = False) -> pd.DataFrame | None:
        """多级查询: 内存 → SQLite → None"""
    
    def set(self, lat: float, lon: float, target_date: date,
            data: pd.DataFrame) -> None:
        """双写: 内存 + SQLite"""
    
    def get_or_fetch(self, lat: float, lon: float, target_date: date,
                     fetcher_func) -> pd.DataFrame:
        """缓存未命中时自动调用 fetcher"""
```

### `gmp/fetcher/meteo_fetcher.py`

```python
import httpx
import pandas as pd
from gmp.fetcher.base import BaseFetcher

class MeteoFetcher(BaseFetcher):
    """Open-Meteo API 实现"""
    
    API_URL = "https://api.open-meteo.com/v1/forecast"
    
    HOURLY_PARAMS = [
        "temperature_2m", "cloud_cover", "cloud_cover_low",
        "cloud_cover_mid", "cloud_cover_high",
        "precipitation_probability", "visibility",
        "wind_speed_10m", "weather_code",
        "snowfall", "rain", "showers",
    ]
    
    def __init__(self, cache: WeatherCache, timeout_config: dict | None = None):
        ...
    
    def fetch_hourly(self, lat: float, lon: float, days: int = 7) -> pd.DataFrame:
        """获取小时级天气预报（先查缓存再调 API）"""
    
    def fetch_multi_points(self, coords: list[tuple[float, float]], 
                           days: int = 1) -> dict[tuple, pd.DataFrame]:
        """批量获取多个坐标点的天气（坐标去重）"""
    
    def _parse_response(self, response: dict) -> pd.DataFrame:
        """解析 Open-Meteo JSON → DataFrame"""
```

### `gmp/fetcher/mock_fetcher.py`

```python
class MockMeteoFetcher(BaseFetcher):
    """测试用 Mock 数据获取器"""
    
    def __init__(self, scenario: str = "clear"):
        self.scenario = scenario  # "clear" | "rain" | "timeout" | "frost" | "snow" | "ice"
        self.call_log = []
        self.remote_call_count = 0
    
    def fetch_hourly(self, lat, lon, days=7) -> pd.DataFrame:
        """根据 scenario 返回预制天气数据"""
    
    def _generate_clear_weather(self, days) -> pd.DataFrame:
        """典型晴天: 云量低, 无降水, 高能见度"""
    
    def _generate_rainy_weather(self, days) -> pd.DataFrame:
        """雨天: 高降水概率, 低能见度"""
    
    def _generate_frost_weather(self, days) -> pd.DataFrame:
        """雾凇天: 低温, 低风速, 高湿度"""
```

## 实现要点

### Open-Meteo API 调用

```
GET https://api.open-meteo.com/v1/forecast
  ?latitude=29.75
  &longitude=102.35
  &hourly=temperature_2m,cloud_cover,cloud_cover_low,...
  &forecast_days=7
  &timezone=Asia/Shanghai
```

> **注意**: Open-Meteo 没有 `cloud_base_altitude` 字段。需要根据低云量和站点海拔进行估算，或使用 `cloud_cover_low` 结合海拔数据间接推断云底高度。这是一个设计时的假设，实现时需确认 API 实际返回字段并做适配。

### 坐标精度

所有缓存操作使用 `ROUND(lat, 2)` 和 `ROUND(lon, 2)` 作为 key，确保约 1km 精度内的坐标共享同一条缓存。

### 降级策略

API 超时时：
1. 先查 SQLite（忽略 TTL）获取过期数据
2. 有过期数据 → 返回 + 标记 `Degraded`
3. 无任何数据 → 抛出 `ServiceUnavailableError`

### 超时配置

```python
TIMEOUT_CONFIG = {
    "connect_timeout": 5,
    "read_timeout": 15,
    "retries": 2,
    "retry_delay": 1,
}
```

## 测试计划

### 测试操作步骤

```bash
source venv/bin/activate
pip install httpx pandas pytest
python -m pytest tests/unit/test_cache.py tests/integration/test_cache_sqlite.py -v
```

### 具体测试用例

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `test_cache.py` | `test_memory_cache_hit` | 写入后立即读取命中 |
| `test_cache.py` | `test_memory_cache_ttl_expire` | TTL 过期后返回 None |
| `test_cache.py` | `test_memory_cache_key_format` | key 格式为 "lat_lon_date" |
| `test_cache.py` | `test_weather_cache_fallback` | 内存 Miss → SQLite 查询 |
| `test_cache.py` | `test_weather_cache_dual_write` | set 后内存和 SQLite 都有数据 |
| `test_cache.py` | `test_mock_fetcher_clear` | Mock 晴天数据格式正确 |
| `test_cache.py` | `test_mock_fetcher_rain` | Mock 雨天降水概率 > 50% |
| `test_cache.py` | `test_mock_fetcher_call_log` | 调用记录正确 |
| `test_cache_sqlite.py` | `test_init_db_creates_tables` | 建表后表存在 |
| `test_cache_sqlite.py` | `test_upsert_and_query` | 插入后可查询 |
| `test_cache_sqlite.py` | `test_upsert_duplicate` | 重复插入更新 (REPLACE) |
| `test_cache_sqlite.py` | `test_coord_rounding_cache` | 相近坐标命中同一条缓存 |
| `test_cache_sqlite.py` | `test_save_and_load_prediction` | 预测历史保存和查询 |

## 验收标准

- [ ] SQLite 表结构与设计文档 §2.2 一致
- [ ] 内存缓存 TTL 过期机制正常工作
- [ ] 多级缓存查询链路正确（Memory → SQLite → fetch）
- [ ] MockFetcher 可生成 "clear"/"rain"/"frost"/"timeout" 四种场景
- [ ] 坐标取整缓存 key 正确
- [ ] 所有测试通过
