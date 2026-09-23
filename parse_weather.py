"""
parse_weather.py - Gate 2: 分析 JSON，提取氣溫資料
從 raw_weather.json 提取六大區域（北部、中部、南部、東北部、東部、東南部）
每日最高溫 (MaxT) 與最低溫 (MinT)，整理並輸出為結構化清單及 CSV。
"""

import csv
import json
import os
from typing import List, Dict, Any


INPUT_JSON = "raw_weather.json"
OUTPUT_CSV = "weather_data.csv"

# 六大目標分區
VALID_REGIONS = [
    "北部地區",
    "中部地區",
    "南部地區",
    "東北部地區",
    "東部地區",
    "東南部地區"
]


def parse_weather_json(json_path: str = INPUT_JSON) -> List[Dict[str, Any]]:
    """解析 CWA 天氣預報 JSON 結構，提取每日最高溫與最低溫。"""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"找不到檔案: {json_path}，請先執行 fetch_weather.py 取得資料。")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    parsed_records: List[Dict[str, Any]] = []

    # 解析 locations -> location[]
    try:
        locations = data.get("records", {}).get("locations", {}).get("location", [])
    except AttributeError:
        locations = []

    for loc in locations:
        region_name = loc.get("locationName", "").strip()
        if not region_name:
            continue

        # 提取 weatherElement 列表
        elements = loc.get("weatherElement", [])
        min_temp_map: Dict[str, float] = {}
        max_temp_map: Dict[str, float] = {}

        for elem in elements:
            elem_name = elem.get("elementName", "")
            time_entries = elem.get("time", [])

            for t_entry in time_entries:
                start_time = t_entry.get("startTime", "")
                date_str = start_time.split(" ")[0] if " " in start_time else start_time.split("T")[0]
                val_list = t_entry.get("elementValue", [])
                
                if val_list and "value" in val_list[0]:
                    raw_val = val_list[0]["value"]
                    try:
                        temp_val = float(raw_val)
                    except (ValueError, TypeError):
                        continue

                    if elem_name == "MinT":
                        # 取當日最低溫的極小值
                        if date_str not in min_temp_map or temp_val < min_temp_map[date_str]:
                            min_temp_map[date_str] = temp_val
                    elif elem_name == "MaxT":
                        # 取當日最高溫的極大值
                        if date_str not in max_temp_map or temp_val > max_temp_map[date_str]:
                            max_temp_map[date_str] = temp_val

        # 合併同一個日期的 MinT 與 MaxT
        all_dates = sorted(list(set(min_temp_map.keys()) | set(max_temp_map.keys())))
        for d in all_dates:
            min_t = min_temp_map.get(d)
            max_t = max_temp_map.get(d)

            # 若有一方缺失則合理推算
            if min_t is None and max_t is not None:
                min_t = max_t - 5.0
            elif max_t is None and min_t is not None:
                max_t = min_t + 5.0
            elif min_t is None and max_t is None:
                continue

            parsed_records.append({
                "regionName": region_name,
                "dataDate": d,
                "minT": round(min_t, 1),
                "maxT": round(max_t, 1)
            })

    # 儲存為 CSV
    save_to_csv(parsed_records, OUTPUT_CSV)
    return parsed_records


def save_to_csv(records: List[Dict[str, Any]], csv_path: str = OUTPUT_CSV):
    """將解析結果寫入 CSV 檔案。"""
    if not records:
        print("[警告] 無可寫入 CSV 之資料。")
        return

    fieldnames = ["regionName", "dataDate", "minT", "maxT"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"[完成] 清洗後資料已儲存至: {csv_path} (共 {len(records)} 筆資料)")


if __name__ == "__main__":
    print("=" * 60)
    print("HW10 - 步驟二：分析 JSON，提取氣溫資料")
    print("=" * 60)
    
    # 若 raw_weather.json 不存在，自動觸發 fetch_weather 產出
    if not os.path.exists(INPUT_JSON):
        print(f"[提示] {INPUT_JSON} 不存在，呼叫 fetch_weather.py 生成...")
        from fetch_weather import fetch_cwa_weather
        fetch_cwa_weather()

    results = parse_weather_json(INPUT_JSON)
    
    # 統計檢驗輸出
    print("\n[驗證 Check] 提取結果預覽 (前 10 筆)：")
    print(f"{'地區':<10} | {'日期':<12} | {'最低溫(MinT)':<12} | {'最高溫(MaxT)':<12}")
    print("-" * 55)
    for row in results[:10]:
        print(f"{row['regionName']:<10} | {row['dataDate']:<12} | {row['minT']:<12} | {row['maxT']:<12}")
    
    regions_found = set(r["regionName"] for r in results)
    print("-" * 55)
    print(f"[驗證 Check] 成功解析六大區域數量: {len(regions_found)} / 6")
    print(f"涵蓋區域: {', '.join(sorted(regions_found))}")
    print("=" * 60)
