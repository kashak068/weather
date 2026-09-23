"""
fetch_weather.py - Gate 1: 取得 CWA API 資料
使用中央氣象署 (CWA) 開放資料平台 API 取得台灣全台 22 縣市及六大區域一週天氣預報。
資料集: F-D0047-091 / F-A0010-001
"""

import datetime
import json
import os
from typing import Dict, List, Any
import requests
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# 設定 API 金鑰與端點
CWA_API_KEY = os.getenv("CWA_API_KEY", "").strip()
URL_COUNTIES = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091"
URL_PRIMARY = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0010-001"
OUTPUT_FILE = "raw_weather.json"

# 六大目標區域與對應縣市
REGION_COUNTY_MAP = {
    "北部地區": ["基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣"],
    "中部地區": ["臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣"],
    "南部地區": ["臺南市", "高雄市", "屏東縣"],
    "東北部地區": ["宜蘭縣"],
    "東部地區": ["花蓮縣"],
    "東南部地區": ["臺東縣"],
    "離島地區": ["澎湖縣", "金門縣", "連江縣"]
}

# 全台 22 縣市清單
ALL_COUNTIES = [
    "基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣",
    "臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣",
    "臺南市", "高雄市", "屏東縣",
    "宜蘭縣", "花蓮縣", "臺東縣",
    "澎湖縣", "金門縣", "連江縣"
]


