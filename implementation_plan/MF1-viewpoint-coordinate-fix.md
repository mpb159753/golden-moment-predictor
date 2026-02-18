# 观景台坐标采集与修复 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 逐个在高德地图浏览器上确认全部 49 个观景台的精确 WGS-84 坐标，替换配置文件中错误的坐标，并更新前端静态数据。

**Architecture:** 使用浏览器打开高德地图网页 (amap.com)，逐个搜索每个观景台名称，在地图上定位到精确的观景机位/景点位置，记录 GCJ-02 坐标并转换为 WGS-84 后写入 YAML 配置文件。前端 `public/data/index.json` 由后端 `batch_generate` 命令自动生成，修改 YAML 后需重新生成。

**Tech Stack:** 高德地图网页版 (amap.com) · Python YAML · GCJ-02/WGS-84 坐标转换

---

## 背景

### 问题

配置文件中的 49 个观景台坐标几乎全部错误（偏差 3-60+ km），原因是原始数据由 AI 生成时未严格校验。使用高德 Web 服务 API 批量 POI 搜索验证后发现，48/49 个坐标偏差超过 1km。

### 坐标系说明

- **配置文件** (`config/viewpoints/*.yaml`) 存储 **WGS-84** 坐标（标准 GPS，Open-Meteo 天气 API 需要）
- **高德地图** (amap.com) 显示的是 **GCJ-02** 坐标（国测局坐标系）
- 从高德地图上读取的坐标需要做 **GCJ-02 → WGS-84 反转换** 后才能写入配置文件
- 前端已实现 WGS-84 → GCJ-02 自动转换 (`useCoordConvert.js`)

### GCJ-02 → WGS-84 转换工具

项目根目录已有转换脚本。也可以使用以下 Python 函数（精度约 1-2 米）：

```python
import math
PI = math.pi; A = 6378245.0; EE = 0.00669342162296594323

def _transform_lat(lng, lat):
    ret = -100.0+2.0*lng+3.0*lat+0.2*lat*lat+0.1*lng*lat+0.2*math.sqrt(abs(lng))
    ret += (20.0*math.sin(6.0*lng*PI)+20.0*math.sin(2.0*lng*PI))*2.0/3.0
    ret += (20.0*math.sin(lat*PI)+40.0*math.sin(lat/3.0*PI))*2.0/3.0
    ret += (160.0*math.sin(lat/12.0*PI)+320*math.sin(lat*PI/30.0))*2.0/3.0
    return ret

def _transform_lng(lng, lat):
    ret = 300.0+lng+2.0*lat+0.1*lng*lng+0.1*lng*lat+0.1*math.sqrt(abs(lng))
    ret += (20.0*math.sin(6.0*lng*PI)+20.0*math.sin(2.0*lng*PI))*2.0/3.0
    ret += (20.0*math.sin(lng*PI)+40.0*math.sin(lng/3.0*PI))*2.0/3.0
    ret += (150.0*math.sin(lng/12.0*PI)+300.0*math.sin(lng/30.0*PI))*2.0/3.0
    return ret

def gcj02_to_wgs84(gcj_lng, gcj_lat):
    dlat = _transform_lat(gcj_lng-105.0, gcj_lat-35.0)
    dlng = _transform_lng(gcj_lng-105.0, gcj_lat-35.0)
    radlat = gcj_lat/180.0*PI; magic = math.sin(radlat); magic = 1-EE*magic*magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat*180.0)/((A*(1-EE))/(magic*sqrtmagic)*PI)
    dlng = (dlng*180.0)/(A/sqrtmagic*math.cos(radlat)*PI)
    return round(gcj_lng-dlng, 6), round(gcj_lat-dlat, 6)
```

### 高德 Web 服务 API Key

`d13989c82f1d06d53a7662424c25348c`（Web 服务类型，可调用 POI 搜索、逆地理编码等 REST API）

### 采集方法

对每个观景台，执行以下流程：

