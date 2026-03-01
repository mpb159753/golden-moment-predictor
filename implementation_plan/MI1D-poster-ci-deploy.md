# MI1D: CI 流程集成 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

> [!IMPORTANT]
> **前置条件：** MI1A + MI1B + MI1C 全部完成后再执行此 Task。

**Goal:** 修改 `deploy.yml`，在 build 后、deploy 前新增 Playwright 截图步骤，完成端到端验证。

**Architecture:** 在 GitHub Actions 中安装中文字体和 Chromium，运行 `generate-posters.mjs`，产物写入 `dist/` 后随 Cloudflare Pages 部署。

**Tech Stack:** GitHub Actions, Playwright, Cloudflare Pages

---

### Task 1: 修改 deploy.yml

**Files:**
- Modify: [`.github/workflows/deploy.yml`](file:///Users/mpb/WorkSpace/golden-moment-predictor/.github/workflows/deploy.yml)

**Step 1: 在 L63-64 之间插入新步骤**

```yaml
      - name: Build frontend
        run: npm run build
        working-directory: frontend

      # ── 新增步骤 ──
      - name: Install fonts for screenshot
        run: |
          sudo apt-get update
          sudo apt-get install -y fonts-noto-cjk fonts-noto-color-emoji

      - name: Generate poster screenshots and summaries
        run: |
          npx playwright install --with-deps chromium
          node scripts/generate-posters.mjs
        working-directory: frontend
      # ── 新增结束 ──

      - name: Deploy to Cloudflare Pages
```

**Step 2: 验证 YAML 语法**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))" && echo "YAML OK"`

Expected: `YAML OK`

**Step 3: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add poster screenshot generation step to deploy workflow"
```

---

### Task 2: 本地端到端验证

**Step 1: 构建 + 生成**

```bash
cd frontend && npm run build && node scripts/generate-posters.mjs
```

**Step 2: 检查产物**

```bash
ls frontend/dist/data/posters/3day/   # 应有 7 张 PNG
ls frontend/dist/data/posters/week/   # 应有 7 张 PNG
cat frontend/dist/data/posters/summary_3day.json | python3 -m json.tool | head -10
cat frontend/dist/data/posters/summary_week.json | python3 -m json.tool | head -10
```

**Step 3: 验证 JSON 日期范围**

- `summary_3day.json` 的 `适用日期` 应从明天起 3 天
- `summary_week.json` 的 `适用日期` 应从明天起 7 天

---

### Task 3: 浏览器验证

使用浏览器 agent 完成：

1. 启动 `cd frontend && npm run dev`
2. 访问 `/ops/poster?days=3` — 验证表格从明天起 3 天、选择器只有 3/7、无导出按钮
3. 访问 `/ops/poster?days=7` — 验证默认 7 天
4. 视觉比对 Playwright 截图与 [`posters_20260226/`](file:///Users/mpb/WorkSpace/golden-moment-predictor/posters_20260226) 基准图片（色阶、字体、emoji、布局）

---

## 验证计划

### 完整回归测试
```bash
cd frontend && npx vitest run    # 全部单测
cd frontend && npm run build     # 构建
```

### 集成测试
```bash
cd frontend && node scripts/generate-posters.mjs
# 验证 14 PNG + 2 JSON
```

### 浏览器验证
- 页面 `/ops/poster?days=3` 和 `/ops/poster?days=7` 表现正确
- 截图与基准图片风格一致
