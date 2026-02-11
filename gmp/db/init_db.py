"""GMP 数据库初始化 — 建表脚本

SQL 表结构严格遵循 design/02-data-model.md §2.2。
"""

import sqlite3
from pathlib import Path


def init_database(db_path: str) -> None:
    """初始化数据库，创建表结构和索引。

    如果数据库文件所在目录不存在，会自动创建。
    如果表已存在，不会重复创建 (IF NOT EXISTS)。

    Args:
        db_path: SQLite 数据库文件路径
    """
    # 确保父目录存在
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # 创建 weather_cache 表
        cursor.execute("""
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
            )
        """)

        # 创建 prediction_history 表
        cursor.execute("""
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引加速查询
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_cache_coord_date
            ON weather_cache(lat_rounded, lon_rounded, forecast_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prediction_history_viewpoint
            ON prediction_history(viewpoint_id, target_date)
        """)

        conn.commit()
    finally:
        conn.close()
