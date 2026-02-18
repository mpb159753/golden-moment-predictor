# 川西旅行景观预测引擎 — 实施计划总览

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 从零实现 GMP 引擎，涵盖天文/地理计算、气象数据获取与缓存、6 个评分 Plugin、CLI/JSON 输出、历史回测全链路。

**Architecture:** Plugin 驱动的预计算引擎，Scheduler 聚合 Plugin 数据需求后统一获取，通过 DataContext 共享给各 Plugin 独立评分，BatchGenerator 负责批量编排和文件输出，输出 JSON 文件供前端读取。

**Tech Stack:** Python 3.11+, click, structlog, pandas, ephem, httpx, pyyaml, SQLite

---

## 模块总览

| 编号 | 模块 | 文件 | 描述 | 依赖 |
|------|------|------|------|------|
| M01 | [项目初始化](./M01-project-init.md) | pyproject.toml, venv, 目录骨架 | 创建项目结构、安装依赖 | — |
| M02 | [数据模型与异常](./M02-data-models-exceptions.md) | `gmp/core/models.py`, `gmp/core/exceptions.py` | 所有 dataclass + 异常类 | M01 |
| M03 | [GeoUtils 地理计算](./M03-geo-utils.md) | `gmp/data/geo_utils.py` | 方位角、距离、光路点计算 | M01 |
| M04 | [AstroUtils 天文计算](./M04-astro-utils.md) | `gmp/data/astro_utils.py` | 日出日落、月相、观星窗口 | M02, M03 |
| M05 | [SQLite 缓存层](./M05-cache-layer.md) | `gmp/cache/repository.py`, `gmp/cache/weather_cache.py` | DB 操作 + 缓存管理 | M02 |
| M06 | [MeteoFetcher 数据获取](./M06-meteo-fetcher.md) | `gmp/data/meteo_fetcher.py` | Open-Meteo API 调用 + 解析 | M02, M05 |
| M07 | [配置管理](./M07-config-manager.md) | `gmp/core/config_loader.py` | ConfigManager + ViewpointConfig + RouteConfig | M02 |
| M08 | [评分引擎核心](./M08-scoring-engine.md) | `gmp/scoring/engine.py`, `gmp/scoring/models.py` | ScoreEngine + DataContext + Plugin 接口 | M02, M07 |
| M09A | [CloudSea 云海](./M09A-plugin-cloud-sea.md) | `gmp/scoring/plugins/cloud_sea.py` | 云海评分 Plugin | M08 |
| M09B | [Frost 雾凇](./M09B-plugin-frost.md) | `gmp/scoring/plugins/frost.py` | 雾凇评分 Plugin | M08 |
| M09C | [SnowTree 树挂积雪](./M09C-plugin-snow-tree.md) | `gmp/scoring/plugins/snow_tree.py` | 树挂积雪评分 Plugin | M08 |
| M09D | [IceIcicle 冰挂](./M09D-plugin-ice-icicle.md) | `gmp/scoring/plugins/ice_icicle.py` | 冰挂评分 Plugin | M08 |
| M10A | [GoldenMountain 日照金山](./M10A-plugin-golden-mountain.md) | `gmp/scoring/plugins/golden_mountain.py` | 日照金山评分 Plugin (双实例) | M03, M04, M08 |
| M10B | [Stargazing 观星](./M10B-plugin-stargazing.md) | `gmp/scoring/plugins/stargazing.py` | 观星评分 Plugin | M04, M08 |
| M11A | [输出层: Reporters](./M11A-output-reporters.md) | `gmp/output/summary_generator.py`, `forecast_reporter.py` | SummaryGenerator + ForecastReporter | M02, M08 |
| M11B | [输出层: Timeline+CLI](./M11B-output-timeline-cli.md) | `gmp/output/timeline_reporter.py`, `cli_formatter.py` | TimelineReporter + CLIFormatter | M02, M08, M11A |
| M11C | [输出层: FileWriter](./M11C-output-file-writer.md) | `gmp/output/json_file_writer.py` | JSONFileWriter (文件写入+归档) | M02, M11A, M11B |
| M12 | [调度器 GMPScheduler](./M12-scheduler.md) | `gmp/core/scheduler.py` | 核心评分管线：Plugin 收集→数据获取→评分 | M04, M06, M07, M08 |
| M12B | [批量生成器 BatchGenerator](./M12B-batch-generator.md) | `gmp/core/batch_generator.py` | 批量编排 + 文件输出 + 归档 | M11C, M12 |
| M13 | [Backtester 历史校准](./M13-backtester.md) | `gmp/backtest/backtester.py` | 使用历史数据验证评分模型 | M06, M12 |
| M14 | [CLI 入口](./M14-cli-entry.md) | `gmp/main.py` | click CLI: predict / generate-all / backtest / list-* | M07, M11C, M12, M12B, M13 |
| M15 | [E2E 验收测试](./M15-e2e-acceptance.md) | `tests/e2e/test_e2e_real_api.py` | 真实 API 端到端验收（无 Mock） | M14 |
| M16 | [前端项目初始化](./M16-frontend-project-init.md) | `frontend/` 项目骨架 | Vite + Vue 3 创建、UnoCSS、样式系统、Router、AMap | — |
| M17 | [前端数据层](./M17-frontend-data-layer.md) | `stores/`, `composables/useDataLoader.js` | useDataLoader + Pinia Stores (viewpoints/routes/app) | M16 |
| M18 | [前端 Composables](./M18-frontend-composables.md) | `composables/` | useScoreColor, useComboTags, useAMap, useScreenshot | M16, M17 |
| M19 | [评分可视化组件](./M19-frontend-score-components.md) | `components/score/` | ScoreRing, ScoreBar, StatusBadge | M16, M18 |
| M20 | [事件展示组件](./M20-frontend-event-components.md) | `components/event/`, `assets/icons/` | EventIcon + SVG 图标集, EventCard, EventList | M16, M18, M19 |
| M21 | [预测展示组件](./M21-frontend-forecast-components.md) | `components/forecast/` | DaySummary, WeekTrend (ECharts), HourlyTimeline, BreakdownTable | M16, M18-M20 |
| M22 | [地图组件](./M22-frontend-map-components.md) | `components/map/` | AMapContainer, ViewpointMarker, RouteLine | M16, M18 |
| M23 | [布局通用组件](./M23-frontend-layout-components.md) | `components/layout/` | DatePicker, FilterBar, UpdateBanner | M16, M17 |
| M24 | [导出组件](./M24-frontend-export-components.md) | `components/export/` | ScreenshotBtn, ShareCard (小红书 1080×1440) | M16, M18 |
| M25 | [共享详情页](./M25-frontend-detail-pages.md) | `views/` | ViewpointDetail, RouteDetail (三方案共用) | M17, M19-M24 |
| MA1 | [A方案 首页布局](./MA1-frontend-immersive-map-layout.md) | `views/HomeView.vue`, `components/scheme-a/MapTopBar.vue` | 全屏地图 + 毛玻璃搜索栏 + Marker 三状态 | M16-M22 |
| MA2 | [A方案 BottomSheet](./MA2-frontend-bottom-sheet.md) | `components/scheme-a/BottomSheet.vue` | 三级高度面板，手势拖拽，GSAP 弹性动画 | M16, GSAP |
| MA3 | [A方案 推荐+线路+截图](./MA3-frontend-recommend-route-screenshot.md) | `components/scheme-a/BestRecommendList.vue`, `RoutePanel.vue` | 今日最佳推荐、线路模式面板、截图场景 | MA1, MA2, M19-M22 |
| MA4 | [A方案 动画与优化](./MA4-frontend-animation-optimization.md) | `components/map/`, `views/HomeView.vue` | Marker 入场/脉冲动画、评分 CountUp、懒加载策略 | MA1, MA2, GSAP |
| MB1 | [B方案 分屏首页布局](./MB1-frontend-split-container-layout.md) | `components/scheme-b/SplitContainer.vue`, `DragBar.vue`, `ListTopBar.vue`, `MapPanel.vue` | 分割容器 + 拖拽条 + 搜索/筛选/排序栏 + 首页组装 | M16-M22 |
| MB2 | [B方案 手风琴卡片](./MB2-frontend-accordion-card-sync.md) | `components/scheme-b/ViewpointListItem.vue`, `composables/useListMapSync.js` | 可展开卡片 + Intersection Observer 列表↔地图联动 | MB1, M19-M21 |
| MB3 | [B方案 线路+截图+动画](./MB3-frontend-route-screenshot-animation.md) | `components/scheme-b/RouteListItem.vue`, `RankingScreenshot.vue` | 线路卡片、排行榜截图、入场/FLIP/CountUp 动画 | MB1, MB2, M24, GSAP |
| MC1 | [C方案 卡片流首页布局](./MC1-frontend-card-flow-layout.md) | `views/HomeView.vue`, `components/scheme-c/CardTopBar.vue`, `BackgroundMap.vue` | 暗色模糊地图 + 日期标签栏 + 三层首页结构 | M16-M22 |
| MC2 | [C方案 核心卡片](./MC2-frontend-card-swiper.md) | `components/scheme-c/CardSwiper.vue`, `PredictionCard.vue` | Swiper 卡片容器、可翻转预测卡片 (正面概览+背面详情) | MC1, M19-M21 |
| MC3 | [C方案 全屏地图+截图](./MC3-frontend-fullscreen-map-screenshot.md) | `components/scheme-c/FullscreenMap.vue`, `CompareGrid.vue` | 全屏地图模态、预测卡片截图、对比组图 | MC1, MC2, M22, M24 |
| MC4 | [C方案 动画与优化](./MC4-frontend-animation-optimization.md) | `components/scheme-c/` | 卡片入场/粒子/发光动画、顶栏颜色过渡、懒加载策略 | MC1, MC2, GSAP |

