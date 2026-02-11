"""SQLite 数据操作层

对 weather_cache 和 prediction_history 表的 CRUD 操作。
接口定义遵循 design/07-code-interface.md §7.1 ICacheRepository。
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any


class CacheRepository:
    """SQLite 数据操作层

    所有坐标操作使用 ``ROUND(lat, 2)`` 和 ``ROUND(lon, 2)``，
    确保约 1km 精度内的坐标共享同一条缓存。
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        """创建数据库连接。"""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def query(
        self,
        lat: float,
        lon: float,
        target_date: date,
        hours: list[int],
    ) -> list[dict] | None:
        """查询天气缓存。

        Args:
            lat: 纬度
            lon: 经度
            target_date: 目标日期
            hours: 需要的小时列表

        Returns:
            匹配的缓存记录列表，无数据返回 None
        """
        lat_rounded = round(lat, 2)
        lon_rounded = round(lon, 2)

        placeholders = ",".join("?" for _ in hours)
        sql = f"""
            SELECT * FROM weather_cache
            WHERE lat_rounded = ?
              AND lon_rounded = ?
              AND forecast_date = ?
              AND forecast_hour IN ({placeholders})
            ORDER BY forecast_hour
        """
        params: list[Any] = [lat_rounded, lon_rounded, target_date.isoformat()]
        params.extend(hours)

        conn = self._connect()
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            if not rows:
                return None
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def upsert(
        self,
        lat: float,
        lon: float,
        target_date: date,
        hour: int,
        data: dict,
    ) -> None:
        """插入或更新天气缓存 (INSERT OR REPLACE)。

        Args:
            lat: 纬度
            lon: 经度
            target_date: 目标日期
            hour: 预报小时
            data: 天气数据字典
        """
        lat_rounded = round(lat, 2)
        lon_rounded = round(lon, 2)

        sql = """
            INSERT OR REPLACE INTO weather_cache (
                lat_rounded, lon_rounded, forecast_date, forecast_hour,
                fetched_at, api_source, raw_response_json,
                temperature_2m, cloud_cover_total, cloud_cover_low,
                cloud_cover_medium, cloud_cover_high, cloud_base_altitude,
                precipitation_probability, visibility, wind_speed_10m,
                snowfall, rain, showers, weather_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            lat_rounded,
            lon_rounded,
            target_date.isoformat(),
            hour,
            datetime.now().isoformat(),
            data.get("api_source", "open-meteo"),
            data.get("raw_response_json"),
            data.get("temperature_2m"),
            data.get("cloud_cover_total"),
            data.get("cloud_cover_low"),
            data.get("cloud_cover_medium"),
            data.get("cloud_cover_high"),
            data.get("cloud_base_altitude"),
            data.get("precipitation_probability"),
            data.get("visibility"),
            data.get("wind_speed_10m"),
            data.get("snowfall"),
            data.get("rain"),
            data.get("showers"),
            data.get("weather_code"),
        )

        conn = self._connect()
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def save_prediction(self, prediction: dict) -> None:
        """保存预测历史记录。

        Args:
            prediction: 预测数据字典，包含 viewpoint_id, prediction_date,
                        target_date, event_type, predicted_score 等字段
        """
        sql = """
            INSERT INTO prediction_history (
                viewpoint_id, prediction_date, target_date, event_type,
                predicted_score, predicted_status, confidence,
                conditions_json, actual_result, user_feedback, feedback_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            prediction["viewpoint_id"],
            prediction["prediction_date"],
            prediction["target_date"],
            prediction["event_type"],
            prediction.get("predicted_score"),
            prediction.get("predicted_status"),
            prediction.get("confidence"),
            prediction.get("conditions_json"),
            prediction.get("actual_result"),
            prediction.get("user_feedback"),
            prediction.get("feedback_at"),
        )

        conn = self._connect()
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def get_history(
        self,
        viewpoint_id: str,
        date_range: tuple[date, date],
    ) -> list[dict]:
        """查询预测历史。

        Args:
            viewpoint_id: 观景台 ID
            date_range: (起始日期, 结束日期) 元组

        Returns:
            匹配的历史记录列表
        """
        sql = """
            SELECT * FROM prediction_history
            WHERE viewpoint_id = ?
              AND target_date BETWEEN ? AND ?
            ORDER BY target_date, event_type
        """
        params = (
            viewpoint_id,
            date_range[0].isoformat(),
            date_range[1].isoformat(),
        )

        conn = self._connect()
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