1. **在高德地图 (amap.com) 搜索** 观景台名称
2. **在地图上放大** 到能看清道路/地标的级别
3. **确认位置** — 对于有明确地标的（如垭口、景区入口），直接取搜索结果坐标；对于摄影机位类的，需要在地图上找到对应的道路/山脊位置
4. **读取 GCJ-02 坐标** — 高德地图 URL 或点击位置即可获取
5. **转换为 WGS-84** — 使用上述 `gcj02_to_wgs84` 函数
6. **写入 YAML** — 更新 `lat` 和 `lon` 字段（保留 3-6 位小数）

> [!IMPORTANT]
> 高德 Web 服务 API（POI 搜索）也可以辅助获取坐标，但返回的是 **GCJ-02**，需要转换。
> 对于小众摄影机位（如"猫鼻梁"），POI 搜索结果可信度高；
> 对于"XX机位""XX观景位"这类名称，POI 可能找不到或匹配到酒店/停车场，需要在地图上人工确认。

---

## POI 参考数据

以下是高德 POI 搜索的参考结果。`poi_ref` 列是 POI 返回的 WGS-84 换算坐标（仅作参考，不一定准确）：

| # | 文件 | 名称 | 当前坐标 | POI参考WGS84 | 偏差km | POI名 |
|---|------|------|----------|-------------|--------|------|
| 1 | bipenggou_panyang.yaml | 磐羊湖 | (102.869,31.43) | (102.993,31.383) | 68.5 | 毕棚沟景区 |
| 2 | dagu_4860.yaml | 4860观景台 | (102.82,32.31) | (102.784,32.239) | 8.4 | 古冰川遗迹 |
| 3 | duoraogamu_yala_view.yaml | 亚拉主景平台 | (101.719,30.153) | (101.538,30.434) | 35.8 | 墨石公园景区 |
| 4 | genie_chachongxi.yaml | 查冲西村 | (99.905,30.107) | (99.821,29.832) | 31.6 | 川西格聂秘境酒店 |
| 5 | genie_eye.yaml | 格聂之眼 | (99.844,30.018) | (99.823,29.834) | 20.6 | 格聂之眼旅馆 |
| 6 | genie_laolenggusi.yaml | 老冷古寺 | (99.856,30.036) | (99.821,29.832) | 22.9 | 冷古隐宿 |
| 7 | genie_nuda_camp.yaml | 努达营地 | (99.793,29.998) | (99.789,29.855) | 15.9 | 格聂自然中心 |
| 8 | genie_xiazetong.yaml | 下则通村 | (99.882,30.056) | (99.775,29.832) | 26.9 | 格聂高原民宿 |
| 9 | gongga_lenggacuo.yaml | 冷嘎措 | (101.995,29.676) | (101.706,29.625) | 28.5 | 冷嘎措·山间小舍 |
| 10 | gongga_niubei.yaml | 牛背山(贡嘎) | (102.283,29.839) | (102.371,29.773) | 11.3 | 牛背山星辰营地 |
| 11 | gongga_yaha_pass.yaml | 雅哈垭口 | (101.839,29.886) | (101.687,29.808) | 17.0 | 雅哈垭口民宿 |
| 12 | gongga_yuzixi.yaml | 鱼子西 | (101.675,30.067) | (101.560,30.091) | 11.4 | 鱼子西 |
| 13 | gongga_zimei_pass.yaml | 子梅垭口 | (101.997,29.689) | (101.721,29.518) | 32.7 | 子梅垭口 |
| 14 | guergou_hot_spring_view.yaml | 河谷温泉机位 | (103.389,31.575) | (103.591,32.530) | 107.9 | 牟尼沟 |
| 15 | jiuzhai_wuhuahai.yaml | 五花海 | (103.903,33.184) | (103.881,33.162) | 3.2 | 五花海站 |
| 16 | lianbaoyeze_zhagaer.yaml | 扎尕尔措 | (100.784,32.964) | (101.174,33.066) | 38.1 | 扎尕尔措 |
| 17 | majiagou_main_view.yaml | 主沟观景点 | (102.884,31.571) | (102.117,29.653) | 225.5 | 海螺沟 |
| 18 | mengtun_gaoqiaogou.yaml | 高桥沟 | (103.188,31.466) | (103.127,31.690) | 25.5 | 孟屯高桥沟露营 |
| 19 | moshi_main_view.yaml | 异域星球观景位 | (101.565,30.045) | (101.538,30.434) | 43.3 | 墨石公园景区 |
| 20 | niubei_gongga.yaml | 牛背山 | (102.35,29.75) | (102.372,29.772) | 3.3 | 牛背山游客中心 |
| 21 | shenmulei_redwood_view.yaml | 红杉林主机位 | (102.872,30.782) | (102.717,30.689) | 18.0 | 神木垒山庄 |
| 22 | siguniang_changping.yaml | 长坪沟 | (102.941,31.09) | (102.824,31.097) | 11.1 | 四姑娘山景区 |
| 23 | siguniang_erguniang_view.yaml | 二姑娘峰观景位 | (102.905,31.077) | (102.922,31.049) | 3.5 | 二峰大本营 |
| 24 | siguniang_haizi_chaoshanping.yaml | 海子沟-朝山坪 | (102.918,31.073) | (102.824,31.097) | 9.3 | 四姑娘山景区 |
| 25 | siguniang_maobiliang.yaml | 猫鼻梁 | (102.932,31.096) | (102.845,30.990) | 14.4 | 猫鼻梁 |
| 26 | siguniang_shuangqiao.yaml | 双桥沟 | (102.966,31.137) | (102.824,31.097) | 14.2 | 四姑娘山景区 |
| 27 | tagong_muya.yaml | 木雅金塔机位 | (101.542,30.008) | (101.526,30.323) | 35.1 | 木雅金塔 |
| 28 | transit_18bends_view.yaml | 天路十八弯观景台 | (100.248,30.103) | (100.871,29.999) | 61.1 | 天路十八弯观景台 |
| 29 | transit_daerpu_valley.yaml | 大二普 | (102.938,31.377) | (102.993,31.383) | 5.2 | 毕棚沟景区 |
| 30 | transit_gaoersi_pass.yaml | 高尔寺山垭口 | (101.546,29.789) | (101.497,30.046) | 28.9 | 高尔寺山养护站 |
| 31 | transit_jiagenba_view.yaml | 甲根坝机位 | (101.654,29.93) | (101.558,29.852) | 12.7 | 邦达露营地 |
| 32 | transit_jianziwan_pass.yaml | 剪子弯山垭口 | (100.773,29.954) | (100.796,30.021) | 7.8 | G318剪子弯山服务区 |
| 33 | transit_kazila_pass.yaml | 卡子拉山垭口 | (100.582,30.065) | (100.638,30.148) | 10.7 | 卡子拉山停车场 |
| 34 | transit_lixiao_redstone.yaml | 理小路红石滩 | (102.962,31.327) | (102.899,31.390) | 9.2 | 凉台沟 |
| 35 | transit_lixiao_tunnel_view.yaml | 理小隧道口观景台 | (102.984,31.351) | (103.048,31.422) | 9.9 | 简阳坪1号隧道 |
| 36 | transit_xinduqiao_view.yaml | 新都桥镇外机位 | (101.509,30.03) | (101.508,30.036) | 0.7 | ✅ 唯一准确! |
| 37 | transit_zheduoshan_pass.yaml | 折多山垭口 | (101.724,30.049) | (101.795,30.082) | 7.8 | 折多山停车点 |
| 38 | yading_echushan_view.yaml | 俄初山观景台 | (100.242,28.586) | (100.194,28.563) | 5.3 | 俄初山观景台 |
| 39 | yading_five_color_lake.yaml | 五色海 | (100.338,28.435) | (100.351,28.380) | 6.2 | 五色海 |
| 40 | yading_luorong_pasture.yaml | 洛绒牛场 | (100.318,28.442) | (100.381,28.390) | 8.5 | 洛绒牛场 |
| 41 | yading_milk_lake.yaml | 牛奶海 | (100.327,28.438) | (100.346,28.374) | 7.3 | 牛奶海 |
| 42 | yading_pearl_lake.yaml | 珍珠海 | (100.288,28.431) | (100.350,28.419) | 6.2 | 仙乃日(错配) |
| 43 | yala_balangshengdu.yaml | 八郎生都 | (101.706,30.185) | (101.459,30.331) | 28.7 | 八郎生都日落餐厅 |
| 44 | yala_gedilamu.yaml | 格底拉姆 | (101.664,30.083) | (101.641,30.215) | 14.9 | 德吉藏餐 |
| 45 | yala_gunong.yaml | 姑弄村 | (101.681,30.112) | (101.516,30.356) | 31.4 | 姑弄村委会 |
| 46 | yala_tagong_view.yaml | 塔公草原机位 | (101.546,30.02) | (101.524,30.319) | 33.4 | 塔公草原大酒店 |
| 47 | yala_yunrao_view.yaml | 云绕亚拉 | (101.724,30.205) | (101.662,30.387) | 21.1 | 云绕亚拉停车场 |
| 48 | zhagushan_pass.yaml | 鹧鸪山垭口机位 | (102.929,31.779) | (102.741,31.880) | 21.0 | 鹧鸪山冰雪世界 |
| 49 | zheduo_gongga.yaml | 折多山 | (101.72,30.05) | (101.804,30.070) | 8.4 | 折多山 |

