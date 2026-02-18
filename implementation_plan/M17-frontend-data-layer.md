# M17: 前端数据层 (DataLoader + Pinia Store)

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现前端数据加载层和 Pinia 状态管理，提供统一的 JSON 数据获取、缓存和共享机制。

**依赖模块:** M16 (前端项目初始化)

---

## 背景

前端所有数据来自后端 `generate-all` 命令预生成的静态 JSON 文件。数据加载策略为"启动加载索引 + 按需加载详情":

1. **启动时** 加载 `index.json` (观景台/线路索引) + `meta.json` (元数据)
2. **选择观景台时** 按需加载 `viewpoints/{id}/forecast.json`
3. **查看某日详情时** 按需加载 `viewpoints/{id}/timeline_YYYY-MM-DD.json`

### 设计参考

- [10-frontend-common.md §10.0.2 数据加载策略](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/10-frontend-common.md): 加载流程 Sequence 图、useDataLoader 接口定义
- [05-api.md §5.2 JSON 输出文件结构](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md): JSON 数据格式定义

### JSON 数据 URL 映射

| 数据 | URL | 加载时机 |
|------|-----|----------|
| 索引 | `/data/index.json` | 启动时 |
| 元数据 | `/data/meta.json` | 启动时 |
| 观景台预测 | `/data/viewpoints/{id}/forecast.json` | 选择观景台时 |
| 逐时数据 | `/data/viewpoints/{id}/timeline_YYYY-MM-DD.json` | 查看某日详情时 |
| 线路预测 | `/data/routes/{id}/forecast.json` | 选择线路时 |

---

## Task 1: useDataLoader Composable

**Files:**
- Create: `frontend/src/composables/useDataLoader.js`
- Test: `frontend/src/__tests__/composables/useDataLoader.test.js`

### 接口定义

```javascript
// frontend/src/composables/useDataLoader.js

/**
 * JSON 数据加载 composable，提供统一的数据获取+缓存机制。
 *
 * 加载策略:
 * - 内存缓存: Map<url, data>，页面生命周期内有效
 * - 重复请求: 同一 URL 不重复 fetch
 * - 错误处理: fetch 失败抛出，调用方自行处理
 *
 * @returns {Object} { loadIndex, loadForecast, loadTimeline, loadRouteForecast, loading, error }
 */
export function useDataLoader() {
  const cache = new Map()
  const loading = ref(false)
  const error = ref(null)

  /**
   * 通用加载函数 (内部)
   * @param {string} url - 数据 URL (相对于 /data/)
   * @returns {Promise<Object>} 解析后的 JSON 对象
   */
  async function _fetch(url) {
    if (cache.has(url)) return cache.get(url)
    loading.value = true
    error.value = null
    try {
      const resp = await fetch(`/data/${url}`)
      if (!resp.ok) throw new Error(`Failed to load ${url}: ${resp.status}`)
      const data = await resp.json()
      cache.set(url, data)
      return data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载全局索引 + 元数据
   * @returns {Promise<{index: Object, meta: Object}>}
   */
  async function loadIndex() {
    const [index, meta] = await Promise.all([
      _fetch('index.json'),
      _fetch('meta.json'),
    ])
    return { index, meta }
  }

  /**
   * 加载观景台预测数据
   * @param {string} viewpointId - 观景台 ID (如 'niubei_gongga')
   * @returns {Promise<Object>} forecast.json 内容
   */
  async function loadForecast(viewpointId) {
    return _fetch(`viewpoints/${viewpointId}/forecast.json`)
  }

  /**
   * 加载逐时数据
   * @param {string} viewpointId - 观景台 ID
   * @param {string} date - 日期 'YYYY-MM-DD'
   * @returns {Promise<Object>} timeline_YYYY-MM-DD.json 内容
   */
  async function loadTimeline(viewpointId, date) {
    return _fetch(`viewpoints/${viewpointId}/timeline_${date}.json`)
  }

  /**
   * 加载线路预测数据
   * @param {string} routeId - 线路 ID (如 'lixiao')
   * @returns {Promise<Object>} 线路 forecast.json 内容
   */
  async function loadRouteForecast(routeId) {
    return _fetch(`routes/${routeId}/forecast.json`)
  }

  return { loadIndex, loadForecast, loadTimeline, loadRouteForecast, loading, error }
}
```

### 应测试的内容

使用 Vitest 测试 (直接读取 `public/data/` 下的真实 JSON 数据，通过 Vite dev server 提供):

- `loadIndex()` → 同时请求 `index.json` + `meta.json`，返回解析后的对象
- `loadForecast('niubei_gongga')` → 请求正确 URL，返回 JSON
- `loadTimeline('niubei_gongga', '2026-02-18')` → 请求正确 URL（使用当天日期）
- 缓存: 同一 URL 多次调用只有 1 次网络请求
- 错误: 404 → 抛出异常，`error.value` 有值
- `loading.value` 在加载期间为 true

---

## Task 2: Pinia Viewpoint Store

**Files:**
- Create: `frontend/src/stores/viewpoints.js`
- Test: `frontend/src/__tests__/stores/viewpoints.test.js`

### 接口定义

