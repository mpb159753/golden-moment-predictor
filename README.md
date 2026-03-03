# 🏔️ GMP — 川西旅行景观预测引擎

> **"让每一次川西之行，都不错过自然的馈赠。"**

GMP (Golden Moment Predictor) 是一个基于气象数据的川西旅行景观预测引擎，能够预测**日照金山、云海、观星、雾凇、树挂积雪、冰挂**等自然景观的出现概率，帮助旅行者选择最佳出行时机。

## ✨ 核心功能

- 🌄 **日照金山预测** — 基于日出/日落方位角、光路云量、目标峰可见度三重评分
- ☁️ **云海预测** — 结合云底高度、观景台海拔、逆温层分析
- ⭐ **观星预测** — 月相、夜间云量、风速综合评估
- ❄️ **冬季景观** — 雾凇 / 树挂积雪 / 冰挂的温度-湿度-风速模型
- 📊 **历史回测** — 使用 Archive API 获取历史天气数据验证模型准确性
- 🗺️ **线路规划** — 多站点线路的联合预测

## 🏗️ 技术架构

```
Plugin 驱动的预计算引擎
Scheduler 聚合 Plugin 数据需求 → 统一获取气象数据
→ DataContext 共享给各 Plugin 独立评分
→ 输出层 (JSON / CLI Table / 文件)
```

**后端技术栈:** Python 3.11+, Click, structlog, pandas, ephem, httpx, PyYAML, SQLite

**前端技术栈:** Vue 3 + Vite, Pinia, Vue Router, 高德地图 JS API, GSAP, ECharts, html2canvas

## 🚀 快速开始

### 后端安装

```bash
git clone https://github.com/your-username/golden-moment-predictor.git
cd golden-moment-predictor

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements-dev.txt

# 安装项目 (可选，使 gmp 命令可用)
pip install -e .
```

### 前端安装与启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (默认 http://localhost:5173)
npm run dev

# 运行测试
npm test

# 生产构建
npm run build

# 预览生产构建
npm run preview
```

> [!NOTE]
> 前端使用高德地图 JS API，需要在 `frontend/.env.development` 中配置 API Key：
> ```
> VITE_AMAP_KEY=你的高德地图Key
> VITE_AMAP_SECURITY_CODE=你的安全密钥
> ```
> 可在 [高德开放平台](https://lbs.amap.com/) 申请。

### 全栈开发流程

```bash
# 1. 生成预测数据（后端 → public/data）
source venv/bin/activate
python -m gmp.main generate-all --days 7

# 2. 启动前端开发服务器（读取 public/data 中的 JSON）
cd frontend && npm run dev
```

### 基本用法

```bash
# 查看帮助
python -m gmp.main --help

# 查看所有可用观景台
python -m gmp.main list-viewpoints

# 预测牛背山未来 3 天的景观
python -m gmp.main predict niubei --days 3

# JSON 格式输出
python -m gmp.main predict niubei --days 3 --output json

# 仅预测特定事件 (如云海和雾凇)
python -m gmp.main predict niubei --days 3 --events cloud_sea,frost --output json

# 线路预测 (理小路: 折多山 → 牛背山)
python -m gmp.main predict-route lixiao --days 1 --output json

# 历史回测
python -m gmp.main backtest niubei --date 2026-02-10
```

## 📖 命令详解

### `predict` — 单站预测

对指定观景台生成景观预测。

```bash
python -m gmp.main predict <VIEWPOINT_ID> [OPTIONS]
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--days` | 预测天数 (1-16) | 1 |
| `--events` | 逗号分隔的事件过滤 | 全部 |
| `--output` | 输出格式 (`json` / `table`) | `table` |
| `--detail` | 显示评分明细 | 否 |
| `--output-file` | 输出 JSON 到文件 | — |
| `--config` | 配置文件路径 | `config/engine_config.yaml` |

**Table 输出示例:**

```
📍 牛背山 (niubei)
============================================================

📅 2026-02-17  不推荐 — 条件不佳
------------------------------------------------------------
事件                           分数  状态
------------------------------------------------------------
观星                           48  Not Recommended
日出金山                          0  Not Recommended
日落金山                          0  Not Recommended

