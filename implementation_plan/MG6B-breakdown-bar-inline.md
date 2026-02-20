# MG6B: 前端 — 评分明细叠放柱状图

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 将事件卡片的评分明细从多行 `ScoreBar` 改为单行叠放柱状图 `BreakdownBar`，显著降低卡片高度，提升信息密度。

**依赖模块:** 无（纯前端组件改造）

---

## 背景

当前 [EventCard.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/event/EventCard.vue) 使用多个 [ScoreBar.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/score/ScoreBar.vue) 组件展示评分明细。每个 ScoreBar 占两行（标签行 + 进度条），一个有 3 个评分维度的事件要占 6+ 行。

设计文档 [§11.5 第④区域](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/11-frontend-architecture-v2.md) 描述的目标格式：

```
🏔️ 日落金山  90/100
  光路 30/35 | 目标 35/40 | 本地 25/25
```

优化方案：用一行叠放柱状图 + 维度标注，替代多行 ScoreBar。

```
评分明细
[光路 10 ][目标 10   ][本地 25        ]  45/100
 ████████░░░░░░░░░░████████████████████
```

### 当前 EventCard 评分明细模板

```html
<div class="event-card__breakdown" v-if="showBreakdown && event.score_breakdown">
  <div class="event-card__breakdown-title">评分明细</div>
  <ScoreBar
    v-for="(detail, key) in event.score_breakdown"
    :key="key"
    :label="breakdownLabel(key)"
    :score="detail.score"
    :max="detail.max"
  />
</div>
```

### 当前 breakdownLabelMap

```javascript
const breakdownLabelMap = {
  light_path: '光路通畅',
  target_visible: '目标可见',
  local_clear: '本地晴朗',
  temperature: '温度',
  moisture: '湿度',
  wind: '风力',
  cloud: '云量',
  base: '基础条件',
  gap: '海拔落差',
  density: '云层密度',
  mid_structure: '中层结构',
  cloud_cover: '云覆盖率',
  precipitation: '降水',
  visibility: '能见度',
  snow_signal: '积雪信号',
  clear_weather: '天气晴好',
  stability: '稳定性',
  water_input: '水源输入',
  freeze_strength: '冻结强度',
  view_quality: '观赏质量',
}
```

---

## Task 1: 新增 BreakdownBar 组件

**Files:**
- New: [BreakdownBar.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/score/BreakdownBar.vue)
- New: [BreakdownBar.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/components/BreakdownBar.test.js)

### 组件规格

**Props:**
- `breakdown: Object` — `{ key: { score: Number, max: Number } }`
- `labelMap: Object` — key → 中文简称映射
- `total: Number` — 可选，总分（默认从 breakdown 各项 max 累加）

**渲染逻辑:**
1. 遍历 breakdown 条目，按 key 顺序排列
2. 每段宽度 = `(item.max / totalMax) * 100%`（按满分占比分配宽度）
3. 每段内部填充比例 = `item.score / item.max`
4. 段内显示维度简称 + 分数（空间不足时省略文字）
5. 右侧显示总得分 / 总满分

**配色方案** — 使用 HSL 旋转生成不同维度的颜色：

```javascript
const segmentColors = [
  'hsl(210, 70%, 55%)',  // 蓝
  'hsl(150, 60%, 45%)',  // 绿
  'hsl(35, 85%, 55%)',   // 橙
  'hsl(280, 55%, 55%)',  // 紫
  'hsl(0, 65%, 55%)',    // 红
]
```

**模板示意:**

```html
<div class="breakdown-bar">
  <div class="breakdown-bar__track">
    <div
      v-for="(seg, idx) in segments"
      :key="seg.key"
      class="breakdown-bar__segment"
      :style="{ width: seg.widthPct + '%' }"
      :title="`${seg.label} ${seg.score}/${seg.max}`"
    >
      <div
        class="breakdown-bar__fill"
        :style="{ width: seg.fillPct + '%', backgroundColor: seg.color }"
      />
      <span v-if="seg.showLabel" class="breakdown-bar__label">
        {{ seg.label }} {{ seg.score }}
      </span>
    </div>
  </div>
  <span class="breakdown-bar__total">{{ totalScore }}/{{ totalMax }}</span>
</div>
```

**样式要点:**

```css
.breakdown-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breakdown-bar__track {
  flex: 1;
  display: flex;
  height: 20px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg-secondary, #F3F4F6);
}

.breakdown-bar__segment {
  position: relative;
  height: 100%;
  /* 段间加 1px 间隔 */
  border-right: 1px solid rgba(255, 255, 255, 0.3);
}

.breakdown-bar__fill {
  height: 100%;
  transition: width 0.6s var(--ease-out-expo);
}

.breakdown-bar__label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  white-space: nowrap;
  overflow: hidden;
}

.breakdown-bar__total {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
```

### 应测试的内容

- 渲染正确数量的段（与 breakdown 条目一致）
- 每段宽度比例正确（按 max 占比）
- 每段填充比例正确（score / max）
- 总分正确计算
- 段内标签显示维度名和分数
- 空 breakdown 时不渲染

---

## Task 2: EventCard 替换 ScoreBar 为 BreakdownBar

**Files:**
- Modify: [EventCard.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/event/EventCard.vue)
- Test: [BreakdownTable.test.js](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/__tests__/components/BreakdownTable.test.js)（如涉及）

### 修改内容

1. **替换 import**: `ScoreBar` → `BreakdownBar`
2. **简化 breakdownLabelMap** — 缩短维度名称以适应柱状图内显示：

```javascript
const breakdownLabelMap = {
  light_path: '光路',
  target_visible: '目标',
  local_clear: '本地',
  temperature: '温度',
  moisture: '湿度',
  wind: '风力',
  cloud: '云量',
  base: '基础',
  gap: '落差',
  density: '密度',
  mid_structure: '中层',
  cloud_cover: '云量',
  precipitation: '降水',
  visibility: '能见',
  snow_signal: '积雪',
  clear_weather: '晴好',
  stability: '稳定',
  water_input: '水源',
  freeze_strength: '冻结',
  view_quality: '观赏',
}
```

3. **替换模板**:

```html
<!-- 评分明细 (单行叠放柱状图) -->
<div class="event-card__breakdown" v-if="showBreakdown && event.score_breakdown">
  <div class="event-card__breakdown-title">评分明细</div>
  <BreakdownBar
    :breakdown="event.score_breakdown"
    :label-map="breakdownLabelMap"
  />
</div>
```

4. **移除 ScoreBar 相关**: 删除 `import ScoreBar` 和 `breakdownLabel()` 函数

---

## 验证命令

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend

# BreakdownBar 单元测试
npx vitest run src/__tests__/components/BreakdownBar.test.js --reporter verbose

# 全量回归
npx vitest run --reporter verbose
```

手动验证要点：
1. 事件卡片的评分明细变为一行叠放柱状图
2. 每段颜色不同，宽度按满分占比分配
3. 段内显示维度简称和分数
4. 右侧显示总得分

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: 设计文档 §11.5, EventCard.vue*