---

## Task 1: 四姑娘山区域 (5 个)

**Files:**
- Modify: `config/viewpoints/siguniang_maobiliang.yaml`
- Modify: `config/viewpoints/siguniang_changping.yaml`
- Modify: `config/viewpoints/siguniang_shuangqiao.yaml`
- Modify: `config/viewpoints/siguniang_haizi_chaoshanping.yaml`
- Modify: `config/viewpoints/siguniang_erguniang_view.yaml`

**Step 1: 在高德地图搜索并确认坐标**

使用浏览器打开 https://amap.com，逐个搜索以下地点，放大到能看清位置的级别：

| 搜索关键词 | 说明 | 注意 |
|-----------|------|------|
| 猫鼻梁 | S303 省道旁的观景平台，眺望四姑娘山 | 应在日隆镇东北方向的公路弯道上 |
| 长坪沟 | 四姑娘山长坪沟景区入口/喇嘛寺 | 搜"长坪沟景区"或"喇嘛寺" |
| 双桥沟 | 四姑娘山双桥沟景区入口 | 搜"双桥沟"景区入口 |
| 海子沟 朝山坪 | 海子沟内的朝山坪位置 | 若找不到可用"海子沟"入口坐标 |
| 二姑娘峰 | 二姑娘峰大本营或观景位 | 搜"四姑娘山二峰" |

