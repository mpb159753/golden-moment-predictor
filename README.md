<p align="center">
  <h1 align="center">🏔️ GMP — Golden Moment Predictor</h1>
  <p align="center"><strong>川西旅行景观预测引擎</strong></p>
  <p align="center">
    <em>预测日照金山 · 云海 · 雾凇 · 观星 · 树挂 · 冰挂的最佳观赏时机</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-blue" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.128-green" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-Apache%202.0-orange" alt="License">
  <img src="https://img.shields.io/badge/tests-350%20passed-brightgreen" alt="Tests">
</p>

---

## ✨ 项目简介

GMP 是一款面向川西高海拔景区的 **7 天景观概率预测引擎**。基于 Open-Meteo 气象 API + 天文计算 + 地理数据，通过 Plugin 架构的评分系统，为旅行者预测以下 7 种自然景观的出现概率与最佳观赏时段：

| 景观 | 说明 | 数据需求 |
|------|------|---------|
| 🌅 日照金山 | 日出/日落时阳光照射雪山 | L2 光路 + 天文 |
| ☁️ 云海 | 低云层形成云海奇观 | 仅 L1 本地 |
| ❄️ 雾凇 | 低温高湿凝结成雾凇 | 仅 L1 本地 |
| 🌌 观星 | 暗天空品质观星窗口 | 天文 (月相) |
| 🌲 树挂积雪 | 降雪后的树挂景观 | 仅 L1 本地 |
| 🧊 冰挂 | 降水冻结形成冰挂 | 仅 L1 本地 |

### 核心特性

- **Plugin 架构** — 评分插件可独立扩展，新增景观只需实现一个 Plugin
- **两级滤网** — L1 本地安全检查 + L2 远程精细分析，按需加载节省 API 调用
- **双模式交互** — REST API 服务 + CLI 命令行工具
- **智能缓存** — 内存 + SQLite 两级缓存，坐标去重，降低 API 开销
- **结构化输出** — Forecast 推荐事件 / Timeline 逐小时时间轴 / CLI 彩色报告

---

## 📐 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    用户接口层                         │
│         FastAPI REST API  /  CLI 命令行               │
├─────────────────────────────────────────────────────┤
│                   输出层 Reporter                     │
│     ForecastReporter │ TimelineReporter │ CLI        │
├─────────────────────────────────────────────────────┤
│                  调度引擎 Scheduler                   │
│    Plugin 收集 → 数据准备 → 滤网分析 → 评分 → 聚合   │
├──────────────┬──────────────┬────────────────────────┤
│   分析层      │   评分层      │   数据层              │
│  L1 本地滤网  │  7 个 Plugin  │  Open-Meteo Fetcher   │
│  L2 远程滤网  │  ScoreEngine  │  SQLite + 内存缓存    │
├──────────────┴──────────────┴────────────────────────┤
│                    基础设施层                         │
│    模型定义 │ 异常层级 │ 配置加载 │ 天文/地理计算      │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 环境要求

- Python ≥ 3.10
- pip

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/golden-moment-predictor.git
cd golden-moment-predictor
```

### 2. 创建虚拟环境并安装依赖

```bash
python3 -m venv venv
source venv/bin/activate       # macOS / Linux
# venv\Scripts\activate        # Windows

pip install -r requirements.txt
```

### 3. 运行测试

```bash
python -m pytest tests/ -v
```

---

## 🖥️ 使用方式

### CLI 模式 — 命令行预测

```bash
# 基本预测 (7 天, 所有景观)
python -m gmp.main predict niubei_gongga

# 指定天数 + 事件过滤
python -m gmp.main predict niubei_gongga --days 3 --events cloud_sea,frost

# JSON 输出
python -m gmp.main predict niubei_gongga --json

# 无颜色模式 (管道/日志场景)
python -m gmp.main predict niubei_gongga --no-color
```

**CLI 输出示例:**

```
╔══════════════════════════════════════╗
║     🏔️ 牛背山 · 7日景观预测             ║
╚══════════════════════════════════════╝

📅 2026-02-12 (High)
──────────────────────────────
☁️ 云海    ⭐ 85/100  ✅ Recommended
      gap: 50/50  density: 20/30  wind: 15/20
❄️ 雾凇    ⭐ 70/100  ⚠️ Possible
      temperature: 30/40  moisture: 20/30
```

### API 模式 — REST 服务

```bash
# 启动 API 服务
python -m gmp.main serve --host 0.0.0.0 --port 8000
```

#### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/viewpoints` | 观景台列表 (支持分页) |
| `GET` | `/api/v1/forecast/{viewpoint_id}` | 景观预测报告 |
| `GET` | `/api/v1/timeline/{viewpoint_id}` | 逐小时时间轴 |

#### 请求示例

```bash
# 查看观景台列表
curl http://localhost:8000/api/v1/viewpoints

# 获取 3 天预测报告，仅看云海和雾凇
curl "http://localhost:8000/api/v1/forecast/niubei_gongga?days=3&events=cloud_sea,frost"

# 获取逐小时时间轴
curl http://localhost:8000/api/v1/timeline/niubei_gongga?days=7
```

#### 错误响应

所有错误返回统一 JSON 格式:

```json
{
  "error": {
    "type": "ViewpointNotFound",
    "message": "未找到观景台: invalid_id",
    "code": 404
  }
}
```

