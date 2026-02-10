# M10 - 测试基建与样例数据

## 1. 模块目标

建立可持续演进的测试体系，确保后续新增插件或规则调整有“快速回归”能力。

---

## 2. 背景上下文

- 参考：`design/09-testing-config.md`
- 测试金字塔目标：
  - Unit 30+
  - Integration 8
  - E2E 2

---

## 3. 交付范围

### 本模块要做

1. Pytest 测试工程化基础（`pytest.ini`、`conftest.py`）。
2. Fixtures 与 MockFetcher 场景库。
3. 单测/集成/E2E 目录组织与基线用例。
4. 关键配置与样例数据文件（YAML/JSON）。

### 本模块不做

- 不新增业务功能；只为已有实现建立验证体系。

---

## 4. 输入与输出契约

### 输入

- 各模块已实现的代码接口
- 设计文档给出的样例数据与目标分数

### 输出

- 一组可复用 fixtures
- 可本地执行的完整测试命令
- 覆盖核心业务路径的基线用例

---

## 5. 实施任务清单

1. 建立目录：
   - `tests/unit`
   - `tests/integration`
   - `tests/e2e`
   - `tests/fixtures`
2. 实现 `tests/fixtures/mock_fetcher.py`：
   - clear/rain/timeout/frost 场景
3. 准备 fixture 数据：
   - `weather_data_clear.json`
   - `weather_data_rainy.json`
   - `viewpoint_niubei.yaml`
4. 建立基线测试：
   - 全流程晴天
   - 雨天 L1 拦截
   - events 过滤跳过 L2
5. 添加测试命令文档（如 `pytest -q`、按目录执行）。

---

## 6. 验收标准

1. 测试可在新环境一键执行；
2. Mock 场景稳定，结果可重复；
3. 关键分支（降级、过滤、一票否决）均有覆盖；
4. 新增插件时可按模板快速补测。

---

## 7. 测试清单（本模块自身）

- `tests/unit/test_mock_fetcher.py`
  - 场景切换与调用计数
- `tests/integration/test_pipeline.py`
  - clear/rain/events 三分支
- `tests/e2e/test_full_forecast.py`
  - 端到端输出结构与关键字段

---

## 8. 新会话启动提示词

```text
请按 implementation_plan/module-10-testing-fixtures.md 完成 M10：
搭建 pytest 基建、fixtures 与 mock 场景，并补齐单测/集成/E2E 基线用例。
目标：让新功能开发后可通过测试快速回归，优先覆盖 clear/rain/timeout/events_filter 关键路径。
```