**Step 2: 记录 GCJ-02 坐标并转换为 WGS-84**

在高德地图上点击或从 URL/搜索结果获取 GCJ-02 坐标，使用 `gcj02_to_wgs84()` 函数转换。

**Step 3: 修改 YAML 文件**

更新每个文件的 `location.lat` 和 `location.lon`。示例：
```yaml
# siguniang_maobiliang.yaml
location:
  lat: 30.990  # 修正前: 31.096
  lon: 102.845  # 修正前: 102.932
  altitude: 3500
```

**Step 4: Commit**

```bash
git add config/viewpoints/siguniang_*.yaml
git commit -m "fix(config): correct coordinates for Siguniangshan viewpoints"
```

---

## Task 2: 贡嘎山区域 (5 个)

**Files:**
- Modify: `config/viewpoints/gongga_lenggacuo.yaml` — 冷嘎措
- Modify: `config/viewpoints/gongga_niubei.yaml` — 牛背山(贡嘎)
- Modify: `config/viewpoints/gongga_yaha_pass.yaml` — 雅哈垭口
- Modify: `config/viewpoints/gongga_yuzixi.yaml` — 鱼子西
- Modify: `config/viewpoints/gongga_zimei_pass.yaml` — 子梅垭口

**Step 1: 搜索并确认坐标**