📅 2026-02-18  可能可见 — 雾凇
------------------------------------------------------------
事件                           分数  状态
------------------------------------------------------------
雾凇                           58  Possible
```

**JSON 输出示例:**

```json
{
  "viewpoint_id": "niubei",
  "viewpoint_name": "牛背山",
  "generated_at": "2026-02-17T00:47:00+08:00",
  "forecast_days": 3,
  "daily": [
    {
      "date": "2026-02-17",
      "summary": "不推荐 — 条件不佳",
      "best_event": {
        "event_type": "stargazing",
        "score": 48,
        "status": "Not Recommended"
      },
      "events": [
        {
          "event_type": "stargazing",
          "display_name": "观星",
          "time_window": "20:20 - 06:28",
          "score": 48,
          "status": "Not Recommended",
          "confidence": "High",
          "tags": ["stargazing"],
          "conditions": [],
          "score_breakdown": {
            "base": { "score": 100, "max": 100, "detail": "quality=optimal" },
            "cloud": { "score": -51, "max": 0, "detail": "avg_cloud=64.4%" },
            "wind": { "score": 0, "max": 0, "detail": "wind deduction" }
          }
        }
      ]
    }
  ]
}
```

### `predict-route` — 线路预测

对指定线路预测沿途各站景观。

```bash
python -m gmp.main predict-route <ROUTE_ID> [OPTIONS]
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--days` | 预测天数 (1-16) | 1 |
| `--events` | 逗号分隔的事件过滤 | 全部 |
| `--output` | 输出格式 (`json` / `table`) | `table` |
| `--config` | 配置文件路径 | `config/engine_config.yaml` |

### `generate-all` — 批量生成

批量生成所有观景台和线路的预测 JSON 文件，用于前端静态部署。

```bash
python -m gmp.main generate-all [OPTIONS]
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--days` | 预测天数 (1-16) | 1 |
| `--events` | 逗号分隔的事件过滤 | 全部 |
| `--fail-fast` | 单站失败时立即中止 | 否 |
| `--no-archive` | 跳过历史归档 | 否 |
| `--output` | JSON 输出目录 | `public/data` |
| `--archive` | 历史归档目录 | `archive` |
| `--config` | 配置文件路径 | `config/engine_config.yaml` |

生成的文件结构:

```
public/data/
├── index.json              # 观景台和线路索引
├── meta.json               # 生成元数据
├── viewpoints/
│   ├── niubei/
│   │   ├── forecast.json
│   │   └── timeline_2026-02-17.json
│   └── zheduo/
│       ├── forecast.json
│       └── timeline_2026-02-17.json
└── routes/
    └── lixiao/
        └── forecast.json
```

### `backtest` — 历史回测

使用 Archive API 获取历史天气数据，验证评分模型在过去某天的预测结果。

```bash
python -m gmp.main backtest <VIEWPOINT_ID> --date <YYYY-MM-DD> [OPTIONS]
```

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--date` | 目标日期 (YYYY-MM-DD) | **必填** |
| `--events` | 逗号分隔的事件过滤 | 全部 |
| `--save` | 保存回测结果到数据库 | 否 |
| `--config` | 配置文件路径 | `config/engine_config.yaml` |

**输出示例:**

```json
{
  "viewpoint_id": "niubei",
  "target_date": "2026-02-10",
  "is_backtest": true,
  "data_source": "archive",
  "events": [
    {
      "event_type": "sunrise_golden_mountain",
      "total_score": 0,
      "status": "Not Recommended",
      "breakdown": {
        "light_path": { "score": 35, "max": 35, "detail": "cloud=0%" },
        "target_visible": { "score": 10, "max": 40, "detail": "cloud=44%" },
        "local_clear": { "score": 0, "max": 25, "detail": "cloud=71%" }
      },
      "confidence": "Low"
    }
  ],
  "meta": {
    "backtest_run_at": "2026-02-17T00:47:23+08:00"
  }
}
```

### `list-viewpoints` — 列出观景台

```bash
# Table 格式 (默认)
python -m gmp.main list-viewpoints

# JSON 格式
python -m gmp.main list-viewpoints --output json
```

**Table 输出:**

```
ID                        名称              海拔(m)      景观类型
----------------------------------------------------------------------
niubei             牛背山             3660       sunrise, sunset, stargazing, cloud_sea, frost, snow_tree, ice_icicle
zheduo             折多山             4298       sunrise, sunset, stargazing, cloud_sea, frost, snow_tree, ice_icicle
```

### `list-routes` — 列出线路

```bash
# Table 格式 (默认)
python -m gmp.main list-routes

# JSON 格式
python -m gmp.main list-routes --output json
```

**Table 输出:**

```
ID                   名称              站数       站点
----------------------------------------------------------------------
lixiao               理小路             2        zheduo → niubei
```

## 🔌 评分 Plugin 系统

GMP 使用可插拔的评分 Plugin 架构，每个景观类型对应一个独立的 Plugin:

| Plugin | 事件类型 | 说明 | 季节限制 |
|--------|----------|------|----------|
| CloudSeaPlugin | `cloud_sea` | 云海评分 | 全年 |
| StargazingPlugin | `stargazing` | 观星评分 | 全年 |
| GoldenMountainPlugin | `sunrise_golden_mountain` / `sunset_golden_mountain` | 日照金山评分 (双实例) | 全年 |
| FrostPlugin | `frost` | 雾凇评分 | 冬季 |
| SnowTreePlugin | `snow_tree` | 树挂积雪评分 | 冬季 |
| IceIciclePlugin | `ice_icicle` | 冰挂评分 | 冬季 |

### 评分等级

| 分数范围 | Status | 含义 |
|----------|--------|------|
| 80-100 | Perfect | 极佳条件 |
| 60-79 | Recommended | 推荐观测 |
| 40-59 | Possible | 可能可见 |
| 0-39 | Not Recommended | 不推荐 |

## 📁 项目结构