## 模块依赖图

```mermaid
graph TD
    M01[M01 项目初始化] --> M02[M02 数据模型]
    M01 --> M03[M03 GeoUtils]
    M02 --> M04[M04 AstroUtils]
    M03 --> M04
    M02 --> M05[M05 缓存层]
    M02 --> M06[M06 MeteoFetcher]
    M05 --> M06
    M02 --> M07[M07 配置管理]
    M02 --> M08[M08 评分引擎核心]
    M07 --> M08
    M08 --> M09A[M09A CloudSea]
    M08 --> M09B[M09B Frost]
    M08 --> M09C[M09C SnowTree]
    M08 --> M09D[M09D IceIcicle]
    M03 --> M10A[M10A GoldenMountain]
    M04 --> M10A
    M08 --> M10A
    M04 --> M10B[M10B Stargazing]
    M08 --> M10B
    M02 --> M11A[M11A Reporters]
    M08 --> M11A
    M11A --> M11B[M11B Timeline+CLI]
    M02 --> M11B
    M08 --> M11B
    M11A --> M11C[M11C FileWriter]
    M11B --> M11C
    M02 --> M11C
    M04 --> M12[M12 调度器]
    M06 --> M12
    M07 --> M12
    M08 --> M12
    M11C --> M12B[M12B 批量生成器]
    M12 --> M12B
    M06 --> M13[M13 Backtester]
    M12 --> M13
    M07 --> M14[M14 CLI]
    M11C --> M14
    M12 --> M14
    M12B --> M14
    M13 --> M14
    M14 --> M15[M15 E2E 验收]

    style M01 fill:#e8f5e9
    style M02 fill:#e8f5e9
    style M03 fill:#e8f5e9
    style M09A fill:#fce4ec
    style M09B fill:#fce4ec
    style M09C fill:#fce4ec
    style M09D fill:#fce4ec
    style M10A fill:#fce4ec
    style M10B fill:#fce4ec
    style M11A fill:#e1f5fe
    style M11B fill:#e1f5fe
    style M11C fill:#e1f5fe
    style M12 fill:#e3f2fd
    style M12B fill:#e3f2fd
    style M14 fill:#fff3e0
    style M15 fill:#fff8e1
```

