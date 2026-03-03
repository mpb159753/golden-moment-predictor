# 景点分组重组与景区标识增强

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 48 个 viewpoint 按"旅行走廊"逻辑重新分组，消除 `other` 垃圾桶分组，并为每个观景点增加景区归属标识，使 poster 呈现清晰直观。同步清理所有 viewpoint 的文件名和 `id` 字段，统一命名规范。

**Architecture:** (1) 统一 viewpoint 文件名/ID 命名规范，清除 `transit_`、误导性前缀；(2) 在 viewpoint YAML 中新增 `scenic_area` 字段；(3) 重新划分 `groups` 为 8 个旅行走廊分组；(4) `poster_generator.py` 更新 `GROUP_META` + 展示名拼接；(5) 同步更新前端截图脚本和下载工作流。

**Tech Stack:** Python (dataclass + YAML) / Node.js (mjs) / Vue.js

---

## 背景

当前 viewpoint 配置使用 `groups` 字段按"山系"分组（如 `gongga`、`siguniang`），无法归入已有山系的景点统一放入 `other`（"其它景区"）。这导致：

- **11 个景点被归入"其它景区"**，分属毕棚沟、达古冰川、九寨沟、莲宝叶则等完全不同的景区，用户无法定位
- **观景点名缺少景区上下文**：如"红杉林主机位"无法让用户知道这是神木垒的景点
- **分组与旅行走廊不匹配**：如 318 沿途的新都桥、甲根坝实际看贡嘎主峰，与贡嘎山系是同一旅行走廊；木雅金塔、墨石公园实际看亚拉神山，与雅拉是同一方向

## 设计方案

### 1. YAML 配置变更：新增 `scenic_area` 字段

为需要景区标识的 viewpoint 新增可选字段 `scenic_area`：

```yaml
# config/viewpoints/shenmulei_redwood_view.yaml (变更前)
id: shenmulei_redwood_view
name: 红杉林主机位
groups:
  - other

# config/viewpoints/shenmulei_redwood_view.yaml (变更后)
id: shenmulei_redwood_view
name: 红杉林主机位
scenic_area: 神木垒          # 新增
groups:
  - other                    # 保留在 other（待后续扩充时再调整）
```

**规则**：
- `scenic_area` 为可选字段，默认为空字符串
- 当 group 的中文名已能清晰定位景区时（如"四姑娘山"→长坪沟），`scenic_area` 可不填
- 当观景点名本身不足以定位（如"磐羊湖"、"红杉林主机位"、"异域星球观景位"），必须填写 `scenic_area`

### 2. Viewpoint 文件名与 ID 命名规范（彻底清理）

**统一命名规则：** `<景区拼音缩写>_<地点描述>` + 可选 `_view` / `_pass` / `_camp` 后缀。去除所有代表「沿途过路点」的 `transit_` 前缀，因为现在 group 已经承担了方向信息，ID 只需反映景区和具体地点。

**需要重命名的文件（10 个 `transit_*`）：**

| 原文件名 | 新文件名 | 原 `id` | 新 `id` | 新 group |
|---|---|---|---|---|
| `transit_xinduqiao_view.yaml` | `xinduqiao_view.yaml` | `transit_xinduqiao_view` | `xinduqiao_view` | `gongga` |
| `transit_jiagenba_view.yaml` | `jiagenba_view.yaml` | `transit_jiagenba_view` | `jiagenba_view` | `gongga` |
| `transit_zheduoshan_pass.yaml` | `zheduoshan_pass.yaml` | `transit_zheduoshan_pass` | `zheduoshan_pass` | `gongga` |
| `transit_gaoersi_pass.yaml` | `gaoersi_pass.yaml` | `transit_gaoersi_pass` | `gaoersi_pass` | `318` |
| `transit_jianziwan_pass.yaml` | `jianziwan_pass.yaml` | `transit_jianziwan_pass` | `jianziwan_pass` | `318` |
| `transit_kazila_pass.yaml` | `kazila_pass.yaml` | `transit_kazila_pass` | `kazila_pass` | `318` |
| `transit_18bends_view.yaml` | `haizishaner_18bends.yaml` | `transit_18bends_view` | `haizishaner_18bends` | `318` |
| `transit_daerpu_valley.yaml` | `daerpu_view.yaml` | `transit_daerpu_valley` | `daerpu_view` | `siguniang` |
| `transit_lixiao_redstone.yaml` | `lixiao_redstone.yaml` | `transit_lixiao_redstone` | `lixiao_redstone` | `siguniang` |
| `transit_lixiao_tunnel_view.yaml` | `lixiao_tunnel_view.yaml` | `transit_lixiao_tunnel_view` | `lixiao_tunnel_view` | `siguniang` |
| `gongga_lenggacuo.yaml` | `lenggacuo.yaml` | `gongga_lenggacuo` | `lenggacuo` | `gongga` |
| `gongga_yaha_pass.yaml` | `yaha_pass.yaml` | `gongga_yaha_pass` | `yaha_pass` | `gongga` |
| `gongga_yuzixi.yaml` | `yuzixi.yaml` | `gongga_yuzixi` | `yuzixi` | `gongga` |
| `gongga_zimei_pass.yaml` | `zimei_pass.yaml` | `gongga_zimei_pass` | `zimei_pass` | `gongga` |
| `niubei.yaml` | `niubei.yaml` | `niubei` | `niubei` | `gongga` |
| `zheduo.yaml` | `zheduo.yaml` | `zheduo` | `zheduo` | `gongga` |
| `duoraogamu_yala_view.yaml` | `duoraogamu_view.yaml` | `duoraogamu_yala_view` | `duoraogamu_view` | `yala` |

