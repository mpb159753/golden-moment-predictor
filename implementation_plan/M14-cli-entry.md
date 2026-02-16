# M14: CLI 入口

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** 实现 click CLI 入口，包括所有命令 (`predict`, `predict-route`, `generate-all`, `backtest`, `list-viewpoints`, `list-routes`)。

**依赖模块:** M07 (ConfigManager), M11 (输出层), M12 (GMPScheduler), M12B (BatchGenerator), M13 (Backtester)

---

## 背景

GMP 以 CLI 为唯一入口。所有命令通过 `python -m gmp.main` 或 `gmp` (安装后) 调用。

### 命令定义参考

[05-api.md §5.1](file:///Users/mpb/WorkSpace/golden-moment-predictor/design/05-api.md)

### 命令列表

```
gmp predict <viewpoint_id>     [--days N] [--events e1,e2] [--output json|table] [--detail] [--output-file path]
gmp predict-route <route_id>   [--days N] [--events e1,e2] [--output json|table]
gmp generate-all               [--days N] [--events e1,e2] [--fail-fast] [--no-archive] [--output dir] [--archive dir]
gmp backtest <viewpoint_id>    --date YYYY-MM-DD [--events e1,e2] [--save]
gmp list-viewpoints            [--output json|table]
gmp list-routes                [--output json|table]
```

---

## Task 1: CLI 入口与组件初始化

**Files:**
- Create: `gmp/main.py`
- Test: `tests/e2e/test_cli.py`

### 组件初始化工厂

```python
def create_scheduler(config_path: str = "config/engine_config.yaml") -> GMPScheduler:
    """创建 Scheduler 及其核心依赖组件

    1. ConfigManager(config_path)
    2. ViewpointConfig.load("config/viewpoints/")
    3. RouteConfig.load("config/routes/")
    4. CacheRepository(config.db_path)
    5. WeatherCache(repo, freshness_config)
    6. MeteoFetcher(cache, timeout_config)
    7. ScoreEngine() → 注册所有 Plugin
    8. AstroUtils()
    9. GeoUtils()
    10. GMPScheduler(核心组件)
    """

def create_batch_generator(
    scheduler: GMPScheduler,
    viewpoint_config: ViewpointConfig,
    route_config: RouteConfig,
    config: ConfigManager,
) -> BatchGenerator:
    """创建 BatchGenerator 及输出层组件

    1. ForecastReporter + TimelineReporter
    2. JSONFileWriter(output_dir, archive_dir)
    3. BatchGenerator(scheduler, viewpoint_config, route_config, reporters, writer)
    """

def _register_plugins(engine: ScoreEngine, config: ConfigManager) -> None:
    """注册所有评分 Plugin
    - GoldenMountainPlugin("sunrise_golden_mountain", config)
    - GoldenMountainPlugin("sunset_golden_mountain", config)
    - StargazingPlugin(config)
    - CloudSeaPlugin(config)
    - FrostPlugin(config)
    - SnowTreePlugin(config)
    - IceIciclePlugin(config)
    """
```

---

## Task 2: `predict` 命令

```python
@cli.command()
@click.argument("viewpoint_id")
@click.option("--days", default=7, type=click.IntRange(1, 16), help="预测天数 (1-16)")
@click.option("--events", default=None, help="逗号分隔的事件过滤")
@click.option("--output", "output_format", default="table", type=click.Choice(["json", "table"]))
@click.option("--detail", is_flag=True, help="显示评分明细")
@click.option("--output-file", default=None, type=click.Path(), help="输出 JSON 文件路径 (仅 --output json)")
@click.option("--config", default="config/engine_config.yaml", help="配置文件路径")
def predict(viewpoint_id, days, events, output_format, detail, output_file, config):
    """对指定观景台生成预测"""
    scheduler = create_scheduler(config)
    result = scheduler.run(viewpoint_id, days=days, events=events_list)

    if output_format == "json":
        forecast = ForecastReporter().generate(result)
        json_output = json.dumps(forecast, ensure_ascii=False, indent=2)
        if output_file:
            Path(output_file).write_text(json_output, encoding="utf-8")
            click.echo(f"已输出到: {output_file}")
        else:
            click.echo(json_output)
    else:
        formatter = CLIFormatter()
        if detail:
            click.echo(formatter.format_detail(result))
        else:
            click.echo(formatter.format_forecast(result))
```

---

## Task 3: `predict-route` 命令

```python
@cli.command("predict-route")
@click.argument("route_id")
@click.option("--days", default=7, type=click.IntRange(1, 16))
@click.option("--events", default=None)
@click.option("--output", "output_format", default="table", type=click.Choice(["json", "table"]))
@click.option("--config", default="config/engine_config.yaml")
def predict_route(route_id, days, events, output_format, config):
    """对指定线路生成预测"""
```

---

## Task 4: `generate-all` 命令

```python
@cli.command("generate-all")
@click.option("--days", default=7, type=click.IntRange(1, 16))
@click.option("--events", default=None)
@click.option("--fail-fast", is_flag=True, help="单站失败时立即中止")
@click.option("--no-archive", is_flag=True, help="跳过历史归档")
@click.option("--output", "output_dir", default="public/data", type=click.Path(), help="JSON 输出目录")
@click.option("--archive", "archive_dir", default="archive", type=click.Path(), help="历史归档目录")
@click.option("--config", default="config/engine_config.yaml")
def generate_all(days, events, fail_fast, no_archive, output_dir, archive_dir, config):
    """批量生成所有观景台和线路的预测 JSON 文件"""
    scheduler = create_scheduler(config)
    batch_gen = create_batch_generator(
        scheduler, viewpoint_config, route_config, config_manager
    )
    result = batch_gen.generate_all(
        days=days, events=events_list,
        fail_fast=fail_fast, no_archive=no_archive
    )
```

---

## Task 5: `backtest` 命令

```python
@cli.command()
@click.argument("viewpoint_id")
@click.option("--date", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--events", default=None)
@click.option("--save", is_flag=True, help="保存回测结果到数据库")
@click.option("--config", default="config/engine_config.yaml")
def backtest(viewpoint_id, date, events, save, config):
    """对历史日期进行回测"""
```

---

## Task 6: `list-viewpoints` 和 `list-routes`

```python
@cli.command("list-viewpoints")
@click.option("--output", "output_format", default="table", type=click.Choice(["json", "table"]))
@click.option("--config", default="config/engine_config.yaml")
def list_viewpoints(output_format, config):
    """列出所有可用观景台"""

@cli.command("list-routes")
@click.option("--output", "output_format", default="table", type=click.Choice(["json", "table"]))
@click.option("--config", default="config/engine_config.yaml")
def list_routes(output_format, config):
    """列出所有可用线路"""
```

---

## Task 7: 错误处理

```python
@cli.command()
def predict(...):
    try:
        ...
    except ViewpointNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
        raise SystemExit(1)
    except ServiceUnavailableError as e:
        click.echo(f"服务不可用: {e}", err=True)
        raise SystemExit(2)
    except GMPError as e:
        click.echo(f"GMP 错误: {e}", err=True)
        raise SystemExit(3)
```

---

## 应测试的内容

**E2E / CLI 测试 (使用 `click.testing.CliRunner`):**

- `gmp predict niubei_gongga --days 1` → 正常输出
- `gmp predict niubei_gongga --output json` → 有效 JSON
- `gmp predict niubei_gongga --output json --output-file out.json` → 写入文件
- `gmp predict 不存在的id` → 错误提示, exit code=1
- `gmp predict-route lixiao --days 3` → 线路预测
- `gmp list-viewpoints` → 显示所有观景台
- `gmp list-routes` → 显示所有线路
- `gmp backtest niubei_gongga --date 2025-12-01` → 回测输出
- `gmp generate-all --days 1` → 生成 JSON 文件
- `gmp generate-all --no-archive` → 跳过归档
- `gmp generate-all --output ./custom/data --archive ./custom/archive` → 自定义路径
- `--config` 参数可指定不同配置文件

---

## 验证命令

```bash
# CLI 集成测试
python -m pytest tests/e2e/test_cli.py -v

# 手动测试 (需真实 API 或完整 Mock)
python -m gmp.main predict niubei_gongga --days 1
python -m gmp.main list-viewpoints
```