```javascript
// frontend/src/stores/viewpoints.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDataLoader } from '@/composables/useDataLoader'

export const useViewpointStore = defineStore('viewpoints', () => {
  const { loadIndex, loadForecast, loadTimeline } = useDataLoader()

  // --- State ---
  const index = ref([])           // index.json → viewpoints 数组
  const meta = ref(null)          // meta.json
  const forecasts = ref({})       // { viewpointId: forecast.json }
  const timelines = ref({})       // { "viewpointId:date": timeline.json }
  const selectedId = ref(null)    // 当前选中的观景台 ID
  const selectedDate = ref(null)  // 当前选中的日期 (默认=今天)
  const loading = ref(false)
  const error = ref(null)

  // --- Getters ---

  /** 当前选中的观景台信息 (来自 index) */
  const currentViewpoint = computed(() =>
    index.value.find(v => v.id === selectedId.value)
  )

  /** 当前选中观景台的预测数据 */
  const currentForecast = computed(() =>
    forecasts.value[selectedId.value] ?? null
  )

  /** 当前选中日期的事件列表 */
  const currentDayEvents = computed(() => {
    const forecast = currentForecast.value
    if (!forecast || !selectedDate.value) return []
    const day = forecast.daily?.find(d => d.date === selectedDate.value)
    return day?.events ?? []
  })

  /** 当前选中日期的逐时数据 */
  const currentTimeline = computed(() => {
    const key = `${selectedId.value}:${selectedDate.value}`
    return timelines.value[key] ?? null
  })

  // --- Actions ---

  /** 初始化: 加载索引 + 元数据 */
  async function init() {
    loading.value = true
    error.value = null
    try {
      const { index: idx, meta: m } = await loadIndex()
      index.value = idx.viewpoints
      meta.value = m
      // 默认日期 = 今天 (YYYY-MM-DD)
      if (!selectedDate.value) {
        selectedDate.value = new Date().toISOString().split('T')[0]
      }
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  /** 选择观景台 → 自动加载预测 */
  async function selectViewpoint(id) {
    selectedId.value = id
    if (!forecasts.value[id]) {
      loading.value = true
      try {
        forecasts.value[id] = await loadForecast(id)
      } catch (e) {
        error.value = e.message
      } finally {
        loading.value = false
      }
    }
  }

  /** 选择日期 → 自动加载逐时数据 */
  async function selectDate(date) {
    selectedDate.value = date
    const key = `${selectedId.value}:${date}`
    if (selectedId.value && !timelines.value[key]) {
      loading.value = true
      try {
        timelines.value[key] = await loadTimeline(selectedId.value, date)
      } catch (e) {
        error.value = e.message
      } finally {
        loading.value = false
      }
    }
  }

  return {
    // State
    index, meta, forecasts, timelines, selectedId, selectedDate, loading, error,
    // Getters
    currentViewpoint, currentForecast, currentDayEvents, currentTimeline,
    // Actions
    init, selectViewpoint, selectDate,
  }
})
```

---

## Task 3: Pinia Route Store

**Files:**
- Create: `frontend/src/stores/routes.js`
- Test: `frontend/src/__tests__/stores/routes.test.js`

### 接口定义

```javascript
// frontend/src/stores/routes.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useDataLoader } from '@/composables/useDataLoader'

export const useRouteStore = defineStore('routes', () => {
  const { loadIndex, loadRouteForecast } = useDataLoader()

  // --- State ---
  const index = ref([])           // index.json → routes 数组
  const forecasts = ref({})       // { routeId: forecast.json }
  const selectedId = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // --- Getters ---
  const currentRoute = computed(() =>
    index.value.find(r => r.id === selectedId.value)
  )
  const currentForecast = computed(() =>
    forecasts.value[selectedId.value] ?? null
  )

  // --- Actions ---
  async function init() {
    loading.value = true
    try {
      const { index: idx } = await loadIndex()
      index.value = idx.routes
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function selectRoute(id) {
    selectedId.value = id
    if (!forecasts.value[id]) {
      loading.value = true
      try {
        forecasts.value[id] = await loadRouteForecast(id)
      } catch (e) {
        error.value = e.message
      } finally {
        loading.value = false
      }
    }
  }

  return {
    index, forecasts, selectedId, loading, error,
    currentRoute, currentForecast,
    init, selectRoute,
  }
})
```

---

## Task 4: Pinia App Store (全局 UI 状态)

**Files:**
- Create: `frontend/src/stores/app.js`

```javascript
// frontend/src/stores/app.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  const isMobile = ref(window.innerWidth < 768)
  const sidebarOpen = ref(false)
  const filterEvent = ref(null)       // 当前事件类型筛选
  const filterMinScore = ref(0)       // 最低评分筛选

  // 监听窗口大小变化
  function initResponsive() {
    window.addEventListener('resize', () => {
      isMobile.value = window.innerWidth < 768
    })
  }

  return { isMobile, sidebarOpen, filterEvent, filterMinScore, initResponsive }
})
```

---

## Task 5: 安装测试框架

**Files:**
- Modify: `frontend/package.json` (dev dependencies)
- Create: `frontend/vitest.config.js`

**Step 1: 安装 Vitest + 测试工具**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm install -D vitest @vue/test-utils happy-dom msw
```

**Step 2: 创建 Vitest 配置**

```javascript
// frontend/vitest.config.js
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    globals: true,
    alias: {
      '@': '/src',
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
```

**Step 3: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): add Vitest testing framework"
```

---

## 验证命令

```bash
# 单元测试
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npx vitest run

# 开发服务器启动后手动验证: 打开浏览器控制台
# 执行 store.init() 观察数据加载请求
npm run dev
```
