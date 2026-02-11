# Module 06: 评分插件 — 复杂型 (日照金山/观星)

## 模块背景

本模块实现 2 个需要远程数据（L2 滤网）或天文数据的复杂评分插件。它们在数据需求和评分逻辑上比简单型 Plugin 复杂得多。

**包含的 Plugin**:
- `GoldenMountainPlugin` — 日照金山（需要 L2 目标天气 + L2 光路天气 + 天文数据）
- `StargazingPlugin` — 观星（需要天文数据：月相/晨暮曦/日落）

**在系统中的位置**: 评分层 (`gmp/scorer/`) — 通过 ScoreEngine 注册。

**前置依赖**: 
- Module 01（数据模型 `DataContext`, `ScoreResult`）
- Module 04（L2 分析结果 `AnalysisResult`，光路/目标可见性数据）

## 设计依据

- [03-scoring-plugins.md](../design/03-scoring-plugins.md): §3.5 GoldenMountainPlugin, §3.6 StargazingPlugin
- [04-data-flow-example.md](../design/04-data-flow-example.md): §Stage 5 评分输出
- [06-class-sequence.md](../design/06-class-sequence.md): §6.5 主流程时序图
- [09-testing-config.md](../design/09-testing-config.md): §9.2 Plugin 测试用例

## 待创建文件列表

| 文件 | 说明 |
|------|------|
| `gmp/scorer/golden_mountain.py` | GoldenMountainPlugin |
| `gmp/scorer/stargazing.py` | StargazingPlugin |
| `tests/unit/test_plugin_golden.py` | 日照金山评分测试 |
| `tests/unit/test_plugin_stargazing.py` | 观星评分测试 |

## 代码接口定义

### `gmp/scorer/golden_mountain.py`

```python
from gmp.core.models import DataRequirement, DataContext, ScoreResult

class GoldenMountainPlugin:
    event_type = "sunrise_golden_mountain"  # 或 "sunset_golden_mountain"
    display_name = "日照金山"
    data_requirement = DataRequirement(
        needs_l2_target=True,
        needs_l2_light_path=True,
        needs_astro=True,
    )
    
    def check_trigger(self, l1_data: dict) -> bool:
        """触发条件: 总云量 < 80% 且 有匹配 Target"""
        return (l1_data["cloud_cover_total"] < 80 
                and len(l1_data.get("matched_targets", [])) > 0)
    
    def score(self, context: DataContext) -> ScoreResult:
        """评分公式:
        Score = S_light + S_target + S_local
        
        各维度:
        - 光路通畅 (满分35): 10点均值云量阶梯
            ≤10%: 35 | 10-20%: 30 | 20-30%: 20 | 30-50%: 10 | >50%: 0
        - 目标可见 (满分40): Primary目标高+中云阶梯
            ≤10%: 40 | 10-20%: 32 | 20-30%: 22 | >30%: 0
        - 本地通透 (满分25): 总云量阶梯
            ≤15%: 25 | 15-30%: 20 | 30-50%: 12 | >50%: 5 | >80%: 0
        
        一票否决:
        - S_light = 0 → 总分 0
        - S_target = 0 → 总分 0
        - S_local = 0 → 总分 0
        """
    
    def _score_light_path(self, light_path_data: list[dict]) -> tuple[int, str]:
        """计算光路通畅分数
        
        参数: 10个检查点的 {low_cloud, mid_cloud, combined} 数据
        返回: (分数, 说明文字)
        
        逻辑:
        1. 计算10点 combined (low+mid) 算术平均值
        2. 按阶梯映射分数
        """
    
    def _score_target_visible(self, context: DataContext) -> tuple[int, str]:
        """计算目标可见分数
        
        逻辑:
        1. 找到 primary 权重的 target
        2. 从 context.target_weather 获取该目标日出/日落时刻的 high_cloud + mid_cloud
        3. 按阶梯映射分数
        
        注意: secondary 目标不参与评分，仅记录在 warnings 中
        """
    
    def _score_local_clear(self, context: DataContext) -> tuple[int, str]:
        """计算本地通透分数
        
        从 context.local_weather 获取日出/日落时刻附近的总云量
        """
    
    def dimensions(self) -> list[str]:
        return ["light_path", "target_visible", "local_clear"]
```

### `gmp/scorer/stargazing.py`