**保持不变的文件（31 个）：**

`siguniang_changping`、`siguniang_shuangqiao`、`siguniang_erguniang_view`、`siguniang_haizi_chaoshanping`、`siguniang_maobiliang`、`genie_eye`、`genie_chachongxi`、`genie_laolenggusi`、`genie_nuda_camp`、`genie_xiazetong`、`yala_gedilamu`、`yala_gunong`、`yala_balangshengdu`、`yala_tagong_view`、`yala_yunrao_view`、`yading_five_color_lake`、`yading_luorong_pasture`、`yading_milk_lake`、`yading_pearl_lake`、`yading_echushan_view`、`bipenggou_panyang`、`dagu_4860`、`jiuzhai_wuhuahai`、`lianbaoyeze_zhagaer`、`majiagou_main_view`、`mengtun_gaoqiaogou`、`moshi_main_view`、`shenmulei_redwood_view`、`tagong_muya`、`zhagushan_pass`、`guergou_hot_spring_view`

> [!WARNING]
> **高引用 ID 重命名影响：**
> - `niubei` → `niubei`：**40+ 处引用**（`test_backtester.py` 19 处、`test_e2e_real_api.py` 15 处、`test_cli.py` 8 处、`test_poster_generator.py` 3 处等）
> - `zheduo` → `zheduo`：**30+ 处引用**（`test_forecast_reporter.py` 5 处、`test_route_config.py` 3 处、前端测试 6 处、`config/routes/lixiao.yaml` 1 处、`README.md` 4 处）
>
> Task 0 中需要用 `sed` 批量替换，并同步更新 `config/routes/lixiao.yaml`、`README.md`、`docs/`。

**Route 文件影响：**

`config/routes/lixiao.yaml` 中 `viewpoint_id: zheduo` → 改为 `viewpoint_id: zheduo`

**不涉及的文件：** `transit_*` 系列没有被测试文件硬编码引用，10 个 transit_* 重命名**无需修改任何测试文件**。

### 3. 全局分组重组

将 48 个 viewpoint 从当前 7 组重新分配为 8 组。以下列出所有变更：

#### 保持不变的分组

| 分组 key | 中文名 | 包含景点（不变） | 点位数 |
|---|---|---|---|
| `genie` | 格聂山系 | 格聂之眼、查冲西、老冷古寺、努达营地、下则通 | 5 |
| `yading` | 亚丁景区 | 五色海、洛绒牛场、牛奶海、珍珠海、俄初山 | 5 |

#### 合并扩充的分组

| 分组 key | 中文名 | 变更内容 | 新点位数 |
|---|---|---|---|
| `gongga` | 贡嘎山系 | + 从 `318` 合入：新都桥(`transit_xinduqiao_view`)、甲根坝(`transit_jiagenba_view`)、折多山垭口(`transit_zheduoshan_pass`) | 6→9 |
| `siguniang` | 四姑娘山方向 | + 从 `lixiao` 合入全部 2 个点；+ 从 `318` 合入：大二普(`transit_daerpu_valley`)；+ 从 `other` 合入：毕棚沟·磐羊湖(`bipenggou_panyang`)、孟屯·高桥沟(`mengtun_gaoqiaogou`) | 5→10 |
| `yala` | 塔公·雅拉方向 | + 从 `other` 合入：木雅金塔(`tagong_muya`)、墨石公园(`moshi_main_view`) | 6→8 |

