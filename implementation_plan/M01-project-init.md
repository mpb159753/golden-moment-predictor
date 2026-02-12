# M01: 项目初始化与基础设施

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建项目骨架、虚拟环境、安装依赖、配置开发工具

**依赖模块:** 无（第一个执行的模块）

---

## 背景

GMP (Golden Moment Predictor) 是一个 Python CLI 工具，用于预测川西高原景观最佳观赏时刻。采用 Plugin 驱动架构，通过 Open-Meteo API 获取天气数据，结合天文/地理计算，输出 JSON 预测文件。

---

## Task 1: 创建项目目录结构

**Files:**
- Create: 项目根目录下的完整目录骨架

**Step 1: 创建目录结构**

```bash
mkdir -p gmp/{core,data,cache,scoring/plugins,output,backtest}
mkdir -p tests/{unit,integration,backtest,e2e,fixtures}
mkdir -p config
```

最终目录结构:
```
gmp/
├── __init__.py
├── main.py                        # CLI 入口 (M14)
├── core/
│   ├── __init__.py
│   ├── models.py                  # 数据模型 (M02)
│   ├── exceptions.py              # 异常定义 (M02)
│   ├── config_loader.py           # 配置加载 (M07)
│   └── scheduler.py               # 调度器 (M12)
├── data/
│   ├── __init__.py
│   ├── meteo_fetcher.py           # 气象获取 (M06)
│   ├── astro_utils.py             # 天文计算 (M04)
│   └── geo_utils.py               # 地理计算 (M03)
├── cache/
│   ├── __init__.py
│   ├── weather_cache.py           # 缓存管理 (M05)
│   └── repository.py              # DB 操作 (M05)
├── scoring/
│   ├── __init__.py
│   ├── engine.py                  # ScoreEngine (M08)
│   ├── models.py                  # DataContext 等 (M08)
│   └── plugins/
│       ├── __init__.py
│       ├── golden_mountain.py     # M10
│       ├── stargazing.py          # M10
│       ├── cloud_sea.py           # M09
│       ├── frost.py               # M09
│       ├── snow_tree.py           # M09
│       └── ice_icicle.py          # M09
├── output/
│   ├── __init__.py
│   ├── forecast_reporter.py       # M11
│   ├── timeline_reporter.py       # M11
│   ├── cli_formatter.py           # M11
│   ├── summary_generator.py       # M11
│   └── json_file_writer.py        # M11
└── backtest/
    ├── __init__.py
    └── backtester.py              # M13

tests/
├── __init__.py
├── conftest.py                    # 共享 fixtures
├── unit/
│   └── __init__.py
├── integration/
│   └── __init__.py
├── backtest/
│   └── __init__.py
├── e2e/
│   └── __init__.py
└── fixtures/
    ├── weather_data_clear.json
    ├── weather_data_rainy.json
    └── viewpoint_niubei.yaml

config/
├── engine_config.yaml             # M07
├── viewpoints/
│   └── niubei_gongga.yaml         # M07
└── routes/
    └── lixiao.yaml                # M07
```

**Step 2: 创建所有 `__init__.py`**

在每个包目录下创建空 `__init__.py` 文件。

**Step 3: Commit**

```bash
git add -A && git commit -m "chore(M01): create project directory skeleton"
```

---

## Task 2: 创建虚拟环境与依赖配置

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pyproject.toml`

**Step 1: 创建 `requirements.txt`**

```
click>=8.0
structlog>=23.0
pandas>=2.0
ephem>=4.0
httpx>=0.25
pyyaml>=6.0
```

**Step 2: 创建 `requirements-dev.txt`**

```
-r requirements.txt
pytest>=7.0
pytest-cov>=4.0
```

**Step 3: 创建 `pyproject.toml`**

```toml
[project]
name = "gmp"
version = "4.0.0"
description = "川西旅行景观预测引擎"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[project.scripts]
gmp = "gmp.main:cli"
```

**Step 4: 创建并激活虚拟环境**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

**Step 5: 验证**

```bash
python -c "import click, structlog, pandas, ephem, httpx, yaml; print('All deps OK')"
pytest --version
```

**Step 6: Commit**

```bash
git add -A && git commit -m "chore(M01): add dependencies and pyproject.toml"
```

---

## Task 3: 配置开发工具

**Files:**
- Create: `.gitignore` (如不存在则更新)

**Step 1: 确保 `.gitignore` 包含必要条目**

检查已有 `.gitignore`，如缺少以下内容则补充：
```
venv/
__pycache__/
*.pyc
.pytest_cache/
data/gmp.db
public/
archive/
*.egg-info/
dist/
build/
```

**Step 2: Commit**

```bash
git add -A && git commit -m "chore(M01): update .gitignore"
```

---

## 验证清单

- [ ] `venv/bin/python` 可用
- [ ] 所有依赖导入成功
- [ ] `pytest` 可执行（0 tests collected 正常）
- [ ] 目录结构与设计文档 `07-code-interface.md §7.4` 一致
