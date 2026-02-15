"""tests/unit/test_cache_repository.py — CacheRepository 单元测试

测试 SQLite 缓存数据库的底层操作层。
"""

from datetime import date, datetime

import pytest

from gmp.cache.repository import CacheRepository


# ==================== Fixtures ====================


@pytest.fixture
def repo(tmp_path):
    """使用临时文件创建 CacheRepository 实例"""
    db_path = str(tmp_path / "test_cache.db")
    r = CacheRepository(db_path)
    yield r
    r.close()


@pytest.fixture
def memory_repo():
    """使用 :memory: 创建 CacheRepository 实例"""
    r = CacheRepository(":memory:")
    yield r
    r.close()


# ==================== 自动建表 ====================


class TestAutoCreateTables:
    def test_creates_weather_cache_table(self, memory_repo):
        """创建数据库时自动建 weather_cache 表"""
        cursor = memory_repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='weather_cache'"
        )
        assert cursor.fetchone() is not None

    def test_creates_prediction_history_table(self, memory_repo):
        """创建数据库时自动建 prediction_history 表"""
        cursor = memory_repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='prediction_history'"
        )
        assert cursor.fetchone() is not None

    def test_creates_tables_with_file_path(self, repo):
        """使用文件路径也能自动建表"""
        cursor = repo._conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        )
        count = cursor.fetchone()[0]
        assert count >= 2


# ==================== upsert_weather + query_weather ====================


class TestWeatherReadWrite:
    def test_upsert_and_query_roundtrip(self, memory_repo):
        """完整读写循环: upsert → query 返回相同数据"""
        data = {
            "fetched_at": "2026-02-10 08:00:00",
            "temperature_2m": -12.3,
            "cloud_cover_total": 15,
            "cloud_cover_low": 5,
            "cloud_cover_medium": 8,
            "cloud_cover_high": 2,
            "cloud_base_altitude": 5200.0,
            "precipitation_probability": 0,
            "visibility": 45000.0,
            "wind_speed_10m": 8.5,
            "snowfall": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "weather_code": 0,
        }
        memory_repo.upsert_weather(29.58, 101.88, date(2026, 2, 11), 6, data)
        result = memory_repo.query_weather(29.58, 101.88, date(2026, 2, 11))
        assert result is not None
        assert len(result) == 1
        row = result[0]
        assert row["temperature_2m"] == pytest.approx(-12.3)
        assert row["cloud_cover_total"] == 15
        assert row["forecast_hour"] == 6

    def test_coordinate_auto_rounding(self, memory_repo):
        """坐标自动 ROUND(2): 29.756 → 29.76"""
        data = {
            "fetched_at": "2026-02-10 08:00:00",
            "temperature_2m": -5.0,
            "cloud_cover_total": 20,
            "cloud_cover_low": 10,
            "cloud_cover_medium": 5,
            "cloud_cover_high": 5,
            "cloud_base_altitude": 3000.0,
            "precipitation_probability": 10,
            "visibility": 30000.0,
            "wind_speed_10m": 5.0,
            "snowfall": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "weather_code": 1,
        }
        # 写入时使用 29.756 (→ round 到 29.76)
        memory_repo.upsert_weather(29.756, 101.884, date(2026, 2, 11), 6, data)
        # 用四舍五入后的值查询
        result = memory_repo.query_weather(29.76, 101.88, date(2026, 2, 11))
        assert result is not None
        assert len(result) == 1

    def test_hours_filter(self, memory_repo):
        """hours 过滤: 只返回指定小时的数据"""
        base_data = {
            "fetched_at": "2026-02-10 08:00:00",
            "temperature_2m": 0.0,
            "cloud_cover_total": 10,
            "cloud_cover_low": 0,
            "cloud_cover_medium": 0,
            "cloud_cover_high": 0,
            "cloud_base_altitude": 5000.0,
            "precipitation_probability": 0,
            "visibility": 50000.0,
            "wind_speed_10m": 3.0,
            "snowfall": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "weather_code": 0,
        }
        for hour in range(24):
            memory_repo.upsert_weather(29.58, 101.88, date(2026, 2, 11), hour, base_data)

        result = memory_repo.query_weather(
            29.58, 101.88, date(2026, 2, 11), hours=[6, 7, 8]
        )
        assert result is not None
        assert len(result) == 3
        hours = [r["forecast_hour"] for r in result]
        assert sorted(hours) == [6, 7, 8]

    def test_upsert_overwrites_existing(self, memory_repo):
        """重复插入覆盖旧数据"""
        data1 = {
            "fetched_at": "2026-02-10 08:00:00",
            "temperature_2m": -12.0,
            "cloud_cover_total": 15,
            "cloud_cover_low": 5,
            "cloud_cover_medium": 8,
            "cloud_cover_high": 2,
            "cloud_base_altitude": 5200.0,
            "precipitation_probability": 0,
            "visibility": 45000.0,
            "wind_speed_10m": 8.5,
            "snowfall": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "weather_code": 0,
        }
        data2 = {**data1, "temperature_2m": -8.0, "fetched_at": "2026-02-10 12:00:00"}

        memory_repo.upsert_weather(29.58, 101.88, date(2026, 2, 11), 6, data1)
        memory_repo.upsert_weather(29.58, 101.88, date(2026, 2, 11), 6, data2)

        result = memory_repo.query_weather(29.58, 101.88, date(2026, 2, 11), hours=[6])
        assert len(result) == 1
        assert result[0]["temperature_2m"] == pytest.approx(-8.0)

    def test_query_no_data_returns_none(self, memory_repo):
        """查询无数据返回 None"""
        result = memory_repo.query_weather(0.0, 0.0, date(2026, 1, 1))
        assert result is None