> [!IMPORTANT]
> `zheduo`（折多山，当前 gongga 组）和 `transit_zheduoshan_pass`（折多山垭口，当前 318 组）是**同一地点的两套配置**。合并后需评估是否去重。本次方案暂保留两套，因为它们的 `capabilities` 列表不同。

#### 缩小的分组

| 分组 key | 中文名 | 变更内容 | 新点位数 |
|---|---|---|---|
| `318` | 318 理塘段 | 移出新都桥、甲根坝、折多山垭口（→贡嘎）、大二普（→四姑娘） | 8→4 |

#### 废弃的分组

| 分组 key | 原中文名 | 处理 |
|---|---|---|
| `lixiao` | 理小路沿途 | 全部 2 个点并入四姑娘山方向，key 废弃 |

#### 新增的分组

| 分组 key | 中文名 | 包含景点 | 点位数 |
|---|---|---|---|
| `aba` | 阿坝方向 | 达古·4860(`dagu_4860`)、鹧鸪沟·温泉(`guergou_hot_spring_view`)、鹧鸪山垭口(`zhagushan_pass`)、九寨·五花海(`jiuzhai_wuhuahai`)、莲宝叶则·扎尕尔措(`lianbaoyeze_zhagaer`) | 5 |

#### 保留在 other 的分组

| 分组 key | 中文名 | 包含景点 | 点位数 |
|---|---|---|---|
| `other` | 其他景区 | 神木垒·红杉林(`shenmulei_redwood_view`)、玛嘉沟·主沟(`majiagou_main_view`) | 2 |

> [!NOTE]
> `majiagou_main_view` 的 `name` 字段需从"主沟观景点"改为更准确的名称（如"主沟观景点"不变，但配合 `scenic_area: 玛嘉沟` 使用）。

### 4. 需要添加/更新的 viewpoint 配置汇总

以下为所有需要修改 YAML 的 viewpoint（含新 ID、新 group、新 scenic_area）：

| 新 `id`（旧 id） | name | scenic_area | 新 groups |
|---|---|---|---|
| `bipenggou_panyang`（不变） | 磐羊湖 | 毕棚沟 | `[siguniang]` |
| `mengtun_gaoqiaogou`（不变） | 高桥沟 | 孟屯河谷 | `[siguniang]` |
| `xinduqiao_view`（原 `transit_xinduqiao_view`） | 新都桥镇外机位 | 新都桥 | `[gongga]` |
| `jiagenba_view`（原 `transit_jiagenba_view`） | 甲根坝机位 | 甲根坝 | `[gongga]` |
| `zheduoshan_pass`（原 `transit_zheduoshan_pass`） | 折多山垭口 | 折多山 | `[gongga]` |
| `gaoersi_pass`（原 `transit_gaoersi_pass`） | 高尔寺垭口 | 高尔寺山 | `[318]` |
| `jianziwan_pass`（原 `transit_jianziwan_pass`） | 剪子弯山垭口 | 剪子弯山 | `[318]` |
| `kazila_pass`（原 `transit_kazila_pass`） | 卡子拉山垭口 | 卡子拉山 | `[318]` |
| `haizishaner_18bends`（原 `transit_18bends_view`） | 天路十八弯观景台 | 海子山 | `[318]` |
| `daerpu_view`（原 `transit_daerpu_valley`） | 大二普 | 大二普 | `[siguniang]` |
| `lixiao_redstone`（原 `transit_lixiao_redstone`） | 理小路红石滩（凉台沟） | 理小路 | `[siguniang]` |
| `lixiao_tunnel_view`（原 `transit_lixiao_tunnel_view`） | 理小隧道口观景台 | 理小路 | `[siguniang]` |
| `tagong_muya`（不变） | 木雅金塔机位 | 塔公草原 | `[yala]` |
| `moshi_main_view`（不变） | 异域星球观景位 | 墨石公园 | `[yala]` |
| `dagu_4860`（不变） | 4860观景台 | 达古冰川 | `[aba]` |
| `guergou_hot_spring_view`（不变） | 河谷温泉机位 | 鹧鸪沟 | `[aba]` |
| `zhagushan_pass`（不变） | 鹧鸪山垭口机位 | 鹧鸪山 | `[aba]` |
| `jiuzhai_wuhuahai`（不变） | 五花海 | 九寨沟 | `[aba]` |
| `lianbaoyeze_zhagaer`（不变） | 扎尕尔措 | 莲宝叶则 | `[aba]` |
| `shenmulei_redwood_view`（不变） | 红杉林主机位 | 神木垒 | `[other]`（不变） |
| `majiagou_main_view`（不变） | 主沟观景点 | 玛嘉沟 | `[other]`（不变） |

