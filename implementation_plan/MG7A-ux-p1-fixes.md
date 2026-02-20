# MG7A: 前端 — P1 用户体验问题整改

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 修复 UX 评估中发现的 5 项 P1 级别体验问题：详情页缺关闭按钮、PC 端手势文案不适配、地图标记辨识度低、筛选按钮缺标签/Tooltip、趋势图缺 Hover Tooltip。

**依赖模块:** 无（纯前端改造，不涉及后端或数据结构变更）

---

## 背景

基于真实截图的 UX 评估发现以下 P1 问题：

| # | 问题 | 影响 |
|---|------|------|
| P1-1 | 详情页（半展态/全展态）缺少关闭/返回按钮 | 新用户无法退出详情 |
| P1-2 | 半展态底部 "↑ 上拉查看完整报告" 在 PC 端不适用 | PC 用户困惑 |
| P1-3 | 地图标记仅为彩色圆点，无法传达观景台名称和事件类型 | 地图浏览效率低 |
| P1-4 | 筛选按钮（🏔️☁️⭐❄️）缺少文字标签/Tooltip | 新用户不知道按钮含义 |
| P1-5 | WeekTrend 折线图缺少 Hover Tooltip 交互 | PC 端无法查看具体数值 |

### 涉及文件

| 文件 | 修改内容 |
|------|---------|
| [HomeView.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/HomeView.vue) | 半展态/全展态添加关闭按钮；"上拉" 文案改为自适应 |
| [BottomSheet.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/scheme-a/BottomSheet.vue) | 新增关闭按钮 slot 或 emit 支持 |
| [ViewpointMarker.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/map/ViewpointMarker.vue) | 默认态增加名称标签（zoom ≥ 9 时） |
| [MapTopBar.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/scheme-a/MapTopBar.vue) | 筛选按钮增加 title + aria-label |
| [WeekTrend.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/forecast/WeekTrend.vue) | ECharts tooltip 已有 trigger:'axis'，增加 formatter |

---

## Task 1: 详情页关闭按钮 + 文案自适应

**Files:**
- Modify: [HomeView.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/HomeView.vue)
- Test: [HomeView.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/views/HomeView.test.js)

### 修改内容

#### 1.1 半展态添加关闭按钮

在 `half-content` 的 `half-title-row` 右侧（`half-best-score` 之后）添加关闭按钮：

```diff
  <div class="half-title-row">
    <span class="half-vp-name">{{ currentViewpoint.name }}</span>
-   <span class="half-best-score">
+   <div class="half-title-right">
+     <span class="half-best-score">
        <EventIcon v-if="currentDay?.best_event?.event_type" :event-type="currentDay.best_event.event_type" :size="18" />
        {{ currentDay?.best_event?.score ?? 0 }}
-   </span>
+     </span>
+     <button class="sheet-close-btn" @click.stop="onCloseSheet" aria-label="关闭">✕</button>
+   </div>
  </div>
```

#### 1.2 全展态添加关闭按钮

在 `full-header__top` 右侧（与景点名同行）添加关闭按钮：

```diff
  <div class="full-header__top">
    <h2 class="full-vp-name">{{ currentViewpoint.name }}</h2>
    <span class="full-date">{{ formatFullDate(currentDay?.date) }}</span>
+   <button class="sheet-close-btn sheet-close-btn--full" @click.stop="onCloseSheet" aria-label="关闭">✕</button>
  </div>
```

#### 1.3 新增 `onCloseSheet` 方法

```javascript
function onCloseSheet() {
  sheetState.value = 'collapsed'
  vpStore.clearSelection()
}
```

#### 1.4 "上拉" 文案改为设备自适应

```diff
- <div class="half-expand-hint">↑ 上拉查看完整报告</div>
+ <div class="half-expand-hint">{{ isTouchDevice ? '↑ 上拉查看完整报告' : '点击查看完整报告' }}</div>
```

新增 computed:

```javascript
const isTouchDevice = computed(() => 'ontouchstart' in window || navigator.maxTouchPoints > 0)
```

#### 1.5 新增样式

```css
.sheet-close-btn {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full, 9999px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  background: rgba(0, 0, 0, 0.05);
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary, #6B7280);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast, 0.15s);
  flex-shrink: 0;
}

.sheet-close-btn:hover {
  background: rgba(0, 0, 0, 0.1);
  color: var(--text-primary, #374151);
}

.half-title-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sheet-close-btn--full {
  margin-left: auto;
}
```

### 应测试的内容

- 半展态渲染 `.sheet-close-btn` 按钮
- 全展态渲染 `.sheet-close-btn--full` 按钮
- 点击关闭按钮触发 `sheetState` 变为 `'collapsed'`
- 非触屏设备显示 "点击查看完整报告" 而非 "上拉查看完整报告"

---

## Task 2: 地图标记增加名称标签

**Files:**
- Modify: [ViewpointMarker.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/map/ViewpointMarker.vue)
- Test: [ViewpointMarker.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/components/ViewpointMarker.test.js)

### 修改内容

在 **默认态**（zoom ≥ 9 且未选中时）的圆形评分标记 **下方** 增加名称标签，让用户无需点击即可了解观景台名称。

修改 `createContent()` 中默认态的 return 部分：

```diff
  // 默认态: 圆形评分标记 + 扩大触摸热区
  return `<div style="
    position: relative;
    transition: transform 0.3s ease;
    padding: 4px;
    cursor: pointer;