```python
class StargazingPlugin:
    event_type = "stargazing"
    display_name = "观星"
    data_requirement = DataRequirement(
        needs_astro=True,  # 月相、月出月落、天文晨暮曦
    )
    
    def check_trigger(self, l1_data: dict) -> bool:
        """触发条件: 夜间总云量 < 70%"""
        return l1_data.get("night_cloud_cover", 100) < 70
    
    def score(self, context: DataContext) -> ScoreResult:
        """评分公式:
        Score = Base - Deduction_cloud - Deduction_wind
        
        基准分 (Base):
        - optimal: 100 (月亮在地平线下的完美暗夜)
        - good: 90 (月相<50%的残月微光)
        - partial: 70 (月相≥50%但有月下时段)
        - poor: 100 - phase×0.8 (满月整夜)
        
        扣分:
        - 云量: TotalCloudCover% × 0.8
        - 风速: >40km/h: -30 | >20km/h: -10 | ≤20: 0
        """
    
    def _determine_base_score(self, context: DataContext) -> tuple[int, str]:
        """根据 StargazingWindow.quality 确定基准分"""
    
    def _calc_cloud_deduction(self, context: DataContext) -> tuple[int, str]:
        """计算夜间平均云量扣分"""
    
    def _calc_wind_deduction(self, context: DataContext) -> tuple[int, str]:
        """计算风速扣分（影响长曝光）"""
    
    def dimensions(self) -> list[str]:
        return ["base", "cloud", "wind"]
```

## 实现要点

### GoldenMountainPlugin 关键逻辑

1. **日出 vs 日落**: 同一个 Plugin 类需要根据事件类型区分。可以在构造函数中传入 `event_type` 参数，或创建两个实例分别注册。设计文档中 `event_type` 可以是 `sunrise_golden_mountain` 或 `sunset_golden_mountain`。

   建议实现方式:
   ```python
   class GoldenMountainPlugin:
       def __init__(self, event_type: str = "sunrise_golden_mountain"):
           self._event_type = event_type
       
       @property
       def event_type(self) -> str:
           return self._event_type
   ```
   
   注册时:
   ```python
   engine.register(GoldenMountainPlugin("sunrise_golden_mountain"))
   engine.register(GoldenMountainPlugin("sunset_golden_mountain"))
   ```

2. **时间窗口**: 日出金山观赏窗口为日出前13分钟到日出后17分钟（约 sunrise-13min ~ sunrise+17min）。日落同理。

3. **光路数据来源**: 从 `context.light_path_weather` 获取，这是 10 个点的 `{low_cloud, mid_cloud, combined}` 列表。

4. **一票否决**: 任何维度得 0 分时，`total_score` 直接设为 0，不是简单求和。

### StargazingPlugin 关键逻辑

1. **时间窗口来源**: 从 `context.stargazing_window` 获取（由 `AstroUtils.determine_stargazing_window()` 计算）
2. **夜间云量**: 从 `context.local_weather` 中提取 20:00-05:00 时段的平均云量
3. **基准分映射**:
   - `quality == "optimal"` → Base = 100
   - `quality == "good"` → Base = 90
   - `quality == "partial"` → Base = 70
   - `quality == "poor"` → Base = max(0, 100 - moon_phase * 0.8)

## 测试计划

### 测试操作步骤

```bash
source venv/bin/activate
python -m pytest tests/unit/test_plugin_golden.py tests/unit/test_plugin_stargazing.py -v
```

### 具体测试用例

#### GoldenMountainPlugin

| 测试函数 | 输入 | 预期 |
|---------|------|------|
| `test_trigger_positive` | 总云22%, 有 matched_targets | True |
| `test_trigger_no_target` | 总云22%, matched_targets=[] | False |
| `test_trigger_overcast` | 总云85% | False |
| `test_score_recommended` | 光路8%, 目标13%, 本地22% | score=87, Recommended |
| `test_score_perfect` | 光路0%, 目标5%, 本地10% | score=100, Perfect |
| `test_veto_light_path` | 光路60%, 目标5%, 本地10% | score=0 (光路否决) |
| `test_veto_target` | 光路5%, 目标50%, 本地10% | score=0 (目标否决) |
| `test_veto_local` | 光路5%, 目标5%, 本地90% | score=0 (本地否决) |
| `test_sunset_variant` | event_type="sunset_..." | 使用日落方位角 |

#### StargazingPlugin

| 测试函数 | 输入 | 预期 |
|---------|------|------|
| `test_trigger_positive` | 夜间云量20% | True |
| `test_trigger_overcast` | 夜间云量75% | False |
| `test_score_perfect` | optimal暗夜, 云量2%, 风2.8 | score=98, Perfect |
| `test_score_good` | good窗口, 云量10%, 微风 | 82 ≤ score ≤ 90 |
| `test_score_poor` | poor(满月100%), 云量50% | score ≤ 30 |
| `test_wind_penalty` | optimal, 云量0%, 风45km/h | 扣30分 |
| `test_moderate_wind` | optimal, 云量0%, 风25km/h | 扣10分 |

## 验收标准

- [ ] GoldenMountainPlugin 评分与设计文档示例一致 (score=87)
- [ ] GoldenMountainPlugin 一票否决逻辑正确
- [ ] GoldenMountainPlugin 支持 sunrise/sunset 双模式
- [ ] StargazingPlugin 评分与设计文档示例一致 (score=98)
- [ ] StargazingPlugin 四种窗口等级基准分正确
- [ ] 所有测试通过