### 4. 代码变更

#### 4.1 数据模型 — `gmp/core/models.py`

`Viewpoint` dataclass 新增 `scenic_area` 字段：

```python
@dataclass
class Viewpoint:
    id: str
    name: str
    location: Location
    capabilities: list[str]
    targets: list[Target]
    groups: list[str] = field(default_factory=list)
    scenic_area: str = ""  # 新增：景区归属（如 "神木垒"）
```

#### 4.2 配置加载 — `gmp/core/config_loader.py`

`ViewpointConfig.load()` 中解析 `scenic_area`：

```python
vp = Viewpoint(
    id=data["id"],
    name=data["name"],
    location=location,
    capabilities=data.get("capabilities", []),
    targets=targets,
    groups=data.get("groups", []),
    scenic_area=data.get("scenic_area", ""),  # 新增
)
```

#### 4.3 Poster 生成 — `gmp/output/poster_generator.py`

**GROUP_META 更新**：

```python
GROUP_META: dict[str, dict] = {
    "gongga": {"name": "贡嘎山系", "order": 1},
    "siguniang": {"name": "四姑娘山方向", "order": 2},
    "yala": {"name": "塔公·雅拉方向", "order": 3},
    "genie": {"name": "格聂山系", "order": 4},
    "yading": {"name": "亚丁景区", "order": 5},
    "318": {"name": "318 理塘段", "order": 6},
    "aba": {"name": "阿坝方向", "order": 7},       # 新增
    "other": {"name": "其他景区", "order": 8},
    # lixiao 已废弃，不再列出
}
```

**Viewpoint 展示名拼接景区前缀**：

在 `generate()` 中构建 `viewpoints_data` 时，拼接 `scenic_area`：

```python
for vp in vps:
    daily = self._build_daily(vp.id, date_list)
    display_name = f"{vp.scenic_area}·{vp.name}" if vp.scenic_area else vp.name
    viewpoints_data.append({
        "id": vp.id,
        "name": display_name,
        "daily": daily,
    })
```

这样 poster.json 中的景点名会变为 `"神木垒·红杉林主机位"`、`"毕棚沟·磐羊湖"` 等。

#### 4.4 前端截图脚本 — `frontend/scripts/generate-posters.mjs`

当前 `GROUP_KEYS` 硬编码按索引映射文件名，极其脆弱。改为从 poster.json 的 `groups[].key` 动态读取：

```javascript
// 变更前（L11）
const GROUP_KEYS = ['gongga', 'siguniang', 'yala', 'genie', 'yading', 'lixiao', 'other']

// 变更后：动态从 poster.json 读取
// 删除 GROUP_KEYS 硬编码
// L54-55 改为：
for (let i = 0; i < sections.length; i++) {
    const key = posterData.groups[i]?.key || `group_${i}`
    // ...
}
```

需要在截图前读取 `poster.json` 获取 group keys。

#### 4.5 下载工作流 — `.agent/workflows/download-posters.md`

更新 group key 列表：

```bash
# 变更前
for name in gongga siguniang yala genie yading lixiao other; do

# 变更后
for name in gongga siguniang yala genie yading 318 aba other; do
```

同步更新文件数量说明和验证步骤中的预期分组数。

#### 4.6 Summary 生成 — `frontend/scripts/build-summary.mjs`

**无需代码改动**。`buildSummary()` 使用 `group.name` 作为"区域"标签，而 `group.name` 来自 poster.json，已由 `poster_generator.py` 的 `GROUP_META` 控制。分组重组后，summary 中的"区域"字段会自动变为新的中文名。

同样，viewpoint 的 `点位` 字段使用 `vp.name`，在 poster_generator.py 中拼接了景区前缀后会自动生效。

### 5. 完整变更影响图