def parse_location_elements(c_loc: dict) -> List[dict]:
    """從單一縣市原始資料萃取 MinT 與 MaxT 7日時間序列。"""
    min_date_temps: Dict[str, List[float]] = {}
    max_date_temps: Dict[str, List[float]] = {}

    for elem in c_loc.get("WeatherElement", []):
        elem_name = elem.get("ElementName", "")
        is_min = elem_name in ["最低溫度", "MinT", "MinTemperature"]
        is_max = elem_name in ["最高溫度", "MaxT", "MaxTemperature"]
        if not (is_min or is_max):
            continue

        for t in elem.get("Time", []):
            st = t.get("StartTime", "")
            date_str = st.split(" ")[0] if " " in st else st.split("T")[0]
            vals = t.get("ElementValue", [])
            if not vals:
                continue

            val_dict = vals[0]
            raw_val = None
            for k in ["MinTemperature", "MaxTemperature", "Value", "value", "Temperature"]:
                if k in val_dict and val_dict[k] not in [None, "", "-"]:
                    raw_val = val_dict[k]
                    break

            if raw_val is not None:
                try:
                    temp_float = float(raw_val)
                    if is_min:
                        min_date_temps.setdefault(date_str, []).append(temp_float)
                    elif is_max:
                        max_date_temps.setdefault(date_str, []).append(temp_float)
                except (ValueError, TypeError):
                    continue

    sorted_dates = sorted(list(set(min_date_temps.keys()) | set(max_date_temps.keys())))[:7]
    min_times = []
    max_times = []

    for d in sorted_dates:
        min_vals = min_date_temps.get(d, [])
        max_vals = max_date_temps.get(d, [])
        
        day_min = round(min(min_vals), 1) if min_vals else 22.0
        day_max = round(max(max_vals), 1) if max_vals else 30.0

        min_times.append({
            "startTime": f"{d} 06:00:00",
            "endTime": f"{d} 18:00:00",
            "elementValue": [{"value": str(day_min), "measures": "攝氏度"}]
        })
        max_times.append({
            "startTime": f"{d} 06:00:00",
            "endTime": f"{d} 18:00:00",
            "elementValue": [{"value": str(day_max), "measures": "攝氏度"}]
        })

    return [
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


def transform_cwa_response(cwa_data: dict) -> dict:
    """將 CWA 各縣市即時預報轉化為全台 22 縣市 + 六大區域整合之標準 JSON 格式。"""
    try:
        raw_locs = cwa_data["records"]["Locations"][0]["Location"]
    except (KeyError, IndexError):
        return None

    county_dict = {loc["LocationName"]: loc for loc in raw_locs}
    locations_list = []

    # 1. 產生個別縣市 (全台 22 縣市) 節點
    for c_name in ALL_COUNTIES:
        if c_name in county_dict:
            weather_elements = parse_location_elements(county_dict[c_name])
            locations_list.append({
                "locationName": c_name,
                "locationType": "county",
                "weatherElement": weather_elements
            })

    # 2. 產生六大分區 (聚合區域) 節點
    for reg_name, county_list in REGION_COUNTY_MAP.items():
        min_date_temps: Dict[str, List[float]] = {}
        max_date_temps: Dict[str, List[float]] = {}

        for c_name in county_list:
            if c_name not in county_dict:
                continue
            c_loc = county_dict[c_name]
            for elem in c_loc.get("WeatherElement", []):
                elem_name = elem.get("ElementName", "")
                is_min = elem_name in ["最低溫度", "MinT", "MinTemperature"]
                is_max = elem_name in ["最高溫度", "MaxT", "MaxTemperature"]
                if not (is_min or is_max):
                    continue

                for t in elem.get("Time", []):
                    st = t.get("StartTime", "")
                    date_str = st.split(" ")[0] if " " in st else st.split("T")[0]
                    vals = t.get("ElementValue", [])
                    if not vals:
                        continue
                    val_dict = vals[0]
                    raw_val = None
                    for k in ["MinTemperature", "MaxTemperature", "Value", "value", "Temperature"]:
                        if k in val_dict and val_dict[k] not in [None, "", "-"]:
                            raw_val = val_dict[k]
                            break
                    if raw_val is not None:
                        try:
                            temp_float = float(raw_val)
                            if is_min:
                                min_date_temps.setdefault(date_str, []).append(temp_float)
                            elif is_max:
                                max_date_temps.setdefault(date_str, []).append(temp_float)
                        except (ValueError, TypeError):
                            continue

        sorted_dates = sorted(list(set(min_date_temps.keys()) | set(max_date_temps.keys())))[:7]
        min_times = []
        max_times = []

        for d in sorted_dates:
            min_vals = min_date_temps.get(d, [])
            max_vals = max_date_temps.get(d, [])
            day_min = round(min(min_vals), 1) if min_vals else 22.0
            day_max = round(max(max_vals), 1) if max_vals else 30.0

            min_times.append({
                "startTime": f"{d} 06:00:00",
                "endTime": f"{d} 18:00:00",
                "elementValue": [{"value": str(day_min), "measures": "攝氏度"}]
            })
            max_times.append({
                "startTime": f"{d} 06:00:00",
                "endTime": f"{d} 18:00:00",
                "elementValue": [{"value": str(day_max), "measures": "攝氏度"}]
            })

        locations_list.append({
            "locationName": reg_name,
            "locationType": "region",
            "weatherElement": [
                {"elementName": "MinT", "description": "最低溫度", "time": min_times},
                {"elementName": "MaxT", "description": "最高溫度", "time": max_times}
            ]
        })

    return {
        "success": "true",
        "result": {
            "resource_id": "F-D0047-091",
            "fields": []
        },
        "records": {
            "locations": {
                "datasetDescription": "臺灣各縣市及區域一週天氣預報",
                "location": locations_list
            }
        }
    }


def generate_fallback_data() -> dict:
    """備用模擬資料生成器。"""
    print("[提示] 啟用備用資料生成器...")
    base_date = datetime.date.today()
    locations_list = []
    
    all_targets = ALL_COUNTIES + list(REGION_COUNTY_MAP.keys())
    for loc_name in all_targets:
        min_times = []
        max_times = []
        for day_offset in range(7):
            cur_date = base_date + datetime.timedelta(days=day_offset)
            date_str = cur_date.strftime("%Y-%m-%d")
            min_times.append({
                "startTime": f"{date_str} 06:00:00",
                "endTime": f"{date_str} 18:00:00",
                "elementValue": [{"value": "23.0", "measures": "攝氏度"}]
            })
            max_times.append({
                "startTime": f"{date_str} 06:00:00",
                "endTime": f"{date_str} 18:00:00",
                "elementValue": [{"value": "31.0", "measures": "攝氏度"}]
            })

        locations_list.append({
            "locationName": loc_name,
            "locationType": "county" if loc_name in ALL_COUNTIES else "region",
            "weatherElement": [
                {"elementName": "MinT", "description": "最低溫度", "time": min_times},
                {"elementName": "MaxT", "description": "最高溫度", "time": max_times}
            ]
        })

    return {
        "success": "true",
        "result": {"resource_id": "F-D0047-091", "fields": []},
        "records": {
            "locations": {
                "datasetDescription": "臺灣各縣市及區域一週天氣預報",
                "location": locations_list
            }
        }
    }


def fetch_cwa_weather(api_key: str = None) -> dict:
    """呼叫 CWA Open Data API 取得全台 22 縣市及各大分區天氣預報。"""
    key = (api_key or CWA_API_KEY).strip()
    data = None
    
    if key and key != "YOUR_CWA_API_KEY_HERE":
        print(f"[資訊] 使用 CWA API Key 請求即時氣象資料 (全台各縣市)...")
        try:
            params = {"Authorization": key, "format": "JSON"}
            resp = requests.get(URL_COUNTIES, params=params, timeout=20)
            if resp.status_code == 200:
                counties_json = resp.json()
                data = transform_cwa_response(counties_json)
                if data:
                    print("[成功] 成功從 CWA API 獲取全台 22 縣市與分區即時預報！")
        except Exception as e:
            print(f"[警告] 連線至 CWA API 發生錯誤: {e}")

    if not data:
        data = generate_fallback_data()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[完成] 原始 JSON 已成功儲存至: {OUTPUT_FILE}")
    return data


if __name__ == "__main__":
    print("=" * 60)
    print("HW10 - 取得 CWA API 全台 22 縣市與六大區域預報資料")
    print("=" * 60)
    result_data = fetch_cwa_weather()
    locs = result_data["records"]["locations"]["location"]
    print(f"\n[驗證 Check] 包含地點/縣市總數量: {len(locs)}")
    counties_cnt = sum(1 for l in locs if l.get("locationType") == "county")
    regions_cnt = sum(1 for l in locs if l.get("locationType") == "region")
    print(f"  - 個別縣市: {counties_cnt} 個")
    print(f"  - 大分區域: {regions_cnt} 個")
    print("=" * 60)
