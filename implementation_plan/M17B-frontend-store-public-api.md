# M17B: Store 公共接口补全

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 为 viewpointStore 和 routeStore 补充三方案 (A/B/C) 共同依赖但 M17 原始定义中缺失的公共接口。

**依赖模块:** M17 (前端数据层)

---

## 背景

M17 定义了 viewpointStore 和 routeStore 的基础接口。后续的方案实施计划 (MA1/MA3/MA4/MB1/MB2/MB3/MC1/MC2) 在编写 HomeView 时，引用了若干 M17 未暴露的 store 方法。经过全面分析，这些缺失接口可分为三类：

### 问题 1: `loadForecast(id)` — 批量预加载需求

三方案的 HomeView 初始化时均需**批量预加载**多个观景台的 forecast 数据：
- A 方案 (MA1): 加载前 3 个观景台
- B 方案 (MB1): 加载全部观景台
- C 方案 (MC1): 加载第一个观景台

现有 `selectViewpoint(id)` 会同时设置 `selectedId`，批量调用会导致 `selectedId` 被反复修改。需要一个**纯数据加载**方法。

### 问题 2: `clearSelection()` — 清除选中状态

A 方案 (MA1) 中 BottomSheet 收起和 `onActivated` 返回时需要重置选中状态。

### 问题 3: `currentDay` — 当前日期的完整 day 对象

MA1 和 MA3 直接引用 `vpStore.currentDay` 获取包含 `date/summary/best_event/events` 的完整 day 对象。MB2 和 MC2 则在组件内部本地计算。将此逻辑提升到 store 可消除重复。

### 设计参考

