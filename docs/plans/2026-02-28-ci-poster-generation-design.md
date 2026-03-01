# CI 预生成海报方案设计

## 背景

本项目部署在 GitHub，由 GitHub Actions 每日运行预测模型并部署到 Cloudflare Pages。当前的图片导出流程依赖用户在浏览器端手动点击"一键导出"，通过 `html2canvas` 截图 + `JSZip` 打包下载。

**现状问题**：本地自动化工作流（用于发布小红书）无法自动获取渲染后的图片和摘要 JSON，需要手动操作浏览器。

**目标**：将图片截图和 JSON 摘要的生成从浏览器端移到 CI 端，作为静态资源部署，本地自动化只需 HTTP 下载。

## 设计决策

| 决策 | 选定方案 | 理由 |
|------|---------|------|
| 图片生成方式 | CI 端 Playwright 截图 | 使用真实 Chromium 引擎，渲染与线上 100% 一致 |
| JSON 生成方式 | Node.js 独立脚本 | 逻辑简单，不依赖浏览器环境 |
| 页面天数参数化 | URL Query `?days=N` | 比点击按钮更稳定，脚本最简单 |
| 天数起算 | 统一从明天开始 | `days.slice(1, 1 + N)`，3 天和 7 天逻辑一致 |
| 截图套数 | 两套（3 天 + 7 天） | 3 天用于小红书日帖，7 天用于周报 |
| 前端导出功能 | 移除 | CI 预生成替代，减少 ~50KB 前端依赖 |

## 改造后的 CI 流程

```
deploy.yml 改动（build 之后、deploy 之前新增）

1. apt-get install fonts-noto-cjk fonts-noto-color-emoji     # 中文+Emoji字体
2. npx playwright install --with-deps chromium                # 安装 Chromium
3. node scripts/generate-posters.mjs                          # 截图 + JSON
4. → 产物写入 frontend/dist/data/posters/
5. 正常 deploy to Cloudflare Pages
```

预计增加 CI 时间：~25 秒。

## 部署后的静态资源结构

```
/data/posters/
  ├── 3day/
  │   ├── gongga.png
  │   ├── siguniang.png
  │   ├── yala.png
  │   ├── genie.png
  │   ├── yading.png
  │   ├── lixiao.png
  │   └── other.png
  ├── week/
  │   ├── gongga.png
  │   ├── siguniang.png
  │   ├── yala.png
  │   ├── genie.png
  │   ├── yading.png
  │   ├── lixiao.png
  │   └── other.png
  ├── summary_3day.json
  └── summary_week.json
```

本地获取方式：
```bash
BASE="https://gmp.pages.dev/data/posters"
curl -o summary_3day.json "$BASE/summary_3day.json"
curl -o gongga_3day.png  "$BASE/3day/gongga.png"
```

## 具体变更

### 1. 新增脚本 `scripts/generate-posters.mjs`

核心职责：
1. 启动本地 HTTP 服务器（`serve` 或 `http-server`），提供 `frontend/dist/`
2. 用 Playwright 分别打开 `http://localhost:PORT/ops/poster?days=3` 和 `?days=7`
3. 等待页面渲染完成（`document.fonts.ready` + `.poster-content` 可见）
4. 逐个 `.group-section` 元素调用 `element.screenshot()` 保存 PNG
5. 读取 `frontend/dist/data/poster.json`，运行 `buildSummary` 同等逻辑生成两份 JSON
6. 将所有产物写入 `frontend/dist/data/posters/`

关键参数：
- `deviceScaleFactor: 2`（与现有 html2canvas scale=2 一致，保证图片清晰度）
- 输出目录：`frontend/dist/data/posters/{3day,week}/`

### 2. 修改 `PosterView.vue`

**改动 1**：读取 URL Query 设置初始天数

```javascript
// 新增：从 URL query 读取天数，默认 7
import { useRoute } from 'vue-router'
const route = useRoute()
const selectedDays = ref(Number(route.query.days) || 7)
```

**改动 2**：天数从明天开始

```javascript
// 改前
const displayedDays = computed(() => posterData.value.days.slice(0, selectedDays.value))

// 改后：统一跳过 days[0]（今天），从明天开始
const displayedDays = computed(() => posterData.value.days.slice(1, 1 + selectedDays.value))
```

**改动 3**：移除导出相关代码

删除以下内容：
- `exportAll()` 函数（~70 行）
- `buildSummary()` 函数（~60 行）
- `exporting` / `exportProgress` 响应式状态
- 导出按钮 UI（`<button class="export-btn">` 区域）
- `html2canvas` 和 `jszip` 的动态 import

**改动 4**：天数选择器调整

```html
<!-- 改前：3/5/7 天 -->
<button v-for="d in [3, 5, 7]" ...>{{ d }}天</button>

<!-- 改后：3/7 天 -->
<button v-for="d in [3, 7]" ...>{{ d }}天</button>
```

### 3. 修改 `deploy.yml`

在 `Build frontend` 和 `Deploy to Cloudflare Pages` 之间新增步骤：

```yaml
- name: Install fonts for screenshot
  run: |
    sudo apt-get update
    sudo apt-get install -y fonts-noto-cjk fonts-noto-color-emoji

- name: Generate poster screenshots and summaries
  run: |
    npx playwright install --with-deps chromium
    node scripts/generate-posters.mjs
  working-directory: frontend
```

### 4. 更新 `PosterView.test.js`

- 移除 `buildSummary` 相关测试（迁移到新脚本的测试）
- 移除 `export filename` 相关测试
- 更新"默认天数"测试：从 5 天改为 7 天
- 新增：query 参数 `?days=3` 设置初始天数的测试

### 5. 移除前端依赖

```bash
cd frontend
npm uninstall html2canvas jszip
```

## 验证计划

### 自动化测试

1. **前端单测**：
   ```bash
   cd frontend && npx vitest run
   ```
   确保 PosterView 和 PredictionMatrix 测试通过（适配后的新测试）

2. **脚本集成测试**：
   ```bash
   cd frontend && npm run build && node scripts/generate-posters.mjs
   ```
   验证产物文件生成：14 张 PNG + 2 个 JSON

### 浏览器 Agent 自动验证

使用浏览器 agent 完成以下验证，无需手动操作：

1. **页面功能验证**：
   - 启动 `npm run dev`，agent 访问 `/ops/poster?days=3` 和 `/ops/poster?days=7`
   - 验证表格正确显示从明天起的天数
   - 验证天数选择器只有 3/7 两个选项
   - 验证导出按钮已移除

2. **视觉风格对比**：
   - 将 Playwright 截图结果与 `posters_20260226/` 目录中的基准图片进行对比
   - 基准图片为之前通过 html2canvas 手动导出的 PNG（内容不同，但风格应一致）
   - 对比要点：色阶渲染、字体、emoji、表格布局、圆角/阴影
   - 基准文件列表：
     - `posters_20260226/poster_gongga_20260226.png`
     - `posters_20260226/poster_siguniang_20260226.png`
     - `posters_20260226/poster_yala_20260226.png`
     - `posters_20260226/poster_genie_20260226.png`
     - `posters_20260226/poster_yading_20260226.png`
     - `posters_20260226/poster_lixiao_20260226.png`
     - `posters_20260226/poster_other_20260226.png`

3. **JSON 内容验证**：
   - agent 读取生成的 `summary_3day.json`，验证日期范围从明天起 3 天
   - agent 读取生成的 `summary_week.json`，验证日期范围从明天起 7 天