| HTTP 状态码 | 类型 | 说明 |
|------------|------|------|
| 404 | ViewpointNotFound | 观景台不存在 |
| 408 | APITimeout | 气象 API 超时 |
| 422 | InvalidParameter | 参数不合法 |
| 503 | ServiceDegraded | 服务降级 (使用过期缓存) |

---

## 📁 项目结构

```
golden-moment-predictor/
├── gmp/                        # 主包
│   ├── api/                    # REST API 层
│   │   ├── routes.py           #   FastAPI 路由 + 应用工厂
│   │   ├── schemas.py          #   Pydantic 请求/响应模型
│   │   └── middleware.py       #   异常处理中间件
│   ├── core/                   # 核心层
│   │   ├── models.py           #   数据模型 (Viewpoint, DataContext, ...)
│   │   ├── exceptions.py       #   异常层级
│   │   ├── config_loader.py    #   引擎 + 观景台配置加载
│   │   ├── scheduler.py        #   主调度引擎 GMPScheduler
│   │   └── pipeline.py         #   L1→L2 分析管线
│   ├── scorer/                 # 评分插件层
│   │   ├── engine.py           #   ScoreEngine 注册中心
│   │   ├── plugin.py           #   评分辅助工具
│   │   ├── golden_mountain.py  #   日照金山插件
│   │   ├── stargazing.py       #   观星插件
│   │   ├── cloud_sea.py        #   云海插件
│   │   ├── frost.py            #   雾凇插件
│   │   ├── snow_tree.py        #   树挂积雪插件
│   │   └── ice_icicle.py       #   冰挂插件
│   ├── analyzer/               # 分析层 (L1/L2 滤网)
│   ├── reporter/               # 输出层
│   │   ├── forecast_reporter.py
│   │   ├── timeline_reporter.py
│   │   └── cli_formatter.py
│   ├── fetcher/                # 数据获取层
│   ├── cache/                  # 缓存层
│   ├── astro/                  # 天文/地理计算
│   ├── config/                 # 配置文件
│   │   ├── engine_config.yaml
│   │   └── viewpoints/         #   观景台 YAML 配置
│   └── main.py                 # 应用入口 (CLI + API)
├── tests/                      # 测试
│   ├── unit/                   #   单元测试 (16 个文件)
│   ├── integration/            #   集成测试
│   └── e2e/                    #   端到端测试
├── design/                     # 设计文档
├── implementation-plans/       # 实施计划书
├── pyproject.toml
├── requirements.txt
└── LICENSE                     # Apache 2.0
```

---

## ⚙️ 配置

### 引擎配置 (`gmp/config/engine_config.yaml`)

控制缓存 TTL、安全阈值、评分权重、分页等全局参数:

```yaml
cache:
  memory_ttl_seconds: 300
  db_ttl_seconds: 3600

thresholds:
  precip_probability: 50     # 降水概率安全线
  wind_speed_max: 20         # 最大风速阈值 (km/h)
  frost_temperature: 2.0     # 雾凇温度阈值 (°C)
```

### 观景台配置 (`gmp/config/viewpoints/*.yaml`)

每个观景台一个 YAML 文件，定义位置、能力和观测目标:

```yaml
id: niubei_gongga
name: 牛背山
location:
  lat: 29.75
  lon: 102.35
  altitude: 3660

capabilities:          # 支持的景观类型
  - sunrise
  - sunset
  - stargazing
  - cloud_sea
  - frost

targets:               # 可观测目标
  - name: 贡嘎主峰
    lat: 29.58
    lon: 101.88
    altitude: 7556
    weight: primary
```

新增观景台只需在 `viewpoints/` 目录添加 YAML 文件，无需改动代码。

---

## 🧪 测试

项目包含 **350 个测试用例**，覆盖三个层级:

```bash
# 运行全部测试
python -m pytest tests/ -v

# 仅运行单元测试
python -m pytest tests/unit/ -v

# 仅运行集成测试 (API 端点)
python -m pytest tests/integration/ -v

# 仅运行 E2E 测试
python -m pytest tests/e2e/ -v
```

| 层级 | 数量 | 覆盖内容 |
|------|------|---------|
| 单元测试 | 261 | 模型/配置/天文/地理/分析/评分/输出 |
| 集成测试 | 13 | API 端点/分页/错误处理/管线 |
| E2E | 8 | 7 天预测全链路/CLI/一致性 |

---

## 🔌 扩展新景观

GMP 采用 Plugin 架构，扩展新景观只需 3 步:

**1. 创建 Plugin 文件** (`gmp/scorer/my_plugin.py`)

```python
from gmp.core.models import DataContext, DataRequirement, ScoreResult
from gmp.scorer.plugin import score_to_status

class MyPlugin:
    event_type = "my_event"
    display_name = "我的景观"
    data_requirement = DataRequirement()  # 按需声明

    def check_trigger(self, l1_data: dict) -> bool:
        return True  # 触发条件

    def score(self, context: DataContext) -> ScoreResult:
        total = 80  # 评分逻辑
        return ScoreResult(
            total_score=total,
            status=score_to_status(total),
            breakdown={"dim": {"score": 80, "max": 100}},
        )
```

**2. 注册 Plugin** — 在 `routes.py` 的 `_create_score_engine()` 和 `main.py` 中添加注册

**3. 配置观景台** — 在 YAML 的 `capabilities` 中添加 `my_event`

---

## 📜 许可证

[Apache License 2.0](LICENSE)
