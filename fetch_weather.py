"""
fetch_weather.py - Gate 1: 取得 CWA API 資料
使用中央氣象署 (CWA) 開放資料平台 API 取得台灣六大區域一週天氣預報。
資料集代號: F-A0010-001 (臺灣各區一週天氣預報)
"""

import datetime
import json
import os
import requests
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# 設定 API 金鑰與端點
CWA_API_KEY = os.getenv("CWA_API_KEY", "").strip()
URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0010-001"
OUTPUT_FILE = "raw_weather.json"

# 六大目標區域
REGIONS = [
    "北部地區",
    "中部地區",
    "南部地區",
    "東北部地區",
    "東部地區",
    "東南部地區"
]


def generate_fallback_data() -> dict:
    """當無 API Key 或網路異常時，生成合規的 7 天模擬/備用天氣預報 JSON。"""
    print("[提示] 啟用備用資料生成器，建立 7 天六大區域預報結構...")
    base_date = datetime.date.today()
    
    # 六大區域的典型溫度基準 (最低溫, 最高溫)
    region_base_temps = {
        "北部地區": (22, 29),
        "中部地區": (23, 31),
        "南部地區": (25, 33),
        "東北部地區": (21, 27),
        "東部地區": (22, 28),
        "東南部地區": (24, 30),
    }

    locations_list = []
    for reg_name in REGIONS:
        min_base, max_base = region_base_temps.get(reg_name, (22, 30))
        min_times = []
        max_times = []

        for day_offset in range(7):
            cur_date = base_date + datetime.timedelta(days=day_offset)
            date_str = cur_date.strftime("%Y-%m-%d")
            start_time = f"{date_str} 06:00:00"
            end_time = f"{date_str} 18:00:00"

            # 模擬微小溫度波動
            variation = (day_offset % 3) - 1
            cur_min = min_base + variation
            cur_max = max_base + variation

            min_times.append({
                "startTime": start_time,
                "endTime": end_time,
                "elementValue": [{"value": str(cur_min), "measures": "攝氏度"}]
            })
            max_times.append({
                "startTime": start_time,
                "endTime": end_time,
                "elementValue": [{"value": str(cur_max), "measures": "攝氏度"}]
            })

        weather_elements = [
            {
                "elementName": "MinT",
                "description": "最低溫度",
                "time": min_times
            },
            {
                "elementName": "MaxT",
                "description": "最高溫度",
                "time": max_times
            }
        ]

        locations_list.append({
            "locationName": reg_name,
            "weatherElement": weather_elements
        })

    return {
        "success": "true",
        "result": {
            "resource_id": "F-A0010-001",
            "fields": []
        },
        "records": {
            "locations": {
                "datasetDescription": "臺灣各區一週天氣預報",
                "location": locations_list
            }
        }
    }


def fetch_cwa_weather(api_key: str = None) -> dict:
    """呼叫 CWA Open Data API 取得天氣預報 JSON。"""
    key = (api_key or CWA_API_KEY).strip()
    
    # 檢查是否具備有效 API Key
    if not key or key == "YOUR_CWA_API_KEY_HERE":
        print("[警告] 尚未設定有效的 CWA_API_KEY，將使用備用示範資料。")
        data = generate_fallback_data()
    else:
        print(f"[資訊] 正在向中央氣象署 API ({URL}) 請求一週預報資料...")
        params = {
            "Authorization": key,
            "format": "JSON"
        }
        try:
            response = requests.get(URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            print("[成功] 成功從 CWA API 獲取即時資料！")
        except requests.exceptions.RequestException as e:
            print(f"[錯誤] API 請求失敗: {e}，切換為備用預報資料。")
            data = generate_fallback_data()

    # 儲存 JSON 到本機檔案
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[完成] 原始 JSON 已成功儲存至: {OUTPUT_FILE}")
    return data


if __name__ == "__main__":
    print("=" * 60)
    print("HW10 - 步驟一：取得 CWA API 資料 (F-A0010-001)")
    print("=" * 60)
    result_data = fetch_cwa_weather()
    
    # 簡單驗證輸出結構
    try:
        locs = result_data["records"]["locations"]["location"]
        print(f"\n[驗證 Check] 包含區域數量: {len(locs)}")
        for loc in locs:
            print(f"  - 區域: {loc.get('locationName')}")
    except KeyError:
        print("\n[驗證 Check] 成功取得 JSON，但請留意結構層級。")
    print("=" * 60)