| 搜索关键词 | 说明 |
|-----------|------|
| 冷嘎措 | 贡嘎雪山西坡的高山湖泊，需放大确认湖泊位置 |
| 牛背山 | 搜"牛背山景区"，取山顶观景平台 |
| 雅哈垭口 | 甲根坝方向看贡嘎的垭口 |
| 鱼子西 | 康定附近的高山草甸观景台 |
| 子梅垭口 | 贡嘎西坡，子梅村上方的垭口 |

**Step 2-4: 同 Task 1 流程**

```bash
git add config/viewpoints/gongga_*.yaml
git commit -m "fix(config): correct coordinates for Gongga viewpoints"
```

---

## Task 3: 格聂区域 (5 个)

**Files:**
- Modify: `config/viewpoints/genie_eye.yaml` — 格聂之眼
- Modify: `config/viewpoints/genie_chachongxi.yaml` — 查冲西村
- Modify: `config/viewpoints/genie_laolenggusi.yaml` — 老冷古寺
- Modify: `config/viewpoints/genie_nuda_camp.yaml` — 努达营地
- Modify: `config/viewpoints/genie_xiazetong.yaml` — 下则通村

**Step 1: 搜索并确认坐标**

| 搜索关键词 | 说明 |
|-----------|------|
| 格聂之眼 | 理塘县格聂景区内的水潭景观 |
| 查冲西村 | 格聂景区附近的藏族村落 |
| 冷古寺 | 格聂主峰脚下的古寺 |
| 格聂营地 / 虎皮坝 | 格聂徒步环线上的营地 |
| 下则通村 | 格聂景区附近的村庄 |

**Step 2-4: 同 Task 1 流程**

```bash
git add config/viewpoints/genie_*.yaml
git commit -m "fix(config): correct coordinates for Genie viewpoints"
```

---

## Task 4: 亚丁区域 (5 个)

**Files:**
- Modify: `config/viewpoints/yading_echushan_view.yaml`
- Modify: `config/viewpoints/yading_five_color_lake.yaml`
- Modify: `config/viewpoints/yading_luorong_pasture.yaml`
- Modify: `config/viewpoints/yading_milk_lake.yaml`
- Modify: `config/viewpoints/yading_pearl_lake.yaml`

**Step 1: 搜索并确认坐标**

| 搜索关键词 | 说明 |
|-----------|------|
| 俄初山观景台 | 亚丁景区外，去往亚丁路上 |
| 五色海 | 亚丁景区内高海拔湖泊 |
| 洛绒牛场 | 亚丁景区内的高山牧场 |
| 牛奶海 | 亚丁景区内高海拔湖泊 |
| 珍珠海 / 卓玛拉措 | 亚丁景区内仙乃日脚下的湖泊 |

**Step 2-4: 同 Task 1 流程**

```bash
git add config/viewpoints/yading_*.yaml
git commit -m "fix(config): correct coordinates for Yading viewpoints"
```

---

## Task 5: 亚拉雪山区域 (5 个)

**Files:**
- Modify: `config/viewpoints/yala_balangshengdu.yaml`
- Modify: `config/viewpoints/yala_gedilamu.yaml`
- Modify: `config/viewpoints/yala_gunong.yaml`
- Modify: `config/viewpoints/yala_tagong_view.yaml`
- Modify: `config/viewpoints/yala_yunrao_view.yaml`

**Step 1: 搜索并确认坐标**

| 搜索关键词 | 说明 |
|-----------|------|
| 八郎生都 | 亚拉雪山观景酒店位置 |
| 格底拉姆 | 新都桥附近看亚拉雪山的位置 |
| 姑弄村 | 道孚县/康定的一个藏族村落 |
| 塔公草原 | 塔公草原上看亚拉雪山的机位 |
| 云绕亚拉 / 亚拉雪山观景台 | 亚拉雪山方向的观景台 |

**Step 2-4: 同 Task 1 流程**

```bash
git add config/viewpoints/yala_*.yaml
git commit -m "fix(config): correct coordinates for Yala viewpoints"
```

---

## Task 6: 交通沿线观景台 (11 个)