```
① 文件重命名（10 个 transit_* → 新名）
config/viewpoints/transit_*.yaml  → 重命名为新文件名，内部 id 字段同步更新
        ↓
② YAML 内容更新（21 个文件：修改 groups + 新增 scenic_area）
config/viewpoints/*.yaml
        ↓
③ 数据模型 + 配置加载
gmp/core/models.py                ← Viewpoint 新增 scenic_area 字段
gmp/core/config_loader.py         ← 解析 scenic_area
        ↓
④ Poster 生成
gmp/output/poster_generator.py    ← GROUP_META 更新 + 展示名拼接
        ↓
poster.json                       → 新的分组结构 + 带景区前缀的景点名
        ↓
⑤ 前端 + 工作流
┌─────────────────────────────────────────────────┐
│ frontend/scripts/generate-posters.mjs           │ ← 动态读取 group key
│ frontend/scripts/build-summary.mjs              │ ← 无需改动（自动继承）
│ .agent/workflows/download-posters.md            │ ← 更新 group key 列表
│ config/routes/*.yaml                            │ ← 无需改动（引用的 ID 不变）
└─────────────────────────────────────────────────┘
        ↓
⑥ 测试
tests/unit/test_poster_generator.py               ← 更新 mock viewpoint（加 scenic_area 属性）
tests/unit/test_config_loader.py                  ← 无需改动
tests/integration/test_config_consistency.py      ← 可能需适配新分组 key
frontend/scripts/__tests__/generate-posters.test.mjs ← 更新测试数据
```

---

## 验证计划

### 自动测试

**1. Python 单元测试**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor
source venv/bin/activate
pytest tests/unit/test_poster_generator.py -v
pytest tests/unit/test_config_loader.py -v
```

需更新 `test_poster_generator.py` 中使用 `other` 和 `gongga` group 的 mock viewpoint，以及新增 `scenic_area` 展示名拼接的测试用例。

**2. 配置一致性测试**

```bash
pytest tests/integration/test_config_consistency.py -v
```

验证所有 viewpoint YAML 的 `groups` 值都在 `GROUP_META` 中有对应条目。

**3. 前端测试**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/frontend
npm test -- --run
```

### 手动验证

**4. Poster 预览**

- 启动前端 dev server：`cd frontend && npm run dev`
- 访问 `/ops/poster?days=3`
- 确认："其他景区"只剩 2 个点位（神木垒·红杉林主机位、玛嘉沟·主沟观景点）
- 确认："阿坝方向"出现并包含 5 个带景区前缀的点位
- 确认："四姑娘山方向"包含新合入的理小路、毕棚沟等点位
- 确认："贡嘎山系"包含新合入的新都桥、甲根坝等点位
- 确认："塔公·雅拉方向"包含木雅金塔、墨石公园

---

## 任务分解

### Task 0: Viewpoint 文件名与 ID 重命名

**Files:**
- Rename + Modify: `config/viewpoints/` 下 17 个文件（重命名 + 修改内部 `id` 字段）
- Modify: `config/routes/lixiao.yaml`（更新 `zheduo` → `zheduo`）
- Batch update tests + docs（`sed` 批量替换高引用 ID）

**Step 1:** 重命名 10 个 `transit_*` 文件

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/config/viewpoints
git mv transit_xinduqiao_view.yaml xinduqiao_view.yaml
git mv transit_jiagenba_view.yaml jiagenba_view.yaml
git mv transit_zheduoshan_pass.yaml zheduoshan_pass.yaml
git mv transit_gaoersi_pass.yaml gaoersi_pass.yaml
git mv transit_jianziwan_pass.yaml jianziwan_pass.yaml
git mv transit_kazila_pass.yaml kazila_pass.yaml
git mv transit_18bends_view.yaml haizishaner_18bends.yaml
git mv transit_daerpu_valley.yaml daerpu_view.yaml
git mv transit_lixiao_redstone.yaml lixiao_redstone.yaml
git mv transit_lixiao_tunnel_view.yaml lixiao_tunnel_view.yaml
```

**Step 2:** 重命名 7 个 `gongga_*` / 其他文件

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor/config/viewpoints
git mv gongga_lenggacuo.yaml lenggacuo.yaml
git mv gongga_yaha_pass.yaml yaha_pass.yaml
git mv gongga_yuzixi.yaml yuzixi.yaml
git mv gongga_zimei_pass.yaml zimei_pass.yaml
git mv niubei.yaml niubei.yaml
git mv zheduo.yaml zheduo.yaml
git mv duoraogamu_yala_view.yaml duoraogamu_view.yaml
```

**Step 3:** 更新每个重命名文件内部的 `id:` 字段，与新文件名一致（无扩展名）

**Step 4:** 批量替换所有测试、文档、配置中的旧 ID

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor

# 高引用 ID：niubei → niubei
grep -rl "niubei" --include="*.py" --include="*.ts" --include="*.js" --include="*.yaml" --include="*.md" --include="*.json" . \
  | grep -v "config/viewpoints/" \
  | xargs sed -i '' 's/niubei/niubei/g'

