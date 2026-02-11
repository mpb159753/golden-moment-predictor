# Module 08: 输出层 — Reporter + CLI

## 模块背景

输出层负责将 Scheduler 的原始评分结果转换为用户友好的输出格式。包含三种输出器：ForecastReporter（JSON 推荐事件）、TimelineReporter（JSON 逐小时时间轴）、CLIFormatter（终端彩色输出）。以及 SummaryGenerator（每日摘要生成器）。

**在系统中的位置**: 输出层 (`gmp/reporter/`) — Scheduler 评分完成后的最后一步。

**前置依赖**: Module 01（数据模型）, Module 07（Scheduler 输出的原始结果结构）

## 设计依据

- [04-data-flow-example.md](../design/04-data-flow-example.md): §Stage 6a ForecastReporter 输出, §Stage 6b TimelineReporter 输出
- [05-api.md](../design/05-api.md): §5.2 forecast 响应, §5.3 timeline 响应
- [06-class-sequence.md](../design/06-class-sequence.md): §6.4 输出层类图

## 待创建文件列表

| 文件 | 说明 |
|------|------|
| `gmp/reporter/__init__.py` | 包初始化 |
| `gmp/reporter/base.py` | BaseReporter 抽象基类 |
| `gmp/reporter/forecast_reporter.py` | ForecastReporter (JSON 推荐事件) |
| `gmp/reporter/timeline_reporter.py` | TimelineReporter (JSON 逐小时) |
| `gmp/reporter/cli_formatter.py` | CLIFormatter (终端彩色输出) |
| `gmp/reporter/summary_generator.py` | SummaryGenerator (规则/LLM) |
| `tests/unit/test_forecast_reporter.py` | ForecastReporter 测试 |
| `tests/unit/test_timeline_reporter.py` | TimelineReporter 测试 |
| `tests/unit/test_cli_formatter.py` | CLIFormatter 测试 |

## 代码接口定义

### `gmp/reporter/forecast_reporter.py`

```python
class ForecastReporter(BaseReporter):
    """生成 /api/v1/forecast/{id} 格式的 JSON 输出"""
    
    def __init__(self, summary_generator: SummaryGenerator):
        self._summary_gen = summary_generator
    
    def generate(self, scheduler_result: dict) -> dict:
        """将 Scheduler 原始结果转换为 Forecast JSON
        
        输出结构 (参见设计文档 Stage 6a):
        {
            "report_date": "2026-02-10",
            "viewpoint": "牛背山",
            "forecast_days": [
                {
                    "date": "2026-02-11",
                    "confidence": "High",
                    "summary": "极佳观景日 — ...",
                    "summary_mode": "rule",
                    "events": [
                        {
                            "type": str,
                            "time_window": str,
                            "score": int,
                            "status": str,
                            "conditions": {...},
                            "score_breakdown": {...},
                        }, ...
                    ]
                }, ...
            ],
            "meta": {
                "generated_at": "2026-02-10T08:00:00+08:00",
                "cache_stats": {...}
            }
        }
        """
    
    def _build_events(self, score_results: list) -> list[dict]:
        """构建事件列表"""
    
    def _format_conditions(self, event_type: str, context: dict) -> dict:
        """根据事件类型生成条件详情"""
```

### `gmp/reporter/timeline_reporter.py`

```python
class TimelineReporter(BaseReporter):
    """生成 /api/v1/timeline/{id} 格式的 JSON 输出"""
    
    def generate(self, scheduler_result: dict) -> dict:
        """将 Scheduler 原始结果转换为 Timeline JSON
        
        输出结构 (参见设计文档 Stage 6b):
        {
            "viewpoint": "牛背山",
            "timeline_days": [
                {
                    "date": "2026-02-11",
                    "confidence": "High",
                    "hours": [
                        {
                            "hour": int,
                            "l1_passed": bool,
                            "cloud_cover": int,
                            "precip_prob": int,
                            "temperature": float,
                            "tags": [str, ...],
                        }, ...
                    ]
                }, ...
            ]
        }
        """
    
    def _assign_tags(self, hour: int, hour_data: dict, 
                      day_context: dict) -> list[str]:
        """为每个小时分配标签
        
        标签映射 (参见设计文档 §5.5 枚举):
        - stargazing_window: 最佳观星时段
        - pre_sunrise: 日出前30min
        - sunrise_golden: 日照金山时段
        - cloud_sea: 云海可见时段
        - frost_window: 雾凇观赏时段
        - snow_tree_window: 树挂积雪观赏时段
        - ice_icicle_window: 冰挂观赏时段
        - rain: 降水时段
        - overcast: 阴天 (云量>60%)
        - clearing: 天气转晴
        """
```

