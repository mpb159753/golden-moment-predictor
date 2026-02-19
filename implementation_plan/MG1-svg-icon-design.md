# MG1 — SVG 景观图标设计与绘制

## 背景

GMP（Golden Moment Predictor）是一个川西旅行景观预测系统，前端展示各观景台（如牛背山、红石滩等）的景观预测评分（0-100）。地图 Marker 和卡片上需要用**图标徽章**来区分"这个高分来自什么景观"，让用户一眼辨别。

### 核心需求

用户在地图上看到两个同样 80 分的景点时，需要通过图标来区分：
- 景点 A：80 分 + 🏔️ 金山图标 → "有日照金山，优先去"
- 景点 B：80 分 + ☀️ 晴天图标 → "天气不错，但没有特殊景观"

### 当前状态

前端已有 7 个 SVG 图标文件，但**全部是占位符**（只是一个圆圈+汉字）：

```
frontend/src/assets/icons/
├── cloud-sea.svg              ← 占位符
├── frost.svg                  ← 占位符
├── ice-icicle.svg             ← 占位符
├── snow-tree.svg              ← 占位符
├── stargazing.svg             ← 占位符
├── sunrise-golden-mountain.svg ← 占位符
└── sunset-golden-mountain.svg  ← 占位符
```

占位符示例（每个文件结构相同）：
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
     fill="none" stroke="currentColor" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round">
  <!-- TODO: 替换为正式图标 — 见上方设计要求 -->
  <circle cx="12" cy="12" r="10" />
  <text x="12" y="16" text-anchor="middle" font-size="10"
        fill="currentColor" stroke="none">日</text>
</svg>
```

## 设计改动

### 需要新增的图标

除了替换现有 7 个占位符之外，还需要**新增 1 个**图标：

| 文件名 | 状态 |
|--------|------|
| `clear-sky.svg` | **[NEW]** 新增，对应新的 `clear_sky` 事件 |

### 图标分组方案

为减少用户理解成本，**部分事件共用同一图标**。共 5 组图标：

| 组名 | 对应事件(event_type) | SVG 文件 | 设计方向 |
|------|---------------------|----------|---------|
| **晴天** | `clear_sky` | `clear-sky.svg` | 太阳：简洁圆形 + 放射光芒线 |
| **金山** | `sunrise_golden_mountain`, `sunset_golden_mountain` | `sunrise-golden-mountain.svg`, `sunset-golden-mountain.svg` | 山峰轮廓 + 金色光晕。**两个文件使用相同图标**，不需要区分日出和日落 |
| **云海** | `cloud_sea` | `cloud-sea.svg` | 山峰**露出云层之上**的剪影。注意必须区别于阴天/多云（天气图标中"头顶乌云"） |
| **观星** | `stargazing` | `stargazing.svg` | 月牙 + 星星组合，表达暗夜星空 |
| **冰晶** | `frost`, `snow_tree`, `ice_icicle` | `frost.svg`, `snow-tree.svg`, `ice-icicle.svg` | 六角冰晶 / 树枝上的冰晶抽象图形。**三个文件使用相同图标**。注意：必须与"下雪"天气图标（雪花❄️飘落感）有视觉区分 |

> **关键区分点：**
> - 冰晶图标 ≠ 下雪天气：冰晶强调"晶莹附着在物体上"，下雪强调"雪花从天飘落"
> - 云海图标 ≠ 阴天天气：云海强调"站在高处俯瞰下方的壮观云层"，阴天强调"头顶乌云密布"

## 技术规范

### SVG 格式要求

```svg
<svg xmlns="http://www.w3.org/2000/svg"
     width="24" height="24"
     viewBox="0 0 24 24"
     fill="none"
     stroke="currentColor"
     stroke-width="2"
     stroke-linecap="round"
     stroke-linejoin="round">
  <!-- 图标路径 -->
