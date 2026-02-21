# MH1A: Viewpoint 分组配置 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 Viewpoint 数据模型新增 `groups` 字段（列表类型，支持一个景点属于多个分组），更新 48 个 YAML 配置文件，删除重复的牛背山配置。

**Architecture:** 修改 `Viewpoint` dataclass 新增 `groups: list[str]`，更新 `ViewpointConfig.load()` 解析逻辑，通过批量脚本为所有 YAML 添加分组配置。

**Tech Stack:** Python 3.11, PyYAML

**设计文档:** [12-poster-page.md](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/12-poster-page.md) §12.3

**后续计划:** MH1B（海报数据生成器）、MH1C（海报前端页面）

---

## Proposed Changes

### Task 1: 删除重复 viewpoint 配置

删除重复的 `gongga_niubei.yaml`，保留更完整的 `niubei_gongga.yaml`（7 capabilities + 2 targets vs 5 capabilities + 1 target）。

---

#### [DELETE] [gongga_niubei.yaml](file:///Users/mpb/WorkSpace/golden-moment-predictor/config/viewpoints/gongga_niubei.yaml)

当前两个牛背山配置对比：

| | `niubei_gongga` (保留) | `gongga_niubei` (删除) |
|--|--|--|
| capabilities | sunrise, sunset, stargazing, cloud_sea, frost, snow_tree, ice_icicle (7) | sunrise, sunset, stargazing, cloud_sea, snow_tree (5) |
| targets | 贡嘎主峰 (primary) + 雅拉神山 (secondary) | 贡嘎主峰 (primary) |
| 坐标 | 相同 | 相同 |

**Step 1:** 删除文件

```bash
rm config/viewpoints/gongga_niubei.yaml
```

**Step 2:** 验证无其他代码硬引用此 ID

```bash
grep -r "gongga_niubei" --include="*.py" --include="*.js" --include="*.vue" gmp/ frontend/src/
```

Expected: 无结果

**Step 3:** Commit

```bash
git add -u config/viewpoints/gongga_niubei.yaml
git commit -m "chore: remove duplicate gongga_niubei viewpoint (keep niubei_gongga)"
```

---

### Task 2: Viewpoint Model 新增 `groups` 字段

---

#### [MODIFY] [models.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/core/models.py)

在 `Viewpoint` dataclass 新增 `groups: list[str]`：

```diff
 @dataclass
 class Viewpoint:
     """观景台"""
     id: str
     name: str
     location: Location
     capabilities: list[str]
     targets: list[Target]
+    groups: list[str] = field(default_factory=list)  # 山系分组 (如 ["gongga", "318"])
```

---

#### [MODIFY] [config_loader.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/core/config_loader.py)

在 `ViewpointConfig.load()` 方法中解析 `groups` 字段：

```diff
         vp = Viewpoint(
             id=data["id"],
             name=data["name"],
             location=location,
             capabilities=data.get("capabilities", []),
             targets=targets,
+            groups=data.get("groups", []),
         )
```

**Step 1: Write failing test** (见 Task 3)

**Step 2: Write implementation**

**Step 3: Run tests**

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor && python -m pytest tests/unit/test_viewpoint_config.py tests/unit/test_models.py -v`

**Step 4: Commit**

```bash
git add gmp/core/models.py gmp/core/config_loader.py
git commit -m "feat(config): add groups field to Viewpoint model"
```

---

### Task 3: 批量更新 48 个 YAML 配置

---

#### [NEW] [add_groups.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/scripts/add_groups.py)

批量脚本为所有 viewpoint YAML 添加 `groups` 字段：

```python
"""为所有 viewpoint YAML 添加 groups 字段"""
from pathlib import Path

GROUP_MAP = {
    "niubei_gongga": ["gongga"],
    "gongga_lenggacuo": ["gongga"],
    "gongga_yaha_pass": ["gongga"],
    "gongga_yuzixi": ["gongga"],
    "gongga_zimei_pass": ["gongga"],
    "zheduo_gongga": ["gongga"],
    "siguniang_changping": ["siguniang"],
    "siguniang_erguniang_view": ["siguniang"],
    "siguniang_haizi_chaoshanping": ["siguniang"],
    "siguniang_maobiliang": ["siguniang"],
    "siguniang_shuangqiao": ["siguniang"],
    "yala_balangshengdu": ["yala"],
    "yala_gedilamu": ["yala"],
    "yala_gunong": ["yala"],
    "yala_tagong_view": ["yala"],
    "yala_yunrao_view": ["yala"],
    "duoraogamu_yala_view": ["yala"],
    "genie_chachongxi": ["genie"],
    "genie_eye": ["genie"],
    "genie_laolenggusi": ["genie"],
    "genie_nuda_camp": ["genie"],
    "genie_xiazetong": ["genie"],
    "yading_echushan_view": ["yading"],
    "yading_five_color_lake": ["yading"],
    "yading_luorong_pasture": ["yading"],
    "yading_milk_lake": ["yading"],
    "yading_pearl_lake": ["yading"],
    "transit_gaoersi_pass": ["318"],
    "transit_zheduoshan_pass": ["318"],
    "transit_jianziwan_pass": ["318"],
    "transit_kazila_pass": ["318"],
    "transit_xinduqiao_view": ["318"],
    "transit_jiagenba_view": ["318"],
    "transit_18bends_view": ["318"],
    "transit_daerpu_valley": ["318"],
    "transit_lixiao_redstone": ["lixiao"],
    "transit_lixiao_tunnel_view": ["lixiao"],
    "jiuzhai_wuhuahai": ["other"],
    "lianbaoyeze_zhagaer": ["other"],
    "bipenggou_panyang": ["other"],
    "dagu_4860": ["other"],
    "guergou_hot_spring_view": ["other"],
    "majiagou_main_view": ["other"],
    "mengtun_gaoqiaogou": ["other"],
    "moshi_main_view": ["other"],
    "shenmulei_redwood_view": ["other"],
    "tagong_muya": ["other"],
    "zhagushan_pass": ["other"],
}

