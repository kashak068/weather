"""
database.py - Gate 3: 存入 SQLite 資料庫
建立 SQLite data.db 並設計 TemperatureForecasts 資料表，
將全台 22 縣市與六大分區之氣溫資料匯入。
"""

import os
import sqlite3
from typing import List, Dict, Any, Tuple


DB_FILE = "data.db"
TABLE_NAME = "TemperatureForecasts"


def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """建立並回傳 SQLite 資料庫連線。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: str = DB_FILE, drop_old: bool = False):
    """建立 TemperatureForecasts 資料表結構。"""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if drop_old:
            cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT NOT NULL,
            locationType TEXT DEFAULT 'county',
            dataDate TEXT NOT NULL,
            minT REAL NOT NULL,
            maxT REAL NOT NULL
        );
        """
        cursor.execute(create_table_sql)
        
        # 檢查欄位是否存在（兼容舊版本）
        cursor.execute(f"PRAGMA table_info({TABLE_NAME});")
        cols = [col[1] for col in cursor.fetchall()]
        if "locationType" not in cols:
            cursor.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN locationType TEXT DEFAULT 'county';")

        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_region ON {TABLE_NAME}(regionName);")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_type ON {TABLE_NAME}(locationType);")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_date ON {TABLE_NAME}(dataDate);")
        conn.commit()
    print(f"[資料庫] 已成功初始化資料表: {TABLE_NAME}")


def insert_forecasts(records: List[Dict[str, Any]], db_path: str = DB_FILE, overwrite: bool = True):
    """將解析後的預報資料清單批次寫入資料庫。"""
    if not records:
        print("[警告] 無欲寫入之記錄。")
        return

    init_database(db_path, drop_old=overwrite)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        insert_sql = f"""
        INSERT INTO {TABLE_NAME} (regionName, locationType, dataDate, minT, maxT)
        VALUES (:regionName, :locationType, :dataDate, :minT, :maxT);
        """
        cursor.executemany(insert_sql, records)
        conn.commit()

    print(f"[資料庫] 成功匯入 {len(records)} 筆資料至 {TABLE_NAME} (位於 {db_path})")


def query_distinct_locations(db_path: str = DB_FILE, location_type: str = None) -> List[str]:
    """列出所有不重複地點/縣市名稱。"""
    if location_type:
        sql = f"SELECT DISTINCT regionName FROM {TABLE_NAME} WHERE locationType = ? ORDER BY regionName;"
        params = (location_type,)
    else:
        sql = f"SELECT DISTINCT regionName FROM {TABLE_NAME} ORDER BY regionName;"
        params = ()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [r["regionName"] for r in rows]


def query_by_location(location_name: str, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """查詢指定縣市或分區的氣溫預報資料。"""
    sql = f"""
    SELECT id, regionName, locationType, dataDate, minT, maxT
    FROM {TABLE_NAME}
    WHERE regionName = ?
    ORDER BY dataDate ASC;
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (location_name,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def query_all_latest_day(db_path: str = DB_FILE, location_type: str = None) -> List[Dict[str, Any]]:
    """查詢所有地點最近一日的氣溫預報（供地圖顯示使用）。"""
    type_clause = "WHERE t.locationType = ?" if location_type else ""
    params = (location_type,) if location_type else ()

    sql = f"""
    SELECT t.regionName, t.locationType, t.dataDate, t.minT, t.maxT
    FROM {TABLE_NAME} t
    INNER JOIN (
        SELECT regionName, MIN(dataDate) as minDate
        FROM {TABLE_NAME}
        GROUP BY regionName
    ) m ON t.regionName = m.regionName AND t.dataDate = m.minDate
    {type_clause}
    ORDER BY t.regionName;
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    print("=" * 60)
    print("HW10 - 步驟三：存入 SQLite 資料庫 (包含全台 22 縣市與分區)")
    print("=" * 60)

    from parse_weather import parse_weather_json
    records = parse_weather_json("raw_weather.json")
    insert_forecasts(records, DB_FILE, overwrite=True)

    print("\n[驗證 Check] 查詢個別縣市清單：")
    counties = query_distinct_locations(DB_FILE, location_type="county")
    print(f"  縣市數量: {len(counties)} 個 -> {', '.join(counties[:8])}...")

    print("\n[驗證 Check] 查詢大分區清單：")
    regions = query_distinct_locations(DB_FILE, location_type="region")
    print(f"  分區數量: {len(regions)} 個 -> {', '.join(regions)}")

    print("\n[驗證 Check] 查詢臺北市資料：")
    tpe = query_by_location("臺北市", DB_FILE)
    for row in tpe:
        print(f"  {row['dataDate']} | 最低溫: {row['minT']}°C | 最高溫: {row['maxT']}°C")

    print("=" * 60)
