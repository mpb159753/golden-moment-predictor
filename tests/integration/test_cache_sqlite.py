"""SQLite 缓存集成测试

使用真实的临时 SQLite 数据库测试。
测试用例严格遵循 module-03-cache-fetcher.md §测试计划。
"""

from __future__ import annotations

import os
import tempfile
from datetime import date

import pytest

from gmp.cache.repository import CacheRepository
from gmp.db.init_db import init_database


@pytest.fixture
def db_path():
    """创建临时数据库文件"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_database(path)
    yield path
    os.unlink(path)


@pytest.fixture
def repo(db_path):
    """创建 CacheRepository 实例"""
    return CacheRepository(db_path)


# ─── 建表测试 ───────────────────────────────────────────────────────


class TestInitDatabase:
    """数据库初始化测试"""

    def test_init_db_creates_tables(self, db_path):
        """建表后表存在"""
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "weather_cache" in tables
        assert "prediction_history" in tables

    def test_init_db_creates_indexes(self, db_path):
        """建表后索引存在"""
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "idx_weather_cache_coord_date" in indexes
        assert "idx_prediction_history_viewpoint" in indexes

    def test_init_db_idempotent(self, db_path):
        """重复建表不报错 (IF NOT EXISTS)"""
        # 已在 fixture 中初始化一次，再次初始化不应报错
        init_database(db_path)

    def test_init_db_creates_directory(self, tmp_path):
        """自动创建父目录"""
        nested_path = str(tmp_path / "sub" / "dir" / "test.db")
        init_database(nested_path)

        import sqlite3
        conn = sqlite3.connect(nested_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "weather_cache" in tables


# ─── CRUD 测试 ──────────────────────────────────────────────────────


class TestCacheRepository:
    """CacheRepository CRUD 测试"""

    def test_upsert_and_query(self, repo):
        """插入后可查询"""
        target = date(2026, 2, 11)
        data = {
            "temperature_2m": 15.5,
            "cloud_cover_total": 20,
            "cloud_cover_low": 5,
            "cloud_cover_medium": 10,
            "cloud_cover_high": 5,
            "precipitation_probability": 10,
            "visibility": 25000,
            "wind_speed_10m": 5.0,
            "snowfall": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "weather_code": 0,
        }

        repo.upsert(29.75, 102.35, target, 8, data)
        result = repo.query(29.75, 102.35, target, [8])

        assert result is not None
        assert len(result) == 1
        assert result[0]["temperature_2m"] == 15.5
        assert result[0]["cloud_cover_total"] == 20

    def test_upsert_duplicate(self, repo):
        """重复插入更新 (REPLACE)"""
        target = date(2026, 2, 11)

        data1 = {"temperature_2m": 15.0, "cloud_cover_total": 20}
        repo.upsert(29.75, 102.35, target, 8, data1)

        data2 = {"temperature_2m": 18.5, "cloud_cover_total": 35}
        repo.upsert(29.75, 102.35, target, 8, data2)

        result = repo.query(29.75, 102.35, target, [8])
        assert result is not None
        assert len(result) == 1
        assert result[0]["temperature_2m"] == 18.5  # 更新后的值
        assert result[0]["cloud_cover_total"] == 35

    def test_coord_rounding_cache(self, repo):
        """相近坐标命中同一条缓存"""
        target = date(2026, 2, 11)

        data = {"temperature_2m": 15.0}
        # 插入坐标 29.7512, 102.3489 → 取整为 29.75, 102.35
        repo.upsert(29.7512, 102.3489, target, 8, data)

        # 用相近坐标查询 → 取整后相同
        result = repo.query(29.7523, 102.3451, target, [8])
        assert result is not None
        assert len(result) == 1

    def test_query_multiple_hours(self, repo):
        """查询多个小时的数据"""
        target = date(2026, 2, 11)

        for h in [6, 7, 8, 9, 10]:
            data = {"temperature_2m": 10.0 + h}
            repo.upsert(29.75, 102.35, target, h, data)

        result = repo.query(29.75, 102.35, target, [7, 8, 9])
        assert result is not None
        assert len(result) == 3

    def test_query_no_match(self, repo):
        """无匹配数据返回 None"""
        target = date(2026, 2, 11)
        result = repo.query(0.0, 0.0, target, [0])
        assert result is None


# ─── 预测历史测试 ───────────────────────────────────────────────────


class TestPredictionHistory:
    """预测历史保存和查询测试"""

    def test_save_and_load_prediction(self, repo):
        """预测历史保存和查询"""
        prediction = {
            "viewpoint_id": "niubei_gongga",
            "prediction_date": "2026-02-10",
            "target_date": "2026-02-11",
            "event_type": "sunrise",
            "predicted_score": 85,
            "predicted_status": "Recommended",
            "confidence": "high",
            "conditions_json": '{"cloud_cover": 10}',
            "actual_result": None,
            "user_feedback": None,
            "feedback_at": None,
        }

        repo.save_prediction(prediction)
        results = repo.get_history(
            "niubei_gongga",
            (date(2026, 2, 10), date(2026, 2, 12))
        )

        assert len(results) == 1
        assert results[0]["event_type"] == "sunrise"
        assert results[0]["predicted_score"] == 85
        assert results[0]["confidence"] == "high"

    def test_get_history_date_filter(self, repo):
        """日期范围过滤"""
        for i in range(5):
            prediction = {
                "viewpoint_id": "niubei_gongga",
                "prediction_date": "2026-02-10",
                "target_date": f"2026-02-{11 + i:02d}",
                "event_type": "sunrise",
                "predicted_score": 70 + i * 5,
                "predicted_status": "Possible",
                "confidence": "medium",
                "conditions_json": None,
                "actual_result": None,
                "user_feedback": None,
                "feedback_at": None,
            }
            repo.save_prediction(prediction)

        # 查询 2/11-2/13，应返回 3 条
        results = repo.get_history(
            "niubei_gongga",
            (date(2026, 2, 11), date(2026, 2, 13))
        )
        assert len(results) == 3

    def test_get_history_empty(self, repo):
        """无历史记录返回空列表"""
        results = repo.get_history(
            "nonexistent_vp",
            (date(2026, 1, 1), date(2026, 12, 31))
        )
        assert results == []