**Files:**
- Modify: `config/viewpoints/tagong_muya.yaml` — 木雅金塔
- Modify: `config/viewpoints/transit_18bends_view.yaml` — 天路十八弯
- Modify: `config/viewpoints/transit_daerpu_valley.yaml` — 大二普
- Modify: `config/viewpoints/transit_gaoersi_pass.yaml` — 高尔寺山垭口
- Modify: `config/viewpoints/transit_jiagenba_view.yaml` — 甲根坝机位
- Modify: `config/viewpoints/transit_jianziwan_pass.yaml` — 剪子弯山垭口
- Modify: `config/viewpoints/transit_kazila_pass.yaml` — 卡子拉山垭口
- Modify: `config/viewpoints/transit_lixiao_redstone.yaml` — 凉台沟红石滩
- Modify: `config/viewpoints/transit_lixiao_tunnel_view.yaml` — 理小隧道口
- Modify: `config/viewpoints/transit_xinduqiao_view.yaml` — 新都桥(✅已准确)
- Modify: `config/viewpoints/transit_zheduoshan_pass.yaml` — 折多山垭口

**Step 1: 搜索并确认坐标**

| 搜索关键词 | 说明 |
|-----------|------|
| 木雅金塔 | 塔公草原上的金塔景点 |
| 天路十八弯 | 理塘毛垭大草原上的观景台 |
| 大二普 | 毕棚沟附近 |
| 高尔寺山 | G318 上的垭口 |
| 甲根坝 | 康定甲根坝镇附近看贡嘎的机位 |
| 剪子弯山 | G318 雅江到理塘之间的垭口 |
| 卡子拉山 | G318 雅江到理塘之间的垭口 |
| 凉台沟 | 理县到小金的路上，红石滩景点 |
| 理小隧道 | 理县到小金隧道口的观景台 |
| 新都桥 | ✅ 已准确, 检查确认即可 |
| 折多山垭口 | G318 康定到新都桥的垭口 |

**Step 2-4: 同 Task 1 流程**

```bash
git add config/viewpoints/tagong_muya.yaml config/viewpoints/transit_*.yaml
git commit -m "fix(config): correct coordinates for transit viewpoints"
```

---

## Task 7: 其他独立景区 (10 个)

**Files:**
- Modify: `config/viewpoints/bipenggou_panyang.yaml` — 毕棚沟磐羊湖
- Modify: `config/viewpoints/dagu_4860.yaml` — 达古冰川4860
- Modify: `config/viewpoints/duoraogamu_yala_view.yaml` — 多饶嘎姆/亚拉主景
- Modify: `config/viewpoints/guergou_hot_spring_view.yaml` — 牟尼沟/河谷温泉
- Modify: `config/viewpoints/jiuzhai_wuhuahai.yaml` — 九寨沟五花海
- Modify: `config/viewpoints/lianbaoyeze_zhagaer.yaml` — 莲宝叶则扎尕尔措
- Modify: `config/viewpoints/majiagou_main_view.yaml` — 磨西沟主观景
- Modify: `config/viewpoints/mengtun_gaoqiaogou.yaml` — 孟屯高桥沟
- Modify: `config/viewpoints/moshi_main_view.yaml` — 墨石公园
- Modify: `config/viewpoints/zhagushan_pass.yaml` — 鹧鸪山垭口

**Step 1: 搜索并确认坐标**

| 搜索关键词 | 说明 |
|-----------|------|
| 毕棚沟 磐羊湖 | 理县毕棚沟景区内 |
| 达古冰川 4860 | 达古冰川最高缆车站, 海拔4860m |
| 墨石公园 / 多饶嘎姆 | 道孚八美镇的墨石公园 |
| 牟尼沟 二道海 | 松潘牟尼沟景区温泉区域 |
| 九寨沟 五花海 | 九寨沟景区内的五花海观景台 |
| 莲宝叶则 扎尕尔措 | 阿坝县莲宝叶则景区内 |
| 磨西古镇 / 海螺沟 | 甘孜磨西镇附近观景点 |
| 孟屯河谷 高桥沟 | 理县孟屯河谷景区 |
| 墨石公园 | 道孚八美镇墨石公园景区 |
| 鹧鸪山 | 理县鹧鸪山垭口 |