# 高引用 ID：zheduo → zheduo
grep -rl "zheduo" --include="*.py" --include="*.ts" --include="*.js" --include="*.yaml" --include="*.md" --include="*.json" . \
  | grep -v "config/viewpoints/" \
  | xargs sed -i '' 's/zheduo/zheduo/g'

# 其他低引用旧 ID（如有）
sed -i '' 's/gongga_lenggacuo/lenggacuo/g; s/gongga_yaha_pass/yaha_pass/g; s/gongga_yuzixi/yuzixi/g; s/gongga_zimei_pass/zimei_pass/g; s/duoraogamu_yala_view/duoraogamu_view/g' \
  $(grep -rl "gongga_lenggacuo\|gongga_yaha_pass\|gongga_yuzixi\|gongga_zimei_pass\|duoraogamu_yala_view" --include="*.py" --include="*.md" . | grep -v "config/viewpoints/")
```

**Step 5:** 验证 id 与文件名全部一致：

```bash
python -c "
import yaml
from pathlib import Path
for f in sorted(Path('config/viewpoints').glob('*.yaml')):
    d = yaml.safe_load(f.read_text())
    assert d['id'] == f.stem, f'{f.name}: id={d[\"id\"]!r} 与文件名不符'
print('所有 id 与文件名一致 ✓')
"
```
Expected: `所有 id 与文件名一致 ✓`

**Step 6:** 运行单元测试确认无断裂

```bash
source venv/bin/activate
pytest tests/unit/ -x -q
```
Expected: all pass

**Step 7:** Commit `git commit -m "refactor: rename all viewpoints to scenic_area_location convention"`

### Task 1: YAML 内容变更（groups + scenic_area）

**Files:**
- Modify: `config/viewpoints/` 下 21 个 YAML 文件（按 §4 汇总表修改 `groups` + 添加 `scenic_area`）

**Step 1:** 按 §4「需要添加/更新的 viewpoint 配置汇总」表格，逐一修改 21 个 YAML 文件
**Step 2:** 验证所有 YAML 可解析：
```bash
python -c "import yaml; [yaml.safe_load(open(f)) for f in __import__('pathlib').Path('config/viewpoints').glob('*.yaml')]"
```
**Step 3:** Commit `git commit -m "config: regroup viewpoints by travel corridor, add scenic_area"`

### Task 2: 数据模型和配置加载

**Files:**
- Modify: `gmp/core/models.py:44-52`
- Modify: `gmp/core/config_loader.py:226-233`

**Step 1:** 在 `Viewpoint` dataclass 添加 `scenic_area: str = ""`
**Step 2:** 在 `config_loader.py` 的 `load()` 方法中添加 `scenic_area=data.get("scenic_area", "")`
**Step 3:** 运行测试 `pytest tests/unit/test_config_loader.py -v`
**Step 4:** Commit

### Task 3: Poster 生成器更新

**Files:**
- Modify: `gmp/output/poster_generator.py:20-29` (GROUP_META)
- Modify: `gmp/output/poster_generator.py:82-88` (展示名拼接)
- Modify: `tests/unit/test_poster_generator.py` (更新测试)

**Step 1:** 更新 `GROUP_META`（新增 `aba`，删除 `lixiao`，修改部分中文名）
**Step 2:** 在 `generate()` 中添加 `scenic_area` 前缀拼接逻辑
**Step 3:** 更新 `test_poster_generator.py`（mock viewpoint 添加 `scenic_area` 属性 + 新增展示名测试）
**Step 4:** 运行测试 `pytest tests/unit/test_poster_generator.py -v`
**Step 5:** Commit

### Task 4: 前端截图脚本更新

**Files:**
- Modify: `frontend/scripts/generate-posters.mjs:11,54-55`
- Modify: `.agent/workflows/download-posters.md`

**Step 1:** 删除 `GROUP_KEYS` 硬编码，改为从 posterData 动态读取 group key
**Step 2:** 更新 `download-posters.md` 中的 group key 列表
**Step 3:** 运行前端测试 `cd frontend && npm test -- --run`
**Step 4:** Commit

### Task 5: 集成验证

**Step 1:** 运行完整后端测试 `pytest tests/ -v`
**Step 2:** 运行完整前端测试 `cd frontend && npm test -- --run`
**Step 3:** 启动 dev server 手动验证 poster 页面
**Step 4:** Final commit + push