</svg>
```

- **ViewBox**: `0 0 24 24`（24×24 基准网格）
- **Stroke**: 使用 `currentColor`（支持前端通过 CSS `color` 属性动态改色）
- **Fill**: 默认 `none`（纯线条风格），特殊元素（如太阳圆心、星星）可使用 `currentColor` 填充
- **Stroke-width**: 默认 `2`（与 Lucide Icons 一致）
- **不使用任何硬编码颜色**：前端通过 CSS `color` 属性控制颜色
- **无 `<text>` 元素**：不使用文字，纯图形

### 视觉风格

- **线条风格**：单色线条图标，参考 [Lucide Icons](https://lucide.dev/) 和 [Tabler Icons](https://tabler.io/icons) 的风格
- **简洁清晰**：16×16 缩放后仍可辨识（用于地图 Marker 徽章）
- **一致性**：所有图标使用相同的线条粗细（stroke-width: 2）、圆角风格（round caps/joins）

### 使用尺寸

前端会在三种场景使用这些图标：
- **16×16**：地图 Marker 上的徽章图标（最小，必须清晰可辨）
- **24×24**：事件卡片内的图标（标准尺寸）
- **32×32**：详情页的图标（最大尺寸）

SVG 的 viewBox 是 24×24，前端通过 CSS width/height 缩放，无需提供多尺寸版本。

### 前端集成方式

图标通过 `EventIcon.vue` 组件加载，位于 [EventIcon.vue](file:///Users/mpb/WorkSpace/golden-moment-predictor/frontend/src/components/event/EventIcon.vue)：

```js
// 现有的映射关系（需要在 MG2 计划中新增 clear_sky）
const EVENT_CONFIG = {
  sunrise_golden_mountain: { color: '#FF8C00', name: '日出金山', icon: SunriseGoldenMountain },
  sunset_golden_mountain:  { color: '#FF4500', name: '日落金山', icon: SunsetGoldenMountain },
  cloud_sea:               { color: '#87CEEB', name: '云海',     icon: CloudSea },
  stargazing:              { color: '#4A0E8F', name: '观星',     icon: Stargazing },
  frost:                   { color: '#B0E0E6', name: '雾凇',     icon: Frost },
  snow_tree:               { color: '#E0E8EF', name: '树挂积雪', icon: SnowTree },
  ice_icicle:              { color: '#ADD8E6', name: '冰挂',     icon: IceIcicle },
}
```

## 交付物

### 需要修改的文件

| 文件 | 操作 |
|------|------|
| `frontend/src/assets/icons/clear-sky.svg` | **[NEW]** 新增 |
| `frontend/src/assets/icons/sunrise-golden-mountain.svg` | **[MODIFY]** 替换占位符 |
| `frontend/src/assets/icons/sunset-golden-mountain.svg` | **[MODIFY]** 替换占位符（与 sunrise 相同内容） |
| `frontend/src/assets/icons/cloud-sea.svg` | **[MODIFY]** 替换占位符 |
| `frontend/src/assets/icons/stargazing.svg` | **[MODIFY]** 替换占位符 |
| `frontend/src/assets/icons/frost.svg` | **[MODIFY]** 替换占位符 |
| `frontend/src/assets/icons/snow-tree.svg` | **[MODIFY]** 替换占位符（与 frost 相同内容） |
| `frontend/src/assets/icons/ice-icicle.svg` | **[MODIFY]** 替换占位符（与 frost 相同内容） |

### 每个图标的设计描述

#### 1. 晴天 `clear-sky.svg`

**语义**：好天气，晴朗，很适合出行
**元素**：一个太阳——中心圆形 + 周围均匀分布的 8 条短放射线
**参考**：Lucide `sun` 图标，但稍作简化（减少光芒线至 6-8 条）
**区分**：这是"值得出门的好天气"，不是"高温警告"

#### 2. 金山 `sunrise-golden-mountain.svg` / `sunset-golden-mountain.svg`

**语义**：日照金山——阳光照射在雪山山顶呈现金色光芒
**元素**：
- 底部：两座山峰轮廓线（一高一低，呈 M 或 V 形）
- 山峰顶部：半圆弧或光晕弧线，表示阳光照射在山顶
- 可选：山峰顶部 2-3 条短光芒线
**注意**：两个文件使用**完全相同**的图标内容
**区分**：重点在"光照在山上"而非太阳本身

#### 3. 云海 `cloud-sea.svg`

**语义**：站在高处俯瞰壮观的云层，山峰穿透云层之上
**元素**：
- 上部：一个或两个山峰的尖顶（简洁三角形或折线）
- 下部：2-3 条柔和的波浪曲线，表示云海在山峰下方延展
**区分**：
- ≠ 阴天（乌云压在头顶）：云海的云在**脚下**，山峰在**云上方**
- 构图关键：山**高于**云

#### 4. 观星 `stargazing.svg`

**语义**：暗夜适合观星，星空条件好
**元素**：
- 一弯月牙（细月牙弧线，不要太大）
- 2-3 颗大小不一的星星（十字星/四角星形状）
**注意**：星星不要用五角星，用简洁的十字交叉线即可
**参考**：Lucide `moon-star` 类似思路

#### 5. 冰晶 `frost.svg` / `snow-tree.svg` / `ice-icicle.svg`

**语义**：冰雪景观——雾凇、雪挂树、冰挂（晶莹剔透附着在物体上的冰晶）
**元素**：
- 一个六角对称的冰晶图案（类似雪花但更"几何化/晶体化"）
- 或者：一段简洁的树枝轮廓，上面有几个小冰晶/冰珠附着
**区分**：
- ≠ 下雪天气（雪花从天飘落）：冰晶强调"生长/附着"在物体表面
- 雪花天气图标通常是："一片雪花 + 飘落动态感"
- 冰晶图标应该是："固定的、精致的晶体结构"
**注意**：三个文件使用**完全相同**的图标内容

## 验证方法

1. 将 SVG 文件写入后，在浏览器中打开每个 SVG 文件确认渲染正确
2. 在 16×16、24×24、32×32 三种尺寸下验证可辨识度
3. 确认 `currentColor` 正常工作（通过父元素 `color` 属性改变颜色）
4. 确认无硬编码颜色值

---

*文档版本: v1.0 | 创建: 2026-02-19 | 关联: 前端信息架构重构*
