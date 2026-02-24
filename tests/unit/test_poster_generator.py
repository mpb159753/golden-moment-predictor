"""tests/unit/test_poster_generator.py — PosterGenerator 单元测试"""

import json
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import MagicMock

from gmp.output.poster_generator import (
    PosterGenerator,
    WEATHER_ICON_MAP,
    GROUP_META,
)

_CST = timezone(timedelta(hours=8))


@pytest.fixture
def tmp_data_dir(tmp_path):
    """创建临时数据目录并写入测试数据。

    日期必须与 generate() 内部 datetime.now() 一致，
    所以动态计算而不是硬编码。
    """
    today = datetime.now(_CST).strftime("%Y-%m-%d")

    vp_dir = tmp_path / "viewpoints" / "niubei_gongga"
    vp_dir.mkdir(parents=True)

    forecast = {
        "daily": [{
            "date": today,
            "events": [
                {
                    "event_type": "sunrise_golden_mountain",
                    "display_name": "日照金山",
                    "score": 90,
                    "score_breakdown": {
                        "light_path": {"score": 30, "max": 35, "detail": "cloud=10%"},
                        "target_visible": {"score": 35, "max": 40, "detail": "cloud=5%"},
                        "local_clear": {"score": 25, "max": 25, "detail": "cloud=12%"},
                    },
                },
                {
                    "event_type": "cloud_sea",
                    "display_name": "云海",
                    "score": 75,
                    "score_breakdown": {
                        "base_cloud": {"score": 40, "max": 50, "detail": "low_cloud=65%"},
                    },
                },
                {
                    "event_type": "clear_sky",
                    "display_name": "晴天",
                    "score": 80,
                    "score_breakdown": {
                        "cloud_cover": {"score": 40, "max": 50, "detail": "avg_cloud=15%"},
                        "precipitation": {"score": 25, "max": 25, "detail": "precipitation probability scoring"},
                        "visibility": {"score": 15, "max": 25, "detail": "visibility scoring"},
                    },
                },
            ],
        }],
    }
    (vp_dir / "forecast.json").write_text(
        json.dumps(forecast, ensure_ascii=False), encoding="utf-8"
    )

    timeline = {
        "hourly": [{"hour": h, "weather": {"weather_icon": "clear"}} for h in range(24)],
    }
    (vp_dir / f"timeline_{today}.json").write_text(
        json.dumps(timeline), encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def mock_viewpoint_config():
    vp = MagicMock()
    vp.id = "niubei_gongga"
    vp.name = "牛背山"
    vp.groups = ["gongga"]
    config = MagicMock()
    config.list_all.return_value = [vp]
    return config


def test_generate_basic_structure(tmp_data_dir, mock_viewpoint_config):
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(mock_viewpoint_config, days=1)
    assert "generated_at" in result
    assert "days" in result
    assert "groups" in result
    assert len(result["groups"]) >= 1


def test_am_event_extraction(tmp_data_dir, mock_viewpoint_config):
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(mock_viewpoint_config, days=1)
    am = result["groups"][0]["viewpoints"][0]["daily"][0]["am"]
    assert am["event"] == "日照金山"
    assert am["score"] == 90
    assert "conditions" in am


def test_pm_event_extraction(tmp_data_dir, mock_viewpoint_config):
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(mock_viewpoint_config, days=1)
    pm = result["groups"][0]["viewpoints"][0]["daily"][0]["pm"]
    assert pm["event"] == "云海"
    assert pm["score"] == 75
    assert "conditions" in pm


def test_am_conditions_passthrough(tmp_data_dir, mock_viewpoint_config):
    """日照金山 score_breakdown → conditions 原样透传"""
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(mock_viewpoint_config, days=1)
    am = result["groups"][0]["viewpoints"][0]["daily"][0]["am"]
    conditions = am["conditions"]
    assert "light_path" in conditions
    assert "target_visible" in conditions
    assert "local_clear" in conditions
    assert conditions["light_path"]["detail"] == "cloud=10%"


def test_pm_conditions_passthrough(tmp_data_dir, mock_viewpoint_config):
    """云海 score_breakdown → conditions 原样透传"""
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(mock_viewpoint_config, days=1)
    pm = result["groups"][0]["viewpoints"][0]["daily"][0]["pm"]
    assert "base_cloud" in pm["conditions"]


def test_clear_sky_fallback_includes_conditions(tmp_path):
    """无专属事件时，clear_sky fallback 的 conditions 也应被透传"""
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

    vp_dir = tmp_path / "viewpoints" / "test_vp"
    vp_dir.mkdir(parents=True)

    # 只有 clear_sky，无 AM/PM 专属事件
    forecast = {
        "daily": [{
            "date": today,
            "events": [
                {
                    "event_type": "clear_sky",
                    "display_name": "晴天",
                    "score": 70,
                    "score_breakdown": {
                        "cloud_cover": {"score": 30, "max": 50, "detail": "avg_cloud=22%"},
                    },
                }
            ],
        }],
    }
    (vp_dir / "forecast.json").write_text(
        __import__("json").dumps(forecast, ensure_ascii=False), encoding="utf-8"
    )
    (vp_dir / f"timeline_{today}.json").write_text(
        __import__("json").dumps({"hourly": []}), encoding="utf-8"
    )

    vp = MagicMock()
    vp.id = "test_vp"
    vp.name = "测试点"
    vp.groups = ["other"]
    config = MagicMock()
    config.list_all.return_value = [vp]

    gen = PosterGenerator(str(tmp_path))
    result = gen.generate(config, days=1)
    am = result["groups"][0]["viewpoints"][0]["daily"][0]["am"]
    # fallback 场景：event 为空，score 非零，conditions 含 clear_sky breakdown
    assert am["event"] == ""
    assert am["score"] == 70
    assert "cloud_cover" in am["conditions"]


def test_no_breakdown_returns_empty_conditions(tmp_path):
    """事件无 score_breakdown 字段时，conditions 应为空 dict，不报错"""
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

    vp_dir = tmp_path / "viewpoints" / "bare_vp"
    vp_dir.mkdir(parents=True)

    forecast = {
        "daily": [{
            "date": today,
            "events": [
                # 故意不包含 score_breakdown
                {"event_type": "sunrise_golden_mountain", "display_name": "日照金山", "score": 85},
            ],
        }],
    }
    (vp_dir / "forecast.json").write_text(
        __import__("json").dumps(forecast, ensure_ascii=False), encoding="utf-8"
    )
    (vp_dir / f"timeline_{today}.json").write_text(
        __import__("json").dumps({"hourly": []}), encoding="utf-8"
    )

    vp = MagicMock()
    vp.id = "bare_vp"
    vp.name = "无 breakdown 景点"
    vp.groups = ["other"]
    config = MagicMock()
    config.list_all.return_value = [vp]

    gen = PosterGenerator(str(tmp_path))
    result = gen.generate(config, days=1)
    am = result["groups"][0]["viewpoints"][0]["daily"][0]["am"]
    assert am["conditions"] == {}


def test_weather_mapping():
    assert WEATHER_ICON_MAP["clear"] == "晴天"
    assert WEATHER_ICON_MAP["cloudy"] == "阴天"
    assert WEATHER_ICON_MAP["snow"] == "雪"


def test_missing_data_graceful(tmp_path):
    vp = MagicMock()
    vp.id = "nonexistent"
    vp.name = "不存在"
    vp.groups = ["other"]
    config = MagicMock()
    config.list_all.return_value = [vp]
    gen = PosterGenerator(str(tmp_path))
    result = gen.generate(config, days=1)
    assert len(result["groups"]) >= 1


def test_multi_group_viewpoint(tmp_data_dir):
    vp = MagicMock()
    vp.id = "niubei_gongga"
    vp.name = "牛背山"
    vp.groups = ["gongga", "318"]
    config = MagicMock()
    config.list_all.return_value = [vp]
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(config, days=1)
    group_keys = [g["key"] for g in result["groups"]]
    assert "gongga" in group_keys
    assert "318" in group_keys
