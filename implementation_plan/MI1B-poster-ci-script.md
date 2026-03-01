# MI1B: CI 截图脚本 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 新建 `generate-posters.mjs` 脚本，用 Playwright 截图海报页面 + 生成摘要 JSON，供 CI 使用。

**Architecture:** 启动本地静态服务器 serve `dist/`，用 Playwright Chromium 打开 `?days=3` 和 `?days=7`，逐个 `.group-section` 元素截图保存 PNG，同时从 `poster.json` 生成两份摘要 JSON。`buildSummary` 从 `PosterView.vue` 迁出为独立导出函数。

**Tech Stack:** Playwright, Node.js (ESM), serve-handler, Vitest

---

### Task 1: 编写 buildSummary 单元测试

**Files:**
- Create: `frontend/scripts/__tests__/generate-posters.test.mjs`

**Step 1: 创建测试文件**

迁移 [`PosterView.test.js`](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/views/PosterView.test.js) 中 `buildSummaryFromPosterData` 的测试数据和全部 7 个测试用例。import 从新脚本的 `buildSummary` 导出。

```javascript
import { describe, it, expect } from 'vitest'
import { buildSummary } from '../generate-posters.mjs'

const summaryData = { /* 与 PosterView.test.js L123-151 完全一致 */ }

describe('buildSummary', () => {
    it('only includes slots with score >= 60 in highlights', () => { ... })
    it('highlights are sorted by score descending', () => { ... })
    it('group_overview records the best viewpoint', () => { ... })
    it('date_range uses Chinese format', () => { ... })
    it('respects selected days count', () => { ... })
    it('dayOffset=1 skips today', () => { ... })
    it('finds group best even if all are < 60', () => { ... })
})
```

> 具体测试代码直接从 PosterView.test.js L153-218 复制，仅把 `buildSummaryFromPosterData` 改为 `buildSummary`。

**Step 2: 运行测试确认失败**

Run: `cd frontend && npx vitest run scripts/__tests__/generate-posters.test.mjs`

Expected: FAIL — 文件不存在

---

### Task 2: 实现 generate-posters.mjs

**Files:**
- Create: `frontend/scripts/generate-posters.mjs`

**Step 1: 实现脚本**

脚本核心结构：

```javascript
import { chromium } from 'playwright'
import { createServer } from 'http'
import { readFileSync, mkdirSync, writeFileSync } from 'fs'
import { join, resolve } from 'path'
import handler from 'serve-handler'

// 独立导出，供测试使用
export function buildSummary(data, dayCount, dayOffset = 0) {
    // 与 PosterView.vue L127-178 逻辑完全一致
}

const GROUP_KEYS = ['gongga', 'siguniang', 'yala', 'genie', 'yading', 'lixiao', 'other']

const SCREENSHOT_CONFIGS = [
    { days: 3, dir: '3day' },
    { days: 7, dir: 'week' },
]

async function main() {
    const distDir = resolve(import.meta.dirname, '../dist')
    const outputBase = join(distDir, 'data', 'posters')

    // 1. 启动本地静态服务器（serve-handler）
    // 2. 启动 Playwright（deviceScaleFactor: 2）
    // 3. 分别打开 ?days=3 和 ?days=7，逐个 .group-section 截图
    // 4. 从 poster.json 生成 summary_3day.json 和 summary_week.json（dayOffset=1）
}

// 仅主脚本运行时执行
const isMain = process.argv[1] && resolve(process.argv[1]) === resolve(import.meta.filename)
if (isMain) main().catch(err => { console.error(err); process.exit(1) })
```

> 完整实现见总览文档 MI1 Task 4 Step 3。

**Step 2: 安装依赖**

```bash
cd frontend && npm install --save-dev serve-handler
```

**Step 3: 运行 buildSummary 单元测试确认通过**

Run: `cd frontend && npx vitest run scripts/__tests__/generate-posters.test.mjs`

Expected: PASS

**Step 4: Commit**

```bash
git add frontend/scripts/ frontend/package.json frontend/package-lock.json
git commit -m "feat: add CI poster generation script with Playwright screenshots"
```

---

## 验证计划

### 自动化测试
```bash
cd frontend && npx vitest run scripts/__tests__/generate-posters.test.mjs
```

### 集成测试（MI1D 阶段执行）
```bash
cd frontend && npm run build && node scripts/generate-posters.mjs
# 检查产物：14 PNG + 2 JSON
ls -la dist/data/posters/3day/ dist/data/posters/week/
cat dist/data/posters/summary_3day.json | head -5
```
