# MI1C: 移除前端导出功能 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从 PosterView.vue 移除 `exportAll()`、`buildSummary()`、导出按钮 UI，卸载 html2canvas/jszip 依赖。

**Architecture:** 纯删除操作。移除 ~130 行 JS 代码、UI 模板、CSS 样式，卸载 2 个 npm 包（减少 ~50KB）。

**Tech Stack:** Vue 3, Vitest, npm

---

### Task 1: 移除导出相关测试

**Files:**
- Modify: [`PosterView.test.js`](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/views/PosterView.test.js)

**Step 1: 删除测试**

删除以下内容：
- `buildSummaryFromPosterData` 内联函数（L70-121）
- `summaryData` 测试数据（L123-151）
- `describe('buildSummary', ...)` 整块（L153-218）
- `describe('export filename includes date', ...)` 整块（L222-246）

> 保留 `describe('PosterView', ...)` 中的 3 个测试。  
> buildSummary 测试已在 MI1B 中迁移到 `scripts/__tests__/generate-posters.test.mjs`。

**Step 2: 运行测试确认通过**

Run: `cd frontend && npx vitest run src/__tests__/views/PosterView.test.js`

Expected: PASS（只剩 3 个测试）

---

### Task 2: 移除 PosterView.vue 中的导出代码

**Files:**
- Modify: [`PosterView.vue`](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/views/PosterView.vue)

**Step 1: 删除 template**

删除导出按钮（L31-35）：
```html
<!-- 删除这 5 行 -->
<button class="export-btn" :disabled="exporting" @click="exportAll">
    <svg ...>...</svg>
    <span v-if="exporting">{{ exportProgress }}</span>
    <span v-else>一键导出全部</span>
</button>
```

**Step 2: 删除 script**

删除以下变量和函数：
- `exporting` 和 `exportProgress`（L79-80）
- `buildSummary()` 函数（L120-178）
- `exportAll()` 函数（L180-249）

**Step 3: 删除 style**

删除 `.export-btn` 相关样式（L339-363）

**Step 4: 运行测试**

Run: `cd frontend && npx vitest run src/__tests__/views/PosterView.test.js`

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/views/PosterView.vue frontend/src/__tests__/views/PosterView.test.js
git commit -m "feat(poster): remove browser export (exportAll, buildSummary, export UI)"
```

---

### Task 3: 卸载 npm 依赖

**Files:**
- Modify: [`package.json`](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/package.json)

**Step 1: 卸载**

```bash
cd frontend && npm uninstall html2canvas jszip
```

**Step 2: 确认构建通过**

Run: `cd frontend && npm run build`

Expected: 构建成功，无残留引用

**Step 3: 运行全部测试**

Run: `cd frontend && npx vitest run`

Expected: 全部 PASS

**Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: remove html2canvas and jszip dependencies"
```

---

## 验证计划

### 自动化测试
```bash
cd frontend && npx vitest run
cd frontend && npm run build
```

### 手动检查
- `package.json` 中不再包含 `html2canvas` 和 `jszip`
- `PosterView.vue` 中搜索 `export`、`html2canvas`、`jszip` 无结果