**Step 2-4: 同 Task 1 流程**

```bash
git add config/viewpoints/bipenggou_*.yaml config/viewpoints/dagu_*.yaml \
  config/viewpoints/duoraogamu_*.yaml config/viewpoints/guergou_*.yaml \
  config/viewpoints/jiuzhai_*.yaml config/viewpoints/lianbaoyeze_*.yaml \
  config/viewpoints/majiagou_*.yaml config/viewpoints/mengtun_*.yaml \
  config/viewpoints/moshi_*.yaml config/viewpoints/zhagushan_*.yaml
git commit -m "fix(config): correct coordinates for other scenic viewpoints"
```

---

## Task 8: 牛背山 + 神木垒 + 折多山 (4 个)

**Files:**
- Modify: `config/viewpoints/niubei_gongga.yaml` — 牛背山
- Modify: `config/viewpoints/shenmulei_redwood_view.yaml` — 神木垒红杉林
- Modify: `config/viewpoints/zheduo_gongga.yaml` — 折多山
- Modify: `config/viewpoints/zhagushan_pass.yaml` — 鹧鸪山 (已在 Task 7)

**Step 1: 搜索并确认坐标**

| 搜索关键词 | 说明 |
|-----------|------|
| 牛背山 景区 | 荥经/天全的牛背山，取山顶观景台 |
| 神木垒 红杉林 | 宝兴县神木垒景区红杉林区域 |
| 折多山 | 康定折多山，取山顶或垭口标志性地点 |

**Step 2-4: 同 Task 1 流程**

```bash
git add config/viewpoints/niubei_*.yaml config/viewpoints/shenmulei_*.yaml \
  config/viewpoints/zheduo_*.yaml
git commit -m "fix(config): correct coordinates for Niubeishan and Shenmulei"
```

---

## Task 9: 更新 targets 坐标

每个 YAML 文件中除了 `location` 还有 `targets` 字段（如幺妹峰、贡嘎主峰等目标山峰坐标）。在修复观景台位置后，也应检查 targets 中的山峰坐标是否正确。

**Step 1: 检查所有 targets 坐标**

```bash
grep -A3 "targets:" config/viewpoints/*.yaml | grep -E "lat:|lon:"
```

对照 Wikipedia/Google Earth 等来源确认山峰坐标。主要的山峰坐标参考：

| 山峰 | WGS-84 坐标 |
|------|-------------|
| 幺妹峰(四姑娘山主峰) | lat=31.106, lon=102.902 |
| 贡嘎山主峰 | lat=29.596, lon=101.879 |
| 格聂主峰 | lat=29.831, lon=99.773 |
| 仙乃日 | lat=28.433, lon=100.316 |
| 央迈勇 | lat=28.398, lon=100.334 |
| 夏诺多吉 | lat=28.413, lon=100.371 |
| 亚拉雪山 | lat=30.380, lon=101.560 |

> 以上山峰坐标需在地图上验证后使用。

**Step 2: 修复有误的 targets**

**Step 3: Commit**

```bash
git add config/viewpoints/*.yaml
git commit -m "fix(config): correct mountain peak target coordinates"
```

---

## Task 10: 重新生成前端数据 & 验证

**Step 1: 重新生成前端静态数据**

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor
source venv/bin/activate
python -m golden_moment_predictor batch_generate --output frontend/public/data
```

> 如果 batch_generate 命令不可用，手动检查 `frontend/public/data/index.json` 中的坐标是否需要同步更新。

**Step 2: 运行前端测试**

```bash
cd frontend && npm test -- --run
```

**Step 3: 浏览器验证**

1. 打开 http://localhost:5173
2. 放大到各个区域检查标记位置
3. 重点检查: 猫鼻梁、格聂之眼、子梅垭口、五色海

**Step 4: Final commit**

```bash
git add frontend/public/data/
git commit -m "chore: regenerate frontend data with corrected coordinates"
```