```
golden-moment-predictor/
├── config/
│   ├── engine_config.yaml          # 引擎核心配置 (评分阈值/权重/缓存)
│   ├── viewpoints/                 # 观景台配置
│   │   ├── niubei.yaml      # 牛背山
│   │   └── zheduo.yaml      # 折多山
│   └── routes/                     # 线路配置
│       └── lixiao.yaml             # 理小路
├── gmp/
│   ├── main.py                     # CLI 入口
│   ├── core/
│   │   ├── models.py               # 数据模型 (dataclass)
│   │   ├── exceptions.py           # 异常类
│   │   ├── config_loader.py        # 配置管理
│   │   ├── scheduler.py            # 调度器 (核心评分管线)
│   │   └── batch_generator.py      # 批量生成器
│   ├── data/
│   │   ├── geo_utils.py            # 地理计算 (方位角/距离)
│   │   ├── astro_utils.py          # 天文计算 (日出日落/月相)
│   │   └── meteo_fetcher.py        # Open-Meteo API 数据获取
│   ├── cache/
│   │   ├── repository.py           # SQLite 缓存 DB 操作
│   │   └── weather_cache.py        # 缓存管理层
│   ├── scoring/
│   │   ├── engine.py               # 评分引擎核心
│   │   ├── models.py               # 评分数据模型
│   │   └── plugins/                # 评分 Plugin
│   │       ├── cloud_sea.py        # 云海
│   │       ├── frost.py            # 雾凇
│   │       ├── snow_tree.py        # 树挂积雪
│   │       ├── ice_icicle.py       # 冰挂
│   │       ├── golden_mountain.py  # 日照金山
│   │       └── stargazing.py       # 观星
│   ├── output/
│   │   ├── forecast_reporter.py    # 预测报告生成
│   │   ├── timeline_reporter.py    # 时间线报告
│   │   ├── summary_generator.py    # 摘要生成
│   │   ├── cli_formatter.py        # CLI 表格格式化
│   │   └── json_file_writer.py     # JSON 文件写入
│   └── backtest/
│       └── backtester.py           # 历史回测
├── frontend/                        # 前端 Vue 应用
│   ├── src/
│   │   ├── views/                  # 页面视图
│   │   │   ├── HomeView.vue        # 首页 (沉浸式地图)
│   │   │   ├── ViewpointDetail.vue # 观景台详情
│   │   │   └── RouteDetail.vue     # 线路详情
│   │   ├── components/             # 组件库
│   │   │   ├── map/                # 地图组件 (AMap/Marker/RouteLine)
│   │   │   ├── scheme-a/           # A方案组件 (TopBar/BottomSheet/推荐)
│   │   │   ├── score/              # 评分展示 (ScoreRing/ScoreBar)
│   │   │   ├── forecast/           # 预测展示 (DaySummary/WeekTrend)
│   │   │   ├── event/              # 事件组件 (EventIcon/EventCard)
│   │   │   ├── export/             # 导出 (ScreenshotBtn/ShareCard)
│   │   │   └── layout/             # 布局 (DatePicker/FilterBar)
│   │   ├── stores/                 # Pinia 状态管理
│   │   ├── composables/            # 组合式函数
│   │   ├── router/                 # Vue Router 配置
│   │   └── assets/                 # 静态资源与样式
│   ├── public/data/                # 预测数据 JSON (由后端生成)
│   └── package.json
├── tests/
│   ├── unit/                       # 单元测试
│   ├── integration/                # 集成测试
│   └── e2e/                        # 端到端测试 (真实 API)
├── design/                         # 系统设计文档
└── implementation_plan/            # 实施计划文档
```

## 🧪 测试

### 后端测试 (Python)

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行所有单元测试 + 集成测试 (不含 E2E)
python -m pytest tests/ -v -m "not e2e"

# 仅运行 E2E 测试 (需要网络访问 Open-Meteo API)
python -m pytest tests/e2e/ -v -m e2e

# 带覆盖率报告
python -m pytest tests/ --cov=gmp --cov-report=term-missing -m "not e2e"
```

### 前端测试 (Vitest)

```bash
cd frontend

# 运行所有测试
npm test

# 监听模式 (开发时推荐)
npx vitest
```

## ⚙️ 配置

### 添加新观景台

在 `config/viewpoints/` 目录下创建 YAML 文件:

```yaml
id: my_viewpoint
name: 我的观景台
location:
  lat: 29.75
  lon: 102.35
  altitude: 3660

capabilities:
  - sunrise
  - sunset
  - stargazing
  - cloud_sea

targets:
  - name: 目标山峰
    lat: 29.58
    lon: 101.88
    altitude: 7556
    weight: primary
    applicable_events: null   # null = 自动根据方位角匹配
```

### 添加新线路

在 `config/routes/` 目录下创建 YAML 文件:

```yaml
id: my_route
name: 我的线路
description: 线路描述
stops:
  - viewpoint_id: viewpoint_a
    order: 1
    stay_note: 建议日出前2小时到达
  - viewpoint_id: viewpoint_b
    order: 2
    stay_note: 推荐过夜
```

## 📄 许可证

[Apache License 2.0](LICENSE)