### `gmp/reporter/summary_generator.py`

```python
class SummaryGenerator:
    """每日摘要生成器"""
    
    def __init__(self, mode: str = "rule"):
        self._mode = mode  # "rule" | "llm"
    
    def generate(self, events: list[dict]) -> tuple[str, str]:
        """生成每日摘要
        
        返回: (summary_text, mode)
        
        规则模式示例:
        - 无事件: "不推荐 — 全天降水"
        - 有事件: "极佳观景日 — 日照金山+壮观云海+完美暗夜"
        """
    
    def _rule_based(self, events: list[dict]) -> str:
        """基于规则生成摘要
        
        逻辑:
        1. 统计 Perfect + Recommended 的事件
        2. 拼接事件名称
        3. 添加前缀: "极佳观景日" / "推荐出行" / "部分景观可见" / "不推荐"
        """
```

### `gmp/reporter/cli_formatter.py`

```python
class CLIFormatter(BaseReporter):
    """终端彩色格式化输出"""
    
    def __init__(self, color_enabled: bool = True):
        self._color = color_enabled
    
    def generate(self, scheduler_result: dict) -> str:
        """生成终端友好的格式化文本
        
        示例:
        ╔══════════════════════════════════════╗
        ║     🏔️ 牛背山 · 7日景观预测         ║
        ╚══════════════════════════════════════╝

        📅 2026-02-11 (High)
        ────────────────────
        🌅 日照金山  ⭐ 87/100  ✅ Recommended
           光路: 35/35  目标: 32/40  本地: 20/25
        🌌 观星     ⭐ 98/100  🏆 Perfect
           基准: 100  云量: -2  风速: 0
        """
    
    def _format_score(self, score: int) -> str:
        """分数格式化 + 颜色"""
    
    def _colorize(self, text: str, level: str) -> str:
        """ANSI 颜色包装"""
    
    def _status_emoji(self, status: str) -> str:
        """状态对应 emoji: Perfect=🏆, Recommended=✅, Possible=⚠️, Not Recommended=❌"""
```

## 实现要点

1. **ForecastReporter**: 
   - `score_breakdown` 中每个维度必须包含 `score`, `max` 两个字段
   - `conditions` 的结构因 `event_type` 而异（如日照金山有 targets 和 light_path，云海有 gap）

2. **TimelineReporter**:
   - 输出 24 小时数据，即使某些小时 L1 未通过也要输出
   - `tags` 通过分析事件时间窗口和天气条件动态生成

3. **SummaryGenerator**:
   - 初期仅实现 `rule` 模式
   - `llm` 模式预留接口，后续迭代

4. **CLIFormatter**:
   - 使用 ANSI 转义码实现颜色
   - 支持 `--no-color` 模式

## 测试计划

### 测试操作步骤

```bash
source venv/bin/activate
python -m pytest tests/unit/test_forecast_reporter.py \
  tests/unit/test_timeline_reporter.py tests/unit/test_cli_formatter.py -v
```

### 具体测试用例

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `test_forecast_reporter.py` | `test_clear_day_output` | 晴天输出包含 6 个事件 |
| `test_forecast_reporter.py` | `test_rainy_day_output` | 雨天 events=[] |
| `test_forecast_reporter.py` | `test_score_breakdown_format` | score_breakdown 含 score+max |
| `test_forecast_reporter.py` | `test_meta_fields` | meta.generated_at 为 ISO 8601 |
| `test_timeline_reporter.py` | `test_24_hours_coverage` | 输出包含 0-23 小时 |
| `test_timeline_reporter.py` | `test_tag_assignment` | 日出时段包含 sunrise_golden tag |
| `test_timeline_reporter.py` | `test_rain_tag` | 降水概率>50 标记 rain tag |
| `test_cli_formatter.py` | `test_output_not_empty` | 有内容输出 |
| `test_cli_formatter.py` | `test_no_color_mode` | 无 ANSI 转义码 |
| `test_cli_formatter.py` | `test_emoji_mapping` | 状态 emoji 正确 |

## 验收标准

- [ ] ForecastReporter 输出结构与设计文档 Stage 6a 一致
- [ ] TimelineReporter 输出结构与设计文档 Stage 6b 一致
- [ ] SummaryGenerator 规则模式生成合理摘要
- [ ] CLIFormatter 终端输出美观可读
- [ ] 所有测试通过
