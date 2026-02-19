# MG5A: 前端 — TrendChart + HourlyWeatherTable 新组件

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现日期选择功能的趋势柱状图组件和可折叠逐时天气表组件，为 MG5B 的详情页重构提供构建块。

**依赖模块:** M21 (WeekTrend), MG3A (timeline weather 数据)

---

## 背景

设计文档 [§11.5](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/11-frontend-architecture-v2.md) 要求详情页将七日趋势图提升为主要日期选择器，替代 DatePicker。同时新增逐时天气表展示 MG3A 产出的温度/云量/天气图标数据。

### 与现有 WeekTrend 的关系

现有 [WeekTrend.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/forecast/WeekTrend.vue) 是折线图（使用 ECharts），不支持日期选择交互。TrendChart 是柱状图 + 点击选日期 + 图标行，属于新组件。

---

## Task 1: TrendChart 组件

**Files:**
- Create: `frontend/src/components/forecast/TrendChart.vue`
- Test: `frontend/src/__tests__/components/TrendChart.test.js`

### Props

| Prop | Type | Required | 说明 |
|------|------|----------|------|
| `daily` | Array | ✅ | forecast.json 的 daily 数组 |
| `selectedDate` | String | — | 当前选中日期 |
| `chartHeight` | Number | — | 图表高度 (默认 180px) |

### Emits

| Event | Payload | 说明 |
|-------|---------|------|
| `select` | dateString | 点击柱体/图标时触发 |

### 布局

```
┌────────────────────────────────────┐
│  ┃  ┃     ┃┃    ┃     ┃     ┃     │  ← ECharts 柱状图
│  ┃  ┃     ┃┃    ┃     ┃     ┃     │     选中柱体不透明，其余半透明
│ 30  39    50 90  55    30     5    │  ← 柱顶分数标签
│──────────────────────────────────  │
│  ☀️ ☀️   🏔️ 🏔️  ☀️   ☀️    ☀️   │  ← 图标行 (EventIcon/emoji)
│ 2/19 20   21  22  23   24    25   │  ← 日期标签 (ECharts X 轴)
└────────────────────────────────────┘
               ▲
           选中日 (高亮)
```

### 实现要点

- 使用 ECharts BarChart（柱状图）
- 柱体颜色使用 [useScoreColor](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/composables/useScoreColor.js)
- 选中日柱体不透明，其余柱体 50% 透明度
- ECharts `click` 事件触发日期选择
- 图标行在 ECharts 下方，手动渲染，使用 [EventIcon.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/event/EventIcon.vue)

### 应测试的内容

- 渲染 `.trend-chart` 容器
- 渲染 `.trend-icons` 图标行
- 选中日期的图标 cell 有 `.selected` class
- ECharts mock 正常初始化

---

## Task 2: HourlyWeatherTable 组件

**Files:**
- Create: `frontend/src/components/forecast/HourlyWeatherTable.vue`
- Test: `frontend/src/__tests__/components/HourlyWeatherTable.test.js`

### Props

| Prop | Type | Required | 说明 |
|------|------|----------|------|
| `hourly` | Array | ✅ | timeline.json 的 hourly 数组 |

### 布局

可折叠天气表，默认收起：

```
┌────────────────────────────────────┐
│  逐时天气                       ▸  │  ← collapse-header (点击展开)
├────────────────────────────────────┤
│  06:00   ☀️   -3.2°C   云10%      │  ← weather-row
│  07:00   ☀️   -1.0°C   云15%      │
│  08:00   ⛅    2.5°C   云30%      │
│  ...                               │
└────────────────────────────────────┘
```

### weather_icon → emoji 映射

```javascript
const WEATHER_EMOJI = {
  clear: '☀️',
  partly_cloudy: '⛅',
  cloudy: '☁️',
  rain: '🌧️',
  snow: '❄️',
}
```

### 应测试的内容

- 默认折叠（`.weather-rows` 不存在）
- 点击 `.collapse-header` 后展开
- 展开后正确渲染行数（过滤掉空 weather 的小时）
- 显示温度值
- 显示云量百分比
- weather_icon 映射为正确的 emoji

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend

# 单元测试
npx vitest run src/__tests__/components/TrendChart.test.js --reporter verbose
npx vitest run src/__tests__/components/HourlyWeatherTable.test.js --reporter verbose

# 全量回归
npx vitest run --reporter verbose
```

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: 设计文档 §11.5, M21, MG3A*
