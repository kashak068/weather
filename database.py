"""
database.py - Gate 3: 存入 SQLite 資料庫
建立 SQLite data.db 並設計 TemperatureForecasts 資料表，
將清洗後的預報資料匯入，並提供查詢介面供 Streamlit 呼叫。
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


def init_database(db_path: str = DB_FILE):
    """建立 TemperatureForecasts 資料表結構。"""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT NOT NULL,
            dataDate TEXT NOT NULL,
            minT REAL NOT NULL,
            maxT REAL NOT NULL
        );
        """
        cursor.execute(create_table_sql)
        # 建立索引加速查詢
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_region ON {TABLE_NAME}(regionName);")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_date ON {TABLE_NAME}(dataDate);")
        conn.commit()
    print(f"[資料庫] 已成功初始化資料表: {TABLE_NAME}")


def insert_forecasts(records: List[Dict[str, Any]], db_path: str = DB_FILE, overwrite: bool = True):
    """將解析後的預報資料清單批次寫入資料庫。"""
    if not records:
        print("[警告] 無欲寫入之記錄。")
        return

    init_database(db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if overwrite:
            # 清空舊資料以避免重複累積
            cursor.execute(f"DELETE FROM {TABLE_NAME}")

        insert_sql = f"""
        INSERT INTO {TABLE_NAME} (regionName, dataDate, minT, maxT)
        VALUES (:regionName, :dataDate, :minT, :maxT);
        """
        cursor.executemany(insert_sql, records)
        conn.commit()

    print(f"[資料庫] 成功匯入 {len(records)} 筆資料至 {TABLE_NAME} (位於 {db_path})")


def query_distinct_regions(db_path: str = DB_FILE) -> List[str]:
    """驗證查詢 1: 列出所有地區名稱。"""
    sql = f"SELECT DISTINCT regionName FROM {TABLE_NAME} ORDER BY regionName;"
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [r["regionName"] for r in rows]


def query_by_region(region_name: str, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """驗證查詢 2: 查詢指定地區的氣溫預報資料。"""
    sql = f"""
    SELECT id, regionName, dataDate, minT, maxT
    FROM {TABLE_NAME}
    WHERE regionName = ?
    ORDER BY dataDate ASC;
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (region_name,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def query_all_latest_day(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """查詢所有區域最近一日的氣溫預報（供地圖顯示使用）。"""
    sql = f"""
    SELECT t.regionName, t.dataDate, t.minT, t.maxT
    FROM {TABLE_NAME} t
    INNER JOIN (
        SELECT regionName, MIN(dataDate) as minDate
        FROM {TABLE_NAME}
        GROUP BY regionName
    ) m ON t.regionName = m.regionName AND t.dataDate = m.minDate;
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    print("=" * 60)
    print("HW10 - 步驟三：存入 SQLite 資料庫 (data.db)")
    print("=" * 60)

    # 取得或解析資料
    from parse_weather import parse_weather_json
    records = parse_weather_json("raw_weather.json")

    # 存入資料庫
    insert_forecasts(records, DB_FILE, overwrite=True)

    # 執行驗證查詢 1
    print("\n[驗證 Check 1] 查詢 DISTINCT regionName：")
    regions = query_distinct_regions(DB_FILE)
    print(f"  資料庫現有地區: {regions}")

    # 執行驗證查詢 2
    print("\n[驗證 Check 2] 查詢中部地區資料：")
    central_data = query_by_region("中部地區", DB_FILE)
    print(f"{'日期':<12} | {'最低溫(MinT)':<12} | {'最高溫(MaxT)':<12}")
    print("-" * 45)
    for row in central_data:
        print(f"{row['dataDate']:<12} | {row['minT']:<12} | {row['maxT']:<12}")

    print("=" * 60)