- [10-frontend-common.md §10.0.2 数据加载策略](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md)
- [M17-frontend-data-layer.md](file:///Users/mpb/WorkSpace/golden-moment-predictor/implementation_plan/M17-frontend-data-layer.md): 原始 store 定义

### 影响分析

| 接口 | 使用方案 | 文件 |
|------|---------|------|
| `loadForecast(id)` | MA1, MA4, MB1, MC1 | HomeView.vue (各方案) |
| `clearSelection()` | MA1 | HomeView.vue (A方案) |
| `currentDay` | MA1, MA3, MB2(可改用), MC2(可改用) | HomeView.vue, 各详情组件 |

---

## Task 1: viewpointStore — 添加 `ensureForecast(id)`

**Files:**
- Modify: `frontend/src/stores/viewpoints.js`
- Test: `frontend/src/__tests__/stores/viewpoints.test.js`

> [!NOTE]
> 命名为 `ensureForecast` 而非 `loadForecast`，原因：
> 1. 与 composable 层的 `useDataLoader.loadForecast()` 区分
> 2. 语义更准确："确保数据已加载到缓存"（幂等操作）

### 接口

```javascript
/**
 * 预加载观景台预测数据（不修改 selectedId）
 * 幂等：已缓存则跳过请求
 * @param {string} id - 观景台 ID
 */
async function ensureForecast(id) {
    if (forecasts.value[id]) return
    loading.value = true
    try {
        forecasts.value[id] = await loadForecast(id)
    } catch (e) {
        error.value = e.message
    } finally {
        loading.value = false
    }
}
```

### 应测试的内容

- `ensureForecast(id)` 加载数据到 `forecasts` 缓存，**不修改** `selectedId`
- 已缓存时不重复请求
- 加载失败时设置 `error`

### 变更位置

在 `viewpoints.js` 的 `selectViewpoint` 下方添加 `ensureForecast`，并在 return 中导出。

**Step 1: 在 `viewpoints.test.js` 中追加测试**

```javascript
it('ensureForecast() loads forecast without changing selectedId', async () => {
    const store = useViewpointStore()
    await store.init()
    // selectedId 初始为 null
    expect(store.selectedId).toBeNull()

    await store.ensureForecast('niubei_gongga')

    // forecast 已加载
    expect(store.forecasts['niubei_gongga']).toBeDefined()
    expect(store.forecasts['niubei_gongga'].viewpoint_id).toBe('niubei_gongga')
    // selectedId 未被修改
    expect(store.selectedId).toBeNull()
})

it('ensureForecast() skips if already cached', async () => {
    const store = useViewpointStore()
    await store.init()
    await store.ensureForecast('niubei_gongga')

    // 再次调用，不应触发额外操作
    const before = store.forecasts['niubei_gongga']
    await store.ensureForecast('niubei_gongga')
    expect(store.forecasts['niubei_gongga']).toBe(before)
})
```

**Step 2: 运行测试，确认失败**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run src/__tests__/stores/viewpoints.test.js
```

Expected: FAIL — `store.ensureForecast is not a function`

**Step 3: 实现 `ensureForecast`**

在 `viewpoints.js` 中添加方法并导出。

**Step 4: 运行测试，确认通过**

```bash
npx vitest run src/__tests__/stores/viewpoints.test.js
```

Expected: PASS

**Step 5: 提交**

```bash
git add frontend/src/stores/viewpoints.js frontend/src/__tests__/stores/viewpoints.test.js
git commit -m "feat(store): add ensureForecast() for batch preloading without selection"
```

---

## Task 2: viewpointStore — 添加 `clearSelection()`

**Files:**
- Modify: `frontend/src/stores/viewpoints.js`
- Test: `frontend/src/__tests__/stores/viewpoints.test.js`

### 接口

```javascript
/** 清除选中状态 (重置 selectedId 为 null) */
function clearSelection() {
    selectedId.value = null
}
```

### 应测试的内容

- `clearSelection()` 将 `selectedId` 设为 `null`
- 调用后 `currentViewpoint` 和 `currentForecast` 均返回 `null/undefined`

**Step 1: 在 `viewpoints.test.js` 中追加测试**

```javascript
it('clearSelection() resets selectedId to null', async () => {
    const store = useViewpointStore()
    await store.init()
    await store.selectViewpoint('niubei_gongga')
    expect(store.selectedId).toBe('niubei_gongga')

    store.clearSelection()

    expect(store.selectedId).toBeNull()
    expect(store.currentViewpoint).toBeUndefined()
    expect(store.currentForecast).toBeNull()
})
```

**Step 2: 运行测试，确认失败**

```bash
npx vitest run src/__tests__/stores/viewpoints.test.js
```

Expected: FAIL — `store.clearSelection is not a function`

**Step 3: 实现 `clearSelection`**

在 `viewpoints.js` 中添加方法并导出。

**Step 4: 运行测试，确认通过**

```bash
npx vitest run src/__tests__/stores/viewpoints.test.js
```

Expected: PASS

**Step 5: 提交**

```bash
git add frontend/src/stores/viewpoints.js frontend/src/__tests__/stores/viewpoints.test.js
git commit -m "feat(store): add clearSelection() to reset viewpoint selection"
```

---

## Task 3: viewpointStore — 添加 `currentDay` getter

**Files:**
- Modify: `frontend/src/stores/viewpoints.js`
- Test: `frontend/src/__tests__/stores/viewpoints.test.js`

### 接口

```javascript
/** 当前选中日期的完整 day 对象 (含 date/summary/best_event/events) */
const currentDay = computed(() => {
    const forecast = currentForecast.value
    if (!forecast?.daily) return null
    if (selectedDate.value) {
        return forecast.daily.find(d => d.date === selectedDate.value) ?? forecast.daily[0] ?? null
    }
    return forecast.daily[0] ?? null
})
```

### 与 `currentDayEvents` 的关系

| getter | 返回值 | 用途 |
|--------|-------|------|
| `currentDayEvents` | `events[]` (仅事件数组) | M25 DetailView 等只需事件列表的场景 |
| `currentDay` | 完整 day 对象 `{ date, summary, best_event, events }` | HomeView 等需要 summary/best_event 的场景 |

两者共存，`currentDayEvents` 保持向后兼容。

### 应测试的内容

- `currentDay` 返回匹配 `selectedDate` 的完整 day 对象
- day 对象包含 `date`、`events`、`summary`（如果数据有的话）
- `selectedDate` 不匹配任何 day 时，fallback 到第一天
- 无 forecast 时返回 `null`

**Step 1: 在 `viewpoints.test.js` 中追加测试**

```javascript
it('currentDay returns full day object for selected date', async () => {
    const store = useViewpointStore()
    await store.init()
    await store.selectViewpoint('niubei_gongga')
    store.selectedDate = '2026-02-18'

    expect(store.currentDay).toBeDefined()
    expect(store.currentDay.date).toBe('2026-02-18')
    expect(store.currentDay.events).toHaveLength(2)
})

it('currentDay falls back to first day if selectedDate not found', async () => {
    const store = useViewpointStore()
    await store.init()
    await store.selectViewpoint('niubei_gongga')
    store.selectedDate = '9999-12-31'  // 不存在的日期

    // fallback 到第一天
    expect(store.currentDay).toBeDefined()
    expect(store.currentDay.date).toBe('2026-02-18')
})

it('currentDay returns null when no forecast loaded', async () => {
    const store = useViewpointStore()
    await store.init()
    // 未选择任何观景台
    expect(store.currentDay).toBeNull()
})
```

**Step 2: 运行测试，确认失败**

```bash
npx vitest run src/__tests__/stores/viewpoints.test.js
```

Expected: FAIL — `store.currentDay` 是 `undefined`

**Step 3: 实现 `currentDay`**

在 `viewpoints.js` 中添加 computed 并导出。

**Step 4: 运行测试，确认通过**

```bash
npx vitest run src/__tests__/stores/viewpoints.test.js
```

Expected: PASS

**Step 5: 提交**

```bash
git add frontend/src/stores/viewpoints.js frontend/src/__tests__/stores/viewpoints.test.js
git commit -m "feat(store): add currentDay getter for full day object access"
```

---

## Task 4: routeStore — 添加 `ensureIndex()`

**Files:**
- Modify: `frontend/src/stores/routes.js`
- Test: `frontend/src/__tests__/stores/routes.test.js`

### 背景

MA1 和 MB1 的 HomeView 中调用 `routeStore.loadIndex()`，但 routeStore 只暴露了 `init()`。由于 viewpointStore 和 routeStore 各自调用 `init()`，routeStore 的 `init()` 也会调用 `useDataLoader().loadIndex()` 进行重复的 `index.json` + `meta.json` 请求（虽然 useDataLoader 有缓存所以实际不会网络请求，但语义上 routeStore.init() 足够）。

实际上，三方案的 HomeView 需要的是"确保 route 索引已加载" — `init()` 已满足需求。因此这里**不新增方法**，只需让各方案计划代码将 `routeStore.loadIndex()` 改为 `routeStore.init()` 即可。

但为了保持调用方的一致性和语义清晰，添加 `ensureIndex()` 作为 `init()` 的幂等别名：

### 接口

```javascript
/**
 * 确保线路索引已加载（幂等别名）
 * 若已加载则跳过
 */
async function ensureIndex() {
    if (index.value.length > 0) return
    await init()
}
```

### 应测试的内容

- `ensureIndex()` 首次调用加载数据
- 已加载后再调用不重复加载

**Step 1: 在 `routes.test.js` 中追加测试**

```javascript
it('ensureIndex() loads routes if not already loaded', async () => {
    const store = useRouteStore()
    expect(store.index).toHaveLength(0)

    await store.ensureIndex()

    expect(store.index).toHaveLength(1)
    expect(store.index[0].id).toBe('lixiao')
})

it('ensureIndex() skips if already loaded', async () => {
    const store = useRouteStore()
    await store.init()
    expect(store.index).toHaveLength(1)

    // 再次调用
    await store.ensureIndex()
    expect(store.index).toHaveLength(1)
})
```

**Step 2: 运行测试，确认失败**

```bash
npx vitest run src/__tests__/stores/routes.test.js
```

Expected: FAIL — `store.ensureIndex is not a function`

**Step 3: 实现 `ensureIndex`**

在 `routes.js` 中添加方法并导出。

**Step 4: 运行测试，确认通过**

```bash
npx vitest run src/__tests__/stores/routes.test.js
```

Expected: PASS

**Step 5: 提交**

```bash
git add frontend/src/stores/routes.js frontend/src/__tests__/stores/routes.test.js
git commit -m "feat(store): add ensureIndex() idempotent alias for route store"
```

---

## 验证命令

```bash
# 运行全部 store 测试
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run src/__tests__/stores/

# 确认全量测试无回归
npx vitest run

# 确认构建不报错
npm run build
```

### 最终接口清单 (变更后)

**viewpointStore 新增:**

| 接口 | 类型 | 说明 |
|------|------|------|
| `ensureForecast(id)` | action | 预加载 forecast，不修改 selectedId |
| `clearSelection()` | action | 重置 selectedId 为 null |
| `currentDay` | getter | 当前 selectedDate 对应的完整 day 对象 |

**routeStore 新增:**

| 接口 | 类型 | 说明 |
|------|------|------|
| `ensureIndex()` | action | 幂等加载线路索引 |
