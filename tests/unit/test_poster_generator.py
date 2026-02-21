"""tests/unit/test_poster_generator.py — PosterGenerator 单元测试"""

import json

import pytest
from unittest.mock import MagicMock

from gmp.output.poster_generator import (
    PosterGenerator,
    WEATHER_ICON_MAP,
    GROUP_META,
)


@pytest.fixture
def tmp_data_dir(tmp_path):
    """创建临时数据目录并写入测试数据"""
    vp_dir = tmp_path / "viewpoints" / "niubei_gongga"
    vp_dir.mkdir(parents=True)

    forecast = {
        "daily": [{
            "date": "2026-02-21",
            "events": [
                {"event_type": "sunrise_golden_mountain", "display_name": "日照金山", "score": 90},
                {"event_type": "cloud_sea", "display_name": "云海", "score": 75},
                {"event_type": "clear_sky", "display_name": "晴天", "score": 80},
            ],
        }],
    }
    (vp_dir / "forecast.json").write_text(
        json.dumps(forecast, ensure_ascii=False), encoding="utf-8"
    )

    timeline = {
        "hourly": [{"hour": h, "weather": {"weather_icon": "clear"}} for h in range(24)],
    }
    (vp_dir / "timeline_2026-02-21.json").write_text(
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


def test_pm_event_extraction(tmp_data_dir, mock_viewpoint_config):
    gen = PosterGenerator(str(tmp_data_dir))
    result = gen.generate(mock_viewpoint_config, days=1)
    pm = result["groups"][0]["viewpoints"][0]["daily"][0]["pm"]
    assert pm["event"] == "云海"
    assert pm["score"] == 75


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
