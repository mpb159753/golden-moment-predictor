# 12. 小红书运营预测海报页面 — 设计文档

> **目标:** 为小红书运营提供一个隐藏的内部页面，以天气+景观事件矩阵表格的形式，展示所有景点未来 5 天的预测信息，支持一键导出为海报图片。

## 12.1 需求背景

小红书天气博主（如"川西超会玩ZD"、"川西天气小助手"）每日发布**按区域分组的多景点×多日天气预测矩阵表格**。这类内容虽然"粗糙"，但信息密度高，能让用户一图了解全局。

GMP 的差异化优势：除天气信息外，还能展示**景观事件评分**（日照金山、云海、雾凇等），这是竞品完全不具备的维度。

### 与现有 ShareCard 的关系

| | ShareCard | 海报页面 |
|--|-----------|---------|
| **定位** | 用户分享工具 | 运营发布工具 |
| **粒度** | 单景点单日 | 全景点多日 |
| **内容** | 详细评分+事件明细 | 天气摘要+景观亮点 |
| **路由** | 详情页内触发 | `/ops/poster` 隐藏路由 |

两者互补，不冲突。

---

## 12.2 设计决策

| 决策项 | 选定方案 |
|-------|---------|
| 信息维度 | **混合模式**：天气 + GMP 景观事件文字（如 `晴天+日照金山`） |
| 分组方式 | **按山系/景区**，沿途垭口按线路（318/理小路等）拆分 |
| 时间粒度 | **上午/下午** 两段 |
| 默认天数 | **5 天**（运营可调 3/5/7） |
| 格子内容 | 文字描述：天气+景观事件名（不用 emoji），如 `晴天+日照金山` |
| 格子背景色 | 按最佳事件分数着色：绿 ≥80 / 黄 50-79 / 橙 25-49 / 红 <25 |
| 访问方式 | 隐藏路由 `/ops/poster`，不在官网导航中露出 |

---

## 12.3 山系分组

| 组名 | 景点 ID | 数量 |
|------|---------|------|
| **贡嘎山系** | niubei_gongga, gongga_lenggacuo, gongga_yaha_pass, gongga_yuzixi, gongga_zimei_pass, zheduo_gongga | 6 |
| **四姑娘山** | siguniang_changping, siguniang_erguniang_view, siguniang_haizi_chaoshanping, siguniang_maobiliang, siguniang_shuangqiao | 5 |
| **雅拉山系** | yala_balangshengdu, yala_gedilamu, yala_gunong, yala_tagong_view, yala_yunrao_view, duoraogamu_yala_view | 6 |
| **格聂山系** | genie_chachongxi, genie_eye, genie_laolenggusi, genie_nuda_camp, genie_xiazetong | 5 |
| **亚丁景区** | yading_echushan_view, yading_five_color_lake, yading_luorong_pasture, yading_milk_lake, yading_pearl_lake | 5 |
| **318 沿途** | transit_gaoersi_pass, transit_zheduoshan_pass, transit_jianziwan_pass, transit_kazila_pass, transit_xinduqiao_view, transit_jiagenba_view, transit_18bends_view, transit_daerpu_valley | 8 |
| **理小路沿途** | transit_lixiao_redstone, transit_lixiao_tunnel_view | 2 |
| **其它景区** | jiuzhai_wuhuahai, lianbaoyeze_zhagaer, bipenggou_panyang, dagu_4860, guergou_hot_spring_view, majiagou_main_view, mengtun_gaoqiaogou, moshi_main_view, shenmulei_redwood_view, tagong_muya, zhagushan_pass | 11 |

> **配置方式:** 每个 viewpoint YAML 新增 `group` 字段（如 `group: gongga`），`poster.json` 生成时根据此字段分组。

---

## 12.4 表格布局

以贡嘎山系为例：

