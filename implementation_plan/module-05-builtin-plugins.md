# M05 - 内置评分插件（6个）

## 1. 模块目标

实现系统首版 6 个景观评分器：

1. `GoldenMountainPlugin`
2. `StargazingPlugin`
3. `CloudSeaPlugin`
4. `FrostPlugin`
5. `SnowTreePlugin`
6. `IceIciclePlugin`

并确保它们遵循统一插件契约，能被 `ScoreEngine` 调用。

---

## 2. 背景上下文

- 参考：`design/03-scoring-plugins.md`
- 核心约束：
  - 分值统一 0~100
  - 状态映射：Perfect / Recommended / Possible / Not Recommended
  - Golden 维度一票否决：光路/目标/本地任一关键维度为 0 则总分 0

---

## 3. 交付范围

### 本模块要做

- `scorer/golden_mountain.py`
- `scorer/stargazing.py`
- `scorer/cloud_sea.py`
- `scorer/frost.py`
- `scorer/snow_tree.py`
- `scorer/ice_icicle.py`
- 插件注册代码（可放 `scorer/engine.py` 的初始化函数或单独模块）

### 本模块不做

- 不处理调度循环（M06）
- 不处理 API 输出格式（M07/M08）

---

## 4. 输入与输出契约

### 输入

- `DataContext`
- L1/L2 分析结果（通过 `context` 与 `details`）

### 输出

- `ScoreResult(total_score, status, breakdown, ...)`
- 每个插件需定义 `event_type`、`display_name`、`data_requirement`

---

## 5. 实施任务清单

1. GoldenMountain：
   - 实现触发：总云量<80 且存在匹配目标
   - 评分三维度：光路(35) + 目标(40) + 本地(25)
   - 执行维度 veto
2. Stargazing：
   - 实现窗口品质与基准分
   - 云量扣分、风速扣分
3. CloudSea：
   - 实现高差/密度/风速阶梯打分
4. Frost：
   - 实现温度/湿度/风速/云况打分
5. SnowTree：
   - 数据来源：基于 Open-Meteo `snowfall/weather_code/cloud_cover/precip_prob/temperature/wind` 与 `past_hours` 推断
   - 实现触发：常规路径（近12小时降雪）；留存路径（近24小时较大雪量+持续低温），且当前晴朗
   - 评分模型：积雪信号 + 晴朗程度 + 稳定保持 - 降雪距今扣分 - 升温融化扣分
6. IceIcicle：
   - 数据来源：基于 Open-Meteo `rain/showers/snowfall/temperature/weather_code/cloud_cover/precip_prob/wind` 与 `past_hours` 推断
   - 实现触发：常规路径（近12小时有效水源并冻结）；留存路径（近24小时强水源+持续低温），且当前可观赏
   - 评分模型：水源输入 + 冻结强度 + 观赏条件 - 水源距今扣分 - 升温融化扣分
7. 统一封装状态映射与分值裁剪函数，避免重复代码。

---

## 6. 验收标准

1. 示例数据可复现关键结果：
   - golden=87
   - stargazing≈98
   - cloud_sea≈95
   - frost≈67
   - snow_tree 在“前夜降雪+夜间持续零下+次日晴朗”场景可触发，且在低温留存场景达到 `Recommended`（≥80）
   - snow_tree 在“降雪距今较久且明显升温”场景应明显降级（`Possible` 或更低）
   - ice_icicle 在“前段时间有水源输入+持续冻结+当前晴朗”场景可触发
   - ice_icicle 在“水源距今较久或升温明显”场景应明显降级（`Possible` 或更低）
2. 每个插件的 `data_requirement` 与设计表一致；
3. 插件可独立单测，不依赖真实 API；
4. 输出 breakdown 结构统一。

---

## 7. 测试清单

- `tests/unit/test_plugin_golden.py`
  - 推荐、完美、光路 veto、目标 veto、安全 veto
- `tests/unit/test_plugin_stargazing.py`
  - optimal、poor、高风、不同月相
- `tests/unit/test_plugin_cloud_sea.py`
  - 厚云海、无云海
- `tests/unit/test_plugin_frost.py`
  - 理想雾凇、干燥雾凇
- `tests/unit/test_plugin_snow_tree.py`
  - 近12小时降雪+当前晴朗触发、无近期降雪不触发、阴天不触发
  - 前夜降雪+持续零下+次日10~12点仍可触发（留存路径）
  - 降雪距今扣分：同等条件下 `hours_since_last_snow` 越大分数越低
  - 升温扣分：同等降雪条件下 `max_temp_since_last_snow` 越高分数越低
- `tests/unit/test_plugin_ice_icicle.py`
  - 近12小时有效水源并冻结触发、无水源不触发、阴天不触发
  - 前夜强水源+持续零下+次日中午仍可触发（留存路径）
  - 水源距今扣分：同等条件下 `hours_since_last_water_input` 越大分数越低
  - 升温扣分：同等水源条件下 `max_temp_since_last_water` 越高分数越低

---

## 8. 新会话启动提示词

```text
请按 implementation_plan/module-05-builtin-plugins.md 完成 M05：
实现六个内置插件（含 SnowTreePlugin、IceIciclePlugin）及评分逻辑，严格对齐设计文档中的公式与阈值，并补齐插件单测。
目标是复现示例分数：87/98/95/67，并验证 snow_tree / ice_icicle 在“前夜发生事件+持续低温留存+次日晴朗”场景仍可稳定触发。
```