+   display: flex;
+   flex-direction: column;
+   align-items: center;
  ">
    ${pulse}
    <div style="
      width: 40px; height: 40px; border-radius: 50%;
      background: ${bg};
      color: white; display: flex; align-items: center; justify-content: center;
      font-weight: 700; font-size: 14px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.2);
      transition: box-shadow 0.3s ease, transform 0.3s ease;
    ">${getSvgBadge()}${props.score}</div>
    <div style="
      width: 0; height: 0;
      border-left: 5px solid transparent;
      border-right: 5px solid transparent;
      border-top: 5px solid ${bg};
-     margin: 0 auto;
    "></div>
+   <div style="
+     font-size: 10px;
+     color: #374151;
+     white-space: nowrap;
+     text-align: center;
+     margin-top: 2px;
+     text-shadow: 0 0 3px white, 0 0 3px white;
+     max-width: 80px;
+     overflow: hidden;
+     text-overflow: ellipsis;
+   ">${props.viewpoint.name}</div>
  </div>`
```

> **设计理由：** 只在 zoom ≥ 9（非缩略态/非选中态）的默认态显示名称。选中态已有展开名称。缩略态（zoom < 9）标记密集，不适合显示文字。

### 应测试的内容

- 默认态（zoom ≥ 9, 未选中）的 `createContent()` 输出包含 `viewpoint.name`
- 缩略态（zoom < 9）不包含名称
- 选中态不受影响（已有名称显示）
- 名称文本有 `text-overflow: ellipsis` 确保不溢出

---

## Task 3: 筛选按钮增加 Tooltip

**Files:**
- Modify: [MapTopBar.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/scheme-a/MapTopBar.vue)
- Test: [MapTopBar.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/components/MapTopBar.test.js)

### 修改内容

#### 3.1 `filterOptions` 增加 `label` 字段

```diff
  const filterOptions = [
-   { type: 'golden_mountain', icon: '🏔️' },
-   { type: 'cloud_sea', icon: '☁️' },
-   { type: 'stargazing', icon: '⭐' },
-   { type: 'frost', icon: '❄️' },
+   { type: 'golden_mountain', icon: '🏔️', label: '日照金山' },
+   { type: 'cloud_sea', icon: '☁️', label: '云海' },
+   { type: 'stargazing', icon: '⭐', label: '观星' },
+   { type: 'frost', icon: '❄️', label: '霜冻' },
  ]
```

#### 3.2 按钮添加 `title` 和 `aria-label`

```diff
  <button
    v-for="filter in filterOptions"
    :key="filter.type"
    :class="['chip', { active: activeFilters.includes(filter.type) }]"
    @click="toggleFilter(filter.type)"
+   :title="filter.label"
+   :aria-label="filter.label"
  >
    {{ filter.icon }}
  </button>
```

### 应测试的内容

- 每个 `.chip` 按钮有 `title` 属性
- `title` 值分别为 `'日照金山'`、`'云海'`、`'观星'`、`'霜冻'`
- 每个 `.chip` 按钮有 `aria-label` 属性（无障碍）

---

## Task 4: WeekTrend 折线图增强 Tooltip

**Files:**
- Modify: [WeekTrend.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/forecast/WeekTrend.vue)
- 无独立测试（ECharts 渲染需浏览器验证）

### 修改内容

当前 `buildOption()` 中 tooltip 已有 `trigger: 'axis'`，但缺少 `formatter` 导致 tooltip 只显示原始数据。添加自定义 formatter 使其显示更友好的中文内容：

```diff
  return {
-   tooltip: { trigger: 'axis' },
+   tooltip: {
+     trigger: 'axis',
+     backgroundColor: 'rgba(255, 255, 255, 0.95)',
+     borderColor: '#E5E7EB',
+     textStyle: { color: '#374151', fontSize: 12 },
+     formatter(params) {
+       if (!params || !params.length) return ''
+       let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
+       for (const p of params) {
+         if (p.value == null) continue
+         html += `<div style="display:flex;align-items:center;gap:6px;margin:2px 0">
+           ${p.marker}
+           <span>${p.seriesName}</span>
+           <span style="font-weight:700;margin-left:auto">${p.value}</span>
+         </div>`
+       }
+       return html
+     },
+   },
    legend: {
```

### 应测试的内容

- 浏览器手动验证：鼠标悬停在折线图上时出现 tooltip
- Tooltip 显示日期、每条折线的名称和分数

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend

# 涉及的单元测试
npx vitest run src/__tests__/components/MapTopBar.test.js --reporter verbose
npx vitest run src/__tests__/views/HomeView.test.js --reporter verbose
npx vitest run src/__tests__/components/ViewpointMarker.test.js --reporter verbose

# 全量回归
npx vitest run --reporter verbose
```

### 手动验证要点

1. **关闭按钮**: 半展态和全展态右上角均有 ✕ 按钮，点击后回到收起态
2. **文案适配**: PC 端（鼠标操作）显示 "点击查看完整报告"；手机端（触屏）显示 "↑ 上拉查看完整报告"
3. **地图标记**: zoom ≥ 9 时每个标记下方显示观景台名称；zoom < 9 时仅显示圆点
4. **筛选 Tooltip**: 鼠标悬停在筛选按钮上，显示中文名称（如 "日照金山"）
5. **趋势图 Tooltip**: 鼠标悬停在 WeekTrend 折线图上，显示日期和各事件分数

---

*文档版本: v1.0 | 创建: 2026-02-20 | 关联: UX 评估报告, MG6A, MG6B*