```
┌────────────┬────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│  贡嘎山系   │    │  2/21    │  2/22    │  2/23    │  2/24    │  2/25    │
├────────────┼────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│            │ 上午│ 晴天     │ 多云     │ 小雪     │ 阴天     │ 晴天     │
│  牛背山     │    │+日照金山 │          │+雾凇     │          │+日照金山 │
│            ├────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│            │ 下午│ 晴天     │ 多云     │ 小雪     │ 阴天     │ 晴天     │
│            │    │+云海     │          │+冰挂     │          │+云海     │
├────────────┼────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│            │ 上午│ 多云     │ 晴天     │ 阴天     │ 多云     │ 晴天     │
│  子梅垭口   │    │          │+日照金山 │          │          │+日照金山 │
│            ├────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│            │ 下午│ 多云     │ 晴天     │ 阴天     │ 多云     │ 晴天     │
│            │    │          │+云海     │          │          │          │
└────────────┴────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

### 格子内容规则

- **有推荐事件 (score ≥ 50)**：`天气+事件名`（如 `晴天+日照金山`）
- **无推荐事件**：仅显示天气（如 `阴天`）
- **多个推荐事件**：取分数最高的一个
- **上午事件归属**：日出金山、雾凇、树挂积雪、冰挂
- **下午事件归属**：日落金山、云海、观星（夜间归入下午列）

### 色块映射

| 最佳事件分数 | 背景色 | 含义 |
|------------|-------|------|
| ≥ 80 | 🟢 绿色 `#C6EFCE` | 强烈推荐 |
| 50-79 | 🟡 黄色 `#FFEB9C` | 值得关注 |
| 25-49 | 🟠 橙色 `#FFC7CE` | 条件一般 |
| < 25 或无事件 | 🔴 红色 `#F4CCCC` | 不推荐 |

---

## 12.5 数据流

### 后端：新增 poster.json

在 `generate-all` 命令中新增一个步骤，聚合所有景点数据生成 `poster.json`：

```json
{
  "generated_at": "2026-02-21T08:00:00+08:00",
  "days": ["2026-02-21", "2026-02-22", "2026-02-23", "2026-02-24", "2026-02-25"],
  "groups": [
    {
      "name": "贡嘎山系",
      "key": "gongga",
      "viewpoints": [
        {
          "id": "niubei_gongga",
          "name": "牛背山",
          "daily": [
            {
              "date": "2026-02-21",
              "am": { "weather": "晴天", "event": "日照金山", "score": 90 },
              "pm": { "weather": "晴天", "event": "云海", "score": 75 }
            }
          ]
        }
      ]
    }
  ]
}
```

### 天气映射规则

从 timeline 数据中取上午(6:00-12:00)/下午(12:00-18:00) 的天气代码，映射为中文：

| WMO WeatherCode | 中文 |
|-----------------|------|
| 0, 1 | 晴天 |
| 2 | 多云 |
| 3 | 阴天 |
| 45, 48 | 雾 |
| 51, 53, 55 | 小雨 |
| 61, 63 | 中雨 |
| 65, 67 | 大雨 |
| 71, 73 | 小雪 |
| 75, 77 | 大雪 |

---

## 12.6 前端页面

### 路由

```javascript
// router/index.js — 隐藏路由，不在导航中露出
{ path: '/ops/poster', component: () => import('@/views/PosterView.vue') }
```

### 页面结构

```
PosterView.vue
├── PosterHeader          标题 + 日期范围 + 天数切换 + 导出按钮
├── PredictionMatrix      山系分组表格（循环渲染每个组）
│   ├── GroupHeader        山系名称标题行
│   └── MatrixTable        表格主体（景点×日期×上下午）
└── PosterFooter          数据更新时间 + 品牌信息
```

### 导出功能

- **"一键导出全部"**：将每个山系分组分别截图为独立 PNG 图片（宽度 1080px）
- 每张图自带标题（山系名 + 日期范围）和页脚（品牌 + 更新时间）
- 复用现有 `useScreenshot` composable

### 运营工作流

```
CI/CD 每日自动生成数据并部署
→ 运营打开 /ops/poster
→ 确认数据OK → 点击"一键导出"
→ 下载图片 → 发小红书帖子
→ 全程 < 2 分钟
```

---

*文档版本: v1.0 | 创建: 2026-02-21 | 基于头脑风暴会话*
