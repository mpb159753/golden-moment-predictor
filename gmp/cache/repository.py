"""gmp/cache/repository.py — SQLite 缓存数据库操作层

底层数据库操作，负责 weather_cache 和 prediction_history 两张表的
建表、读写、查询。坐标自动 ROUND(2)。
"""

from __future__ import annotations

import sqlite3
from datetime import date

import structlog

logger = structlog.get_logger()

# weather_cache 的天气数据字段（不含坐标/时间键）
_WEATHER_DATA_COLUMNS = [
    "temperature_2m",
    "cloud_cover_total",
    "cloud_cover_low",
    "cloud_cover_medium",
    "cloud_cover_high",
    "cloud_base_altitude",
    "precipitation_probability",
    "visibility",
    "wind_speed_10m",
    "snowfall",
    "rain",
    "showers",
    "weather_code",
]

# query_weather 返回的字段
_QUERY_COLUMNS = [
    "lat_rounded",
    "lon_rounded",
    "forecast_date",
    "forecast_hour",
    "fetched_at",
    "api_source",
    *_WEATHER_DATA_COLUMNS,
]


class CacheRepository:
    """SQLite 缓存数据库底层操作"""

    def __init__(self, db_path: str) -> None:
        """连接 SQLite，自动创建表"""
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.debug("cache_repository.init", db_path=db_path)

    # ==================== 建表 ====================

    def _create_tables(self) -> None:
        """创建 weather_cache 和 prediction_history 表 (IF NOT EXISTS)"""
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS weather_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lat_rounded REAL NOT NULL,
                lon_rounded REAL NOT NULL,
                forecast_date DATE NOT NULL,
                forecast_hour INTEGER NOT NULL,
                fetched_at DATETIME NOT NULL,
                api_source TEXT DEFAULT 'open-meteo',
                raw_response_json TEXT,
                temperature_2m REAL,
                cloud_cover_total INTEGER,
                cloud_cover_low INTEGER,
                cloud_cover_medium INTEGER,
                cloud_cover_high INTEGER,
                cloud_base_altitude REAL,
                precipitation_probability INTEGER,
                visibility REAL,
                wind_speed_10m REAL,
                snowfall REAL,
                rain REAL,
                showers REAL,
                weather_code INTEGER,
                UNIQUE(lat_rounded, lon_rounded, forecast_date, forecast_hour)
            );

            CREATE INDEX IF NOT EXISTS idx_coords
                ON weather_cache(lat_rounded, lon_rounded);
            CREATE INDEX IF NOT EXISTS idx_date
                ON weather_cache(forecast_date);
            CREATE INDEX IF NOT EXISTS idx_fetched
                ON weather_cache(fetched_at);

            CREATE TABLE IF NOT EXISTS prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                viewpoint_id TEXT NOT NULL,
                prediction_date DATE NOT NULL,
                target_date DATE NOT NULL,
                event_type TEXT NOT NULL,
                predicted_score INTEGER,
                predicted_status TEXT,
                confidence TEXT,
                conditions_json TEXT,
                actual_result TEXT,
                user_feedback TEXT,
                feedback_at DATETIME,
                is_backtest BOOLEAN DEFAULT 0,
                data_source TEXT DEFAULT 'forecast',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_prediction_target
                ON prediction_history(target_date);
            CREATE INDEX IF NOT EXISTS idx_viewpoint
                ON prediction_history(viewpoint_id);
        """
        )

    # ==================== weather_cache 操作 ====================

    def query_weather(
        self,
        lat: float,
        lon: float,
        target_date: date,
        hours: list[int] | None = None,
    ) -> list[dict] | None:
        """查询天气缓存

        坐标会自动 ROUND(2)。
        hours=None 查全天 (0-23)。
        返回 None 表示无数据。
        """
        lat_r = round(lat, 2)
        lon_r = round(lon, 2)
        date_str = target_date.isoformat()

        if hours is not None:
            placeholders = ",".join("?" for _ in hours)
            sql = f"""
                SELECT {', '.join(_QUERY_COLUMNS)}
                FROM weather_cache
                WHERE lat_rounded = ? AND lon_rounded = ?
                  AND forecast_date = ?
                  AND forecast_hour IN ({placeholders})
                ORDER BY forecast_hour
            """
            params: list = [lat_r, lon_r, date_str, *hours]
        else:
            sql = f"""
                SELECT {', '.join(_QUERY_COLUMNS)}
                FROM weather_cache
                WHERE lat_rounded = ? AND lon_rounded = ?
                  AND forecast_date = ?
                ORDER BY forecast_hour
            """
            params = [lat_r, lon_r, date_str]

        rows = self._conn.execute(sql, params).fetchall()
        if not rows:
            return None
        return [dict(row) for row in rows]

    def upsert_weather(
        self,
        lat: float,
        lon: float,
        target_date: date,
        hour: int,
        data: dict,
    ) -> None:
        """INSERT OR REPLACE 天气数据。坐标自动 ROUND(2)。"""
        lat_r = round(lat, 2)
        lon_r = round(lon, 2)
        date_str = target_date.isoformat()

        values = {
            "lat_rounded": lat_r,
            "lon_rounded": lon_r,
            "forecast_date": date_str,
            "forecast_hour": hour,
            "fetched_at": data["fetched_at"],
        }
        for col in _WEATHER_DATA_COLUMNS:
            if col in data:
                values[col] = data[col]

        columns = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        sql = f"INSERT OR REPLACE INTO weather_cache ({columns}) VALUES ({placeholders})"
        self._conn.execute(sql, list(values.values()))
        self._conn.commit()

    def upsert_weather_batch(
        self,
        lat: float,
        lon: float,
        target_date: date,
        rows: list[dict],
    ) -> None:
        """批量写入 (一天24条)。使用事务优化性能。"""
        for row in rows:
            hour = row["forecast_hour"]
            self.upsert_weather(lat, lon, target_date, hour, row)

    # ==================== prediction_history 操作 ====================

    def save_prediction(self, record: dict) -> None:
        """保存预测历史记录到 prediction_history"""
        columns = [
            "viewpoint_id",
            "prediction_date",
            "target_date",
            "event_type",
            "predicted_score",
            "predicted_status",
            "confidence",
            "conditions_json",
            "is_backtest",
            "data_source",
        ]
        values = [record.get(c) for c in columns]
        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO prediction_history ({', '.join(columns)}) VALUES ({placeholders})"
        self._conn.execute(sql, values)
        self._conn.commit()

    def get_predictions(
        self,
        viewpoint_id: str,
        target_date: date | None = None,
    ) -> list[dict]:
        """查询预测历史。返回空列表表示无数据。"""
        if target_date is not None:
            sql = """
                SELECT * FROM prediction_history
                WHERE viewpoint_id = ? AND target_date = ?
                ORDER BY created_at
            """
            rows = self._conn.execute(
                sql, [viewpoint_id, target_date.isoformat()]
            ).fetchall()
        else:
            sql = """
                SELECT * FROM prediction_history
                WHERE viewpoint_id = ?
                ORDER BY created_at
            """
            rows = self._conn.execute(sql, [viewpoint_id]).fetchall()

        return [dict(row) for row in rows]

    # ==================== 生命周期 ====================

    def close(self) -> None:
        """关闭连接"""
        self._conn.close()