config_dir = Path("config/viewpoints")
for yaml_file in sorted(config_dir.glob("*.yaml")):
    text = yaml_file.read_text(encoding="utf-8")
    if "\ngroups:" in text:
        continue
    vp_id = yaml_file.stem
    groups = GROUP_MAP.get(vp_id, ["other"])
    groups_yaml = "groups:\n" + "".join(f"  - {g}\n" for g in groups)
    text = text.replace("\nlocation:", f"\n{groups_yaml}location:", 1)
    yaml_file.write_text(text, encoding="utf-8")
    print(f"Updated: {yaml_file.name} -> {groups}")
```

**Step 1:** 运行脚本

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor && python scripts/add_groups.py`

**Step 2:** 验证所有 YAML 都有 groups

```bash
grep -L "^groups:" config/viewpoints/*.yaml
```

Expected: 空输出

**Step 3:** Commit

```bash
git add config/viewpoints/ scripts/add_groups.py
git commit -m "feat(config): add groups field to all viewpoint YAMLs"
```

---

### Task 4: 更新 batch_generator index.json 输出

---

#### [MODIFY] [batch_generator.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/gmp/core/batch_generator.py)

在 `index.json` 输出中新增 `groups` 字段：

```diff
             vp_index.append({
                 "id": vp.id,
                 "name": vp.name,
+                "groups": vp.groups,
                 "location": {
                     "lat": vp.location.lat,
```

**Step 1:** 修改代码

**Step 2:** Run tests

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor && python -m pytest tests/unit/test_batch_generator.py -v`

**Step 3:** Commit

```bash
git add gmp/core/batch_generator.py
git commit -m "feat(batch): include groups in index.json output"
```

---

### Task 5: 测试

---

#### [MODIFY] [test_viewpoint_config.py](file:///Users/mpb/WorkSpace/golden-moment-predictor/tests/unit/test_viewpoint_config.py)

新增测试验证 `groups` 字段：

```python
def test_viewpoint_groups_field(tmp_path):
    """验证 groups 字段被正确解析"""
    yaml_content = """
id: test_vp
name: 测试观景台
groups:
  - gongga
  - 318
location:
  lat: 30.0
  lon: 102.0
  altitude: 3000
capabilities:
  - clear_sky
"""
    (tmp_path / "test.yaml").write_text(yaml_content, encoding="utf-8")
    config = ViewpointConfig()
    config.load(str(tmp_path))
    vp = config.get("test_vp")
    assert vp.groups == ["gongga", "318"]


def test_viewpoint_groups_default_empty(tmp_path):
    """验证 groups 缺失时默认空列表"""
    yaml_content = """
id: test_vp2
name: 无分组观景台
location:
  lat: 30.0
  lon: 102.0
  altitude: 3000
"""
    (tmp_path / "test2.yaml").write_text(yaml_content, encoding="utf-8")
    config = ViewpointConfig()
    config.load(str(tmp_path))
    vp = config.get("test_vp2")
    assert vp.groups == []
```

Run: `cd /Users/mpb/WorkSpace/golden-moment-predictor && python -m pytest tests/unit/test_viewpoint_config.py -v`

---

## Verification Plan

### Automated Tests

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor
python -m pytest tests/unit/test_viewpoint_config.py tests/unit/test_models.py tests/unit/test_batch_generator.py -v
```

### 配置一致性检查

```bash
# 所有 YAML 都有 groups
grep -L "^groups:" config/viewpoints/*.yaml
# Expected: 空输出

# 重复 viewpoint 已删除
ls config/viewpoints/gongga_niubei.yaml 2>&1
# Expected: No such file or directory

# 总数正确 (48 个)
ls config/viewpoints/*.yaml | wc -l
# Expected: 48
```

### 集成验证

```bash
cd /Users/mpb/WorkSpace/golden-moment-predictor
python -m pytest tests/integration/test_config_consistency.py -v
```

---

*计划版本: v1.0 | 创建: 2026-02-21 | 拆分自 MH1-poster-page.md v2.0*