# ==================== upsert_weather_batch ====================


class TestBatchUpsert:
    def test_batch_writes_multiple_rows(self, memory_repo):
        """批量写入多条数据"""
        base = {
            "fetched_at": "2026-02-10 08:00:00",
            "temperature_2m": 0.0,
            "cloud_cover_total": 10,
            "cloud_cover_low": 0,
            "cloud_cover_medium": 0,
            "cloud_cover_high": 0,
            "cloud_base_altitude": 5000.0,
            "precipitation_probability": 0,
            "visibility": 50000.0,
            "wind_speed_10m": 3.0,
            "snowfall": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "weather_code": 0,
        }
        rows = [{**base, "forecast_hour": h, "temperature_2m": -10.0 + h} for h in range(24)]
        memory_repo.upsert_weather_batch(29.58, 101.88, date(2026, 2, 11), rows)

        result = memory_repo.query_weather(29.58, 101.88, date(2026, 2, 11))
        assert result is not None
        assert len(result) == 24


# ==================== prediction_history ====================


class TestPredictionHistory:
    def test_save_and_get_predictions(self, memory_repo):
        """保存并查询预测历史"""
        record = {
            "viewpoint_id": "niubei_gongga",
            "prediction_date": "2026-02-10",
            "target_date": "2026-02-11",
            "event_type": "sunrise_golden_mountain",
            "predicted_score": 88,
            "predicted_status": "Recommended",
            "confidence": "High",
            "conditions_json": '{"cloud": "low"}',
            "is_backtest": 0,
            "data_source": "forecast",
        }
        memory_repo.save_prediction(record)
        results = memory_repo.get_predictions("niubei_gongga")
        assert len(results) == 1
        assert results[0]["predicted_score"] == 88
        assert results[0]["event_type"] == "sunrise_golden_mountain"

    def test_get_predictions_by_date(self, memory_repo):
        """按日期过滤预测历史"""
        for i, target in enumerate(["2026-02-11", "2026-02-12"]):
            record = {
                "viewpoint_id": "niubei_gongga",
                "prediction_date": "2026-02-10",
                "target_date": target,
                "event_type": "sunrise_golden_mountain",
                "predicted_score": 80 + i,
                "predicted_status": "Recommended",
                "confidence": "High",
                "conditions_json": "{}",
                "is_backtest": 0,
                "data_source": "forecast",
            }
            memory_repo.save_prediction(record)

        results = memory_repo.get_predictions(
            "niubei_gongga", target_date=date(2026, 2, 11)
        )
        assert len(results) == 1
        assert results[0]["target_date"] == "2026-02-11"

    def test_get_predictions_empty(self, memory_repo):
        """查询不存在的预测历史返回空列表"""
        results = memory_repo.get_predictions("nonexistent_vp")
        assert results == []


# ==================== 数据类型正确性 ====================


class TestDataTypes:
    def test_weather_data_types(self, memory_repo):
        """验证查询结果的数据类型"""
        data = {
            "fetched_at": "2026-02-10 08:00:00",
            "temperature_2m": -12.3,
            "cloud_cover_total": 15,
            "cloud_cover_low": 5,
            "cloud_cover_medium": 8,
            "cloud_cover_high": 2,
            "cloud_base_altitude": 5200.0,
            "precipitation_probability": 0,
            "visibility": 45000.0,
            "wind_speed_10m": 8.5,
            "snowfall": 0.0,
            "rain": 0.0,
            "showers": 0.0,
            "weather_code": 0,
        }
        memory_repo.upsert_weather(29.58, 101.88, date(2026, 2, 11), 6, data)
        result = memory_repo.query_weather(29.58, 101.88, date(2026, 2, 11))
        row = result[0]

        # float 类型
        assert isinstance(row["temperature_2m"], float)
        assert isinstance(row["cloud_base_altitude"], float)
        assert isinstance(row["visibility"], float)
        assert isinstance(row["wind_speed_10m"], float)

        # int 类型
        assert isinstance(row["cloud_cover_total"], int)
        assert isinstance(row["forecast_hour"], int)

        # str 类型
        assert isinstance(row["fetched_at"], str)
