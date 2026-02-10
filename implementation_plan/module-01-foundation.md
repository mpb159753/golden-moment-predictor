# M01 - 基础骨架与核心契约

## 1. 模块目标

构建 GMP 的最小可运行基础层，提供后续模块可复用的“统一语言”：

- 核心数据模型（`Viewpoint`、`Target`、`DataContext`、`ScoreResult` 等）
- 通用异常体系
- 引擎配置加载能力
- 项目目录骨架

---

## 2. 背景上下文（来自设计文档）

- 参考：`design/07-code-interface.md`、`design/01-architecture.md`
- 系统是 Plugin 驱动架构，后续模块都依赖统一 dataclass / Protocol。
- 配置必须外置（阈值、权重、并发、分页、缓存 TTL）。

---

## 3. 交付范围

### 本模块要做

1. 创建项目目录（`gmp/` 及子包）。
2. 实现 `core/models.py`（主要 dataclass）。
3. 实现 `core/exceptions.py`（异常与降级告警）。
4. 实现 `core/config_loader.py`（`EngineConfig` + YAML 读取）。
5. 提供默认配置文件 `config/engine_config.yaml`。

### 本模块不做

- 不实现具体天气拉取与缓存细节（M02）。
- 不实现天文/地理计算（M03）。
- 不实现评分逻辑（M05）。

---

## 4. 输入与输出契约

### 输入

- 文档定义的字段规范（`07-code-interface.md`）。
- 默认配置参数（`09-testing-config.md` 的 YAML 样例）。

### 输出

- 可被其他模块直接 import 的稳定接口：
  - `gmp/core/models.py`
  - `gmp/core/exceptions.py`
  - `gmp/core/config_loader.py`

---

## 5. 实施任务清单（建议顺序）

1. 创建目录骨架（含 `__init__.py`）：
   - `gmp/core`
   - `gmp/config/viewpoints`
   - `gmp/tests/unit`
2. 在 `core/models.py` 实现：
   - `Location`、`Target`、`Viewpoint`
   - `SunEvents`、`MoonStatus`、`StargazingWindow`
   - `AnalysisResult`、`ScoreResult`
   - `DataRequirement`、`DataContext`
3. 在 `core/exceptions.py` 实现：
   - `GMPError`
   - `APITimeoutError`
   - `InvalidCoordinateError`
   - `ViewpointNotFoundError`
   - `DataDegradedWarning`
4. 在 `core/config_loader.py` 实现：
   - `EngineConfig` dataclass
   - `load_engine_config(path)` 方法（YAML → dataclass）
5. 新建配置：
   - `gmp/config/engine_config.yaml`（参数与设计文档一致）

---

## 6. 验收标准

1. `models.py` 字段命名与设计文档一致；
2. `EngineConfig` 可成功加载 YAML，且具备默认值；
3. 异常类信息可读且可在 API 层映射；
4. 其它模块可直接 import，无循环依赖。

---

## 7. 测试清单

- `tests/unit/test_models.py`
  - dataclass 初始化与默认值测试
- `tests/unit/test_config_loader.py`
  - 正常加载、缺省值回退、非法字段报错
- `tests/unit/test_exceptions.py`
  - 错误消息格式与属性值

---

## 8. 新会话可直接使用的启动提示词

```text
请按 gmp_implementation_plan/module-01-foundation.md 完成模块 M01：
1) 创建 gmp 项目骨架；
2) 落地 core/models.py、core/exceptions.py、core/config_loader.py；
3) 提供 engine_config.yaml；
4) 编写并运行对应单测。
要求：严格对齐 design/07-code-interface.md 字段定义，完成后汇报文件清单与测试结果。
```