## 推荐执行顺序

> **并行友好**: M03 和 M05 可以并行；M09A-D 四个 Plugin 可全部并行；M10A/M10B 可与 M09 并行；M11A 可与 M09/M10 并行。

1. **基础层** (顺序): M01 → M02
2. **工具层** (可并行): M03 | M05 | M07
3. **数据层**: M04 → M06
4. **核心层**: M08
5. **插件层** (可全部并行): M09A | M09B | M09C | M09D | M10A | M10B | M11A
6. **输出层** (串行): M11A → M11B → M11C
7. **集成层** (顺序): M12 → M12B | M13 → M14
8. **验收层**: M15

## 全局约定

### TDD 流程
每个模块遵循 Red-Green-Refactor:
1. 写失败测试
2. 运行确认失败
3. 写最小实现通过测试
4. 运行确认通过
5. 重构（保持绿色）
6. 提交

### 配置驱动
- **所有评分阈值/权重来自 `engine_config.yaml`**，代码中零魔法数字
- Plugin 构造函数接受配置 dict
- 测试中通过 fixture 提供测试配置

### 提交规范
```
feat(module): 简短描述
test(module): 添加测试
refactor(module): 重构改进
```

### 测试命令
```bash
# 单模块测试
python -m pytest tests/unit/test_geo_utils.py -v

# 全量测试 (不含 E2E)
python -m pytest tests/ -v -m "not e2e"

# E2E 测试 (需网络)
python -m pytest tests/e2e/ -v -m e2e

# 带覆盖率
python -m pytest tests/ --cov=gmp --cov-report=term-missing -m "not e2e"
```

---

*文档版本: v1.1 | 更新: 2026-02-13 | 基于设计文档 v4.0*
