"""tests/e2e/test_cli.py — CLI 集成测试

使用 click.testing.CliRunner 测试所有 CLI 命令。
所有外部依赖 (Scheduler, Fetcher, etc.) 通过 mock create_scheduler 隔离。
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gmp.core.models import (
    ForecastDay,
    Location,
    PipelineResult,
    Route,
    RouteStop,
    ScoreResult,
    Viewpoint,
)


# ==================== Fixtures ====================


@pytest.fixture()
def runner():
    return CliRunner()


def _make_viewpoint(vid: str = "niubei", name: str = "牛背山") -> Viewpoint:
    return Viewpoint(
        id=vid,
        name=name,
        location=Location(lat=29.75, lon=102.35, altitude=3660),
        capabilities=["sunrise", "cloud_sea"],
        targets=[],
    )


def _make_pipeline_result(viewpoint: Viewpoint | None = None) -> PipelineResult:
    vp = viewpoint or _make_viewpoint()
    return PipelineResult(
        viewpoint=vp,
        forecast_days=[
            ForecastDay(
                date="2026-02-15",
                summary="测试摘要",
                best_event=ScoreResult(
                    event_type="sunrise_golden_mountain",
                    total_score=90,
                    status="Recommended",
                    breakdown={"light_path": {"score": 35, "max": 35}},
                    time_window="07:15 - 07:45",
                    confidence="High",
                    highlights=["东方少云 ☀️"],
                ),
                events=[
                    ScoreResult(
                        event_type="sunrise_golden_mountain",
                        total_score=90,
                        status="Recommended",
                        breakdown={"light_path": {"score": 35, "max": 35}},
                        time_window="07:15 - 07:45",
                        confidence="High",
                        highlights=["东方少云 ☀️"],
                    ),
                ],
                confidence="High",
            ),
        ],
        meta={"generated_at": "2026-02-15T05:00:00+08:00"},
    )


def _make_route() -> Route:
    return Route(
        id="lixiao",
        name="理小路",
        stops=[
            RouteStop(viewpoint_id="zheduo", order=1, stay_note="建议停留2小时"),
            RouteStop(viewpoint_id="niubei", order=2, stay_note="建议停留3小时"),
        ],
    )


def _mock_scheduler():
    """创建 mock scheduler，模拟 run / run_route 行为"""
    scheduler = MagicMock()
    scheduler.run.return_value = _make_pipeline_result()
    scheduler.run_route.return_value = [
        _make_pipeline_result(_make_viewpoint("zheduo", "折多山")),
        _make_pipeline_result(_make_viewpoint("niubei", "牛背山")),
    ]
    return scheduler


def _mock_viewpoint_config():
    """创建 mock viewpoint_config"""
    config = MagicMock()
    vp1 = _make_viewpoint("niubei", "牛背山")
    vp2 = _make_viewpoint("zheduo", "折多山")
    config.list_all.return_value = [vp1, vp2]
    config.get.side_effect = lambda vid: (
        vp1 if vid == "niubei" else vp2
    )
    return config


def _mock_route_config():
    """创建 mock route_config"""
    config = MagicMock()
    route = _make_route()
    config.list_all.return_value = [route]
    config.get.return_value = route
    return config


# ==================== Task 1: CLI 入口与组件初始化 ====================


class TestCLIGroup:
    """测试 CLI group 基本功能"""

    def test_cli_help(self, runner):
        """gmp --help 应正常输出帮助信息"""
        from gmp.main import cli

        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "GMP" in result.output

    def test_cli_has_predict_command(self, runner):
        """cli group 应包含 predict 命令"""
        from gmp.main import cli

        result = runner.invoke(cli, ["predict", "--help"])
        assert result.exit_code == 0
        assert "viewpoint_id" in result.output.lower() or "VIEWPOINT_ID" in result.output

    def test_cli_has_predict_route_command(self, runner):
        """cli group 应包含 predict-route 命令"""
        from gmp.main import cli

        result = runner.invoke(cli, ["predict-route", "--help"])
        assert result.exit_code == 0

    def test_cli_has_generate_all_command(self, runner):
        """cli group 应包含 generate-all 命令"""
        from gmp.main import cli

        result = runner.invoke(cli, ["generate-all", "--help"])
        assert result.exit_code == 0

    def test_cli_has_backtest_command(self, runner):
        """cli group 应包含 backtest 命令"""
        from gmp.main import cli

        result = runner.invoke(cli, ["backtest", "--help"])
        assert result.exit_code == 0

    def test_cli_has_list_viewpoints_command(self, runner):
        """cli group 应包含 list-viewpoints 命令"""
        from gmp.main import cli

        result = runner.invoke(cli, ["list-viewpoints", "--help"])
        assert result.exit_code == 0

    def test_cli_has_list_routes_command(self, runner):
        """cli group 应包含 list-routes 命令"""
        from gmp.main import cli

        result = runner.invoke(cli, ["list-routes", "--help"])
        assert result.exit_code == 0


# ==================== Task 2: predict 命令 ====================


class TestPredictCommand:
    """测试 predict 命令"""

    @patch("gmp.main.create_scheduler")
    def test_predict_table_output(self, mock_create, runner):
        """gmp predict niubei --days 1 → 正常表格输出"""
        mock_create.return_value = _mock_scheduler()
        from gmp.main import cli

        result = runner.invoke(cli, ["predict", "niubei", "--days", "1"])
        assert result.exit_code == 0
        assert "牛背山" in result.output

    @patch("gmp.main.create_scheduler")
    def test_predict_json_output(self, mock_create, runner):
        """gmp predict niubei --output json → 有效 JSON"""
        mock_create.return_value = _mock_scheduler()
        from gmp.main import cli

        result = runner.invoke(cli, ["predict", "niubei", "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "viewpoint_id" in data

    @patch("gmp.main.create_scheduler")
    def test_predict_json_output_file(self, mock_create, runner, tmp_path):
        """gmp predict niubei --output json --output-file out.json → 写入文件"""
        mock_create.return_value = _mock_scheduler()
        from gmp.main import cli

        out_file = str(tmp_path / "out.json")
        result = runner.invoke(
            cli,
            ["predict", "niubei", "--output", "json", "--output-file", out_file],
        )
        assert result.exit_code == 0
        assert "已输出到" in result.output
        with open(out_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "viewpoint_id" in data

    @patch("gmp.main.create_scheduler")
    def test_predict_detail_output(self, mock_create, runner):
        """gmp predict niubei --detail → 详细输出"""
        mock_create.return_value = _mock_scheduler()
        from gmp.main import cli

        result = runner.invoke(cli, ["predict", "niubei", "--detail"])
        assert result.exit_code == 0
        assert "Score:" in result.output
        assert "📊 Breakdown:" in result.output
        assert "light_path" in result.output

    @patch("gmp.main._create_core_components")
    def test_predict_with_events_filter(self, mock_components, runner):
        """gmp predict niubei --events sunrise_golden_mountain → 带事件过滤"""
        scheduler = _mock_scheduler()
        mock_engine = MagicMock()
        mock_engine.display_names = {}
        mock_components.return_value = (
            scheduler,
            _mock_viewpoint_config(),
            _mock_route_config(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            mock_engine,
        )
        from gmp.main import cli

        result = runner.invoke(
            cli,
            ["predict", "niubei", "--events", "sunrise_golden_mountain,cloud_sea"],
        )
        assert result.exit_code == 0
        # 确认 events 被解析传到 scheduler
        scheduler.run.assert_called_once()
        call_kwargs = scheduler.run.call_args
        assert "sunrise_golden_mountain" in call_kwargs.kwargs.get("events", []) or \
               "sunrise_golden_mountain" in (call_kwargs.args[1] if len(call_kwargs.args) > 1 else [])


# ==================== Task 3: predict-route 命令 ====================


class TestPredictRouteCommand:
    """测试 predict-route 命令"""

    @patch("gmp.main._create_core_components")
    def test_predict_route_table(self, mock_components, runner):
        """gmp predict-route lixiao --days 3 → 正常表格输出"""
        scheduler = _mock_scheduler()
        mock_engine = MagicMock()
        mock_engine.display_names = {}
        mock_components.return_value = (
            scheduler,
            _mock_viewpoint_config(),
            _mock_route_config(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            mock_engine,
        )
        from gmp.main import cli

        result = runner.invoke(cli, ["predict-route", "lixiao", "--days", "3"])
        assert result.exit_code == 0
        assert "线路:" in result.output
        assert "理小路" in result.output

    @patch("gmp.main._create_core_components")
    def test_predict_route_json(self, mock_components, runner):
        """gmp predict-route lixiao --output json → 有效 JSON"""
        scheduler = _mock_scheduler()
        mock_engine = MagicMock()
        mock_engine.display_names = {}
        mock_components.return_value = (
            scheduler,
            _mock_viewpoint_config(),
            _mock_route_config(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            mock_engine,
        )
        from gmp.main import cli

        result = runner.invoke(cli, ["predict-route", "lixiao", "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "route_id" in data


# ==================== Task 4: generate-all 命令 ====================


class TestGenerateAllCommand:
    """测试 generate-all 命令"""

    @patch("gmp.main.create_batch_generator")
    @patch("gmp.main._create_core_components")
    def test_generate_all_basic(self, mock_components, mock_create_bg, runner):
        """gmp generate-all --days 1 → 生成成功输出摘要"""
        scheduler = _mock_scheduler()
        mock_engine = MagicMock()
        mock_engine.display_names = {}
        mock_components.return_value = (
            scheduler,
            _mock_viewpoint_config(),
            _mock_route_config(),
            MagicMock(),  # config_manager
            MagicMock(),  # repo
            MagicMock(),  # fetcher
            mock_engine,  # engine
        )
        batch_gen = MagicMock()
        batch_gen.generate_all.return_value = {
            "viewpoints_processed": 2,
            "routes_processed": 1,
            "failed_viewpoints": [],
            "failed_routes": [],
            "output_dir": "public/data",
            "archive_dir": "2026-02-15T05-00",
        }
        mock_create_bg.return_value = batch_gen
        from gmp.main import cli

        result = runner.invoke(cli, ["generate-all", "--days", "1"])
        assert result.exit_code == 0
        assert "生成完成" in result.output
        assert "观景台: 2 成功" in result.output
        assert "线路: 1 成功" in result.output

    @patch("gmp.main.create_batch_generator")
    @patch("gmp.main._create_core_components")
    def test_generate_all_no_archive(self, mock_components, mock_create_bg, runner):
        """gmp generate-all --no-archive → no_archive=True 传递到 batch_gen"""
        scheduler = _mock_scheduler()
        mock_engine = MagicMock()
        mock_engine.display_names = {}
        mock_components.return_value = (
            scheduler,
            _mock_viewpoint_config(),
            _mock_route_config(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            mock_engine,
        )
        batch_gen = MagicMock()
        batch_gen.generate_all.return_value = {
            "viewpoints_processed": 0,
            "routes_processed": 0,
            "failed_viewpoints": [],
            "failed_routes": [],
            "output_dir": "public/data",
            "archive_dir": None,
        }
        mock_create_bg.return_value = batch_gen
        from gmp.main import cli

        result = runner.invoke(cli, ["generate-all", "--no-archive"])
        assert result.exit_code == 0
        # 验证 no_archive 参数已传递
        call_kwargs = batch_gen.generate_all.call_args.kwargs
        assert call_kwargs["no_archive"] is True

    @patch("gmp.main.create_batch_generator")
    @patch("gmp.main._create_core_components")
    def test_generate_all_custom_paths(self, mock_components, mock_create_bg, runner):
        """gmp generate-all --output ./custom/data --archive ./custom/archive → 自定义路径"""
        scheduler = _mock_scheduler()
        mock_engine = MagicMock()
        mock_engine.display_names = {}
        mock_components.return_value = (
            scheduler,
            _mock_viewpoint_config(),
            _mock_route_config(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            mock_engine,
        )
        batch_gen = MagicMock()
        batch_gen.generate_all.return_value = {
            "viewpoints_processed": 0,
            "routes_processed": 0,
            "failed_viewpoints": [],
            "failed_routes": [],
            "output_dir": "./custom/data",
            "archive_dir": None,
        }
        mock_create_bg.return_value = batch_gen
        from gmp.main import cli

        result = runner.invoke(
            cli,
            ["generate-all", "--output", "./custom/data", "--archive", "./custom/archive"],
        )
        assert result.exit_code == 0
        # 验证自定义路径传递到 create_batch_generator
        bg_call_kwargs = mock_create_bg.call_args.kwargs
        assert bg_call_kwargs["output_dir"] == "./custom/data"
        assert bg_call_kwargs["archive_dir"] == "./custom/archive"


# ==================== Task 5: backtest 命令 ====================


class TestBacktestCommand:
    """测试 backtest 命令"""

    @patch("gmp.main.create_scheduler")
    @patch("gmp.main.create_backtester")
    def test_backtest_basic(self, mock_create_bt, mock_create_sched, runner):
        """gmp backtest niubei --date 2025-12-01 → 回测输出"""
        mock_create_sched.return_value = _mock_scheduler()
        backtester = MagicMock()
        backtester.run.return_value = {
            "viewpoint_id": "niubei",
            "target_date": "2025-12-01",
            "is_backtest": True,
            "data_source": "cache",
            "events": [],
        }
        mock_create_bt.return_value = backtester
        from gmp.main import cli

        result = runner.invoke(cli, ["backtest", "niubei", "--date", "2025-12-01"])
        assert result.exit_code == 0


# ==================== Task 6: list 命令 ====================


class TestListCommands:
    """测试 list-viewpoints 和 list-routes 命令"""

    @patch("gmp.main.create_scheduler")
    def test_list_viewpoints_table(self, mock_create, runner):
        """gmp list-viewpoints → 显示所有观景台"""
        mock_create.return_value = _mock_scheduler()
        from gmp.main import cli

        with patch("gmp.main._load_configs") as mock_configs:
            mock_configs.return_value = (
                _mock_viewpoint_config(),
                _mock_route_config(),
                MagicMock(),  # config_manager
            )
            result = runner.invoke(cli, ["list-viewpoints"])
        assert result.exit_code == 0
        assert "牛背山" in result.output

    @patch("gmp.main.create_scheduler")
    def test_list_viewpoints_json(self, mock_create, runner):
        """gmp list-viewpoints --output json → 有效 JSON"""
        mock_create.return_value = _mock_scheduler()
        from gmp.main import cli

        with patch("gmp.main._load_configs") as mock_configs:
            mock_configs.return_value = (
                _mock_viewpoint_config(),
                _mock_route_config(),
                MagicMock(),
            )
            result = runner.invoke(cli, ["list-viewpoints", "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2

    @patch("gmp.main.create_scheduler")
    def test_list_routes_table(self, mock_create, runner):
        """gmp list-routes → 显示所有线路"""
        mock_create.return_value = _mock_scheduler()
        from gmp.main import cli

        with patch("gmp.main._load_configs") as mock_configs:
            mock_configs.return_value = (
                _mock_viewpoint_config(),
                _mock_route_config(),
                MagicMock(),
            )
            result = runner.invoke(cli, ["list-routes"])
        assert result.exit_code == 0
        assert "理小路" in result.output


# ==================== Task 7: 错误处理 ====================


class TestErrorHandling:
    """测试错误处理"""

    @patch("gmp.main.create_scheduler")
    def test_predict_not_found_viewpoint(self, mock_create, runner):
        """gmp predict 不存在的id → 错误提示, exit code=1"""
        from gmp.core.exceptions import ViewpointNotFoundError

        scheduler = _mock_scheduler()
        scheduler.run.side_effect = ViewpointNotFoundError("不存在的id")
        mock_create.return_value = scheduler
        from gmp.main import cli

        result = runner.invoke(cli, ["predict", "不存在的id"])
        assert result.exit_code == 1
        assert "错误" in result.output or "未找到" in result.output

    @patch("gmp.main._create_core_components")
    def test_predict_service_unavailable(self, mock_components, runner):
        """服务不可用 → exit code=2"""
        from gmp.core.exceptions import ServiceUnavailableError

        scheduler = _mock_scheduler()
        scheduler.run.side_effect = ServiceUnavailableError("API 超时")
        mock_engine = MagicMock()
        mock_engine.display_names = {}
        mock_components.return_value = (
            scheduler,
            _mock_viewpoint_config(),
            _mock_route_config(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            mock_engine,
        )
        from gmp.main import cli

        result = runner.invoke(cli, ["predict", "niubei"])
        assert result.exit_code == 2

    @patch("gmp.main._create_core_components")
    def test_predict_generic_gmp_error(self, mock_components, runner):
        """通用 GMPError → exit code=3"""
        from gmp.core.exceptions import GMPError

        scheduler = _mock_scheduler()
        scheduler.run.side_effect = GMPError("未知错误")
        mock_engine = MagicMock()
        mock_engine.display_names = {}
        mock_components.return_value = (
            scheduler,
            _mock_viewpoint_config(),
            _mock_route_config(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            mock_engine,
        )
        from gmp.main import cli

        result = runner.invoke(cli, ["predict", "niubei"])
        assert result.exit_code == 3
