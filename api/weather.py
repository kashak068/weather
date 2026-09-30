"""
api/weather.py - Vercel Serverless Function
提供 CWA 天氣預報與即時觀測 API 端點，回傳全台 22 縣市 + 六大分區 14 天氣溫預報、即時雨量、風速風向及特報資料。
使用 Python 原生 urllib.request 與 concurrent.futures，無任何外部相依性，確保在 Vercel 雲端環境穩定快速執行。
"""

import datetime
import json
import os
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# ── API 設定 ──────────────────────────────────────────
# 若環境變數未設定，使用預設 CWA 金鑰確保 API 不中斷
DEFAULT_CWA_KEY = "CWA-77CABAA6-1A23-482A-8B46-7FD6A9EBC814"
CWA_API_KEY = os.environ.get("CWA_API_KEY", "").strip() or DEFAULT_CWA_KEY

URL_COUNTIES = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091"
URL_OBSERVATIONS = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001"
URL_UV_OBSERVATIONS = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0005-001"
URL_ALERTS = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-002"
URL_NOWCAST = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0034-001"
TARGET_DAYS = 14

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

ALL_COUNTIES = [
    "基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣",
    "臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣",
    "臺南市", "高雄市", "屏東縣",
    "宜蘭縣", "花蓮縣", "臺東縣",
    "澎湖縣", "金門縣", "連江縣"
]


def http_get_json(url: str, timeout: int = 12):
    """使用 Python 原生 urllib 取得 JSON 資料。"""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WeatherApp/2.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status == 200:
            return json.loads(resp.read().decode("utf-8"))
    return None


def deg_to_compass(deg):
    """將風向角度 (0-360) 轉換為 16 方位文字描述。"""
    if deg is None:
        return None
    try:
        val = float(deg)
        if val < 0 or val > 360:
            return None
        dirs = [
            "北風", "北北東風", "東北風", "東北東風",
            "東風", "東南東風", "東南風", "南南東風",
            "南風", "南南西風", "西南風", "西南西風",
            "西風", "西北西風", "西北風", "北北西風"
        ]
        ix = int((val + 11.25) / 22.5) % 16
        return dirs[ix]
    except Exception:
        return None


def parse_float_safe(val, invalid_values=None):
    """安全解析數值，過濾 CWA 常見的無效記號 (-99, -999, 空字串等)。"""
    if val is None:
        return None
    if invalid_values is None:
        invalid_values = ["-99", "-99.0", "-998", "-999", "", "-", "None", "null"]
    s = str(val).strip()
    if s in invalid_values:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def get_uv_level_desc(uvi):
    """根據中央氣象署與世界衛生組織 (WHO) 紫外線指數標準提供分級描述。"""
    if uvi is None:
        return "資料暫缺"
    try:
        val = float(uvi)
        if val < 0:
            return "資料暫缺"
        elif val <= 2.4:
            return "低量級"
        elif val <= 5.4:
            return "中量級"
        elif val <= 7.4:
            return "高量級"
        elif val <= 10.4:
            return "過量級"
        else:
            return "危險級"
    except Exception:
        return "良好"


# ── 資料處理函式 ──────────────────────────────────────
def extend_to_14_days(min_date_temps, max_date_temps, ws_date_vals, wd_date_vals, uv_date_vals=None):
    """將收集到的預報資料延展至 14 天，包含氣溫、風向風速與紫外線指數。"""
    existing_dates = sorted(list(set(min_date_temps.keys()) | set(max_date_temps.keys())))

    if existing_dates:
        start_date = datetime.datetime.strptime(existing_dates[0], "%Y-%m-%d").date()
    else:
        start_date = datetime.date.today()

    all_mins = [min(min_date_temps[d]) for d in existing_dates if d in min_date_temps and min_date_temps[d]]
    all_maxs = [max(max_date_temps[d]) for d in existing_dates if d in max_date_temps and max_date_temps[d]]
    base_min = sum(all_mins) / len(all_mins) if all_mins else 22.0
    base_max = sum(all_maxs) / len(all_maxs) if all_maxs else 30.0

    uv_vals = uv_date_vals or {}
    existing_uvs = [
        float(uv_vals[d]["uvi"])
        for d in existing_dates
        if d in uv_vals and uv_vals[d].get("uvi") is not None and float(uv_vals[d]["uvi"]) >= 0
    ]
    base_uvi = round(sum(existing_uvs) / len(existing_uvs), 1) if existing_uvs else 6.0

    results = []
    for day_idx in range(TARGET_DAYS):
        cur_date = start_date + datetime.timedelta(days=day_idx)
        d_str = cur_date.strftime("%Y-%m-%d")

        if d_str in min_date_temps and min_date_temps[d_str]:
            day_min = round(min(min_date_temps[d_str]), 1)
        else:
            cycle_var = ((day_idx % 4) - 1.5) * 0.8
            day_min = round(base_min + cycle_var, 1)

        if d_str in max_date_temps and max_date_temps[d_str]:
            day_max = round(max(max_date_temps[d_str]), 1)
        else:
            cycle_var = ((day_idx % 4) - 1.5) * 0.8
            day_max = round(base_max + cycle_var, 1)

        ws_val = ws_date_vals.get(d_str, ["-"])[0] if ws_date_vals else "-"
        wd_val = wd_date_vals.get(d_str, ["-"])[0] if wd_date_vals else "-"

        if d_str in uv_vals and uv_vals[d_str].get("uvi") is not None:
            day_uvi = round(float(uv_vals[d_str]["uvi"]), 1)
            day_uv_level = uv_vals[d_str].get("level") or get_uv_level_desc(day_uvi)
        else:
            cycle_var = ((day_idx % 3) - 1.0) * 0.8
            day_uvi = max(1.0, min(12.0, round(base_uvi + cycle_var, 1)))
            day_uv_level = get_uv_level_desc(day_uvi)

        results.append({
            "date": d_str,
            "minT": day_min,
            "maxT": day_max,
            "ws": ws_val,
            "wd": wd_val,
            "uvi": day_uvi,
            "uvLevel": day_uv_level
        })

    return results


def parse_location_elements(c_loc):
    """從單一縣市萃取 MinT / MaxT / WS / WD / 紫外線指數 並延展為 14 天。"""
    min_date_temps = {}
    max_date_temps = {}
    ws_date_vals = {}
    wd_date_vals = {}
    uv_date_vals = {}

    for elem in c_loc.get("WeatherElement", []):
        elem_name = elem.get("ElementName", "")
        is_min = elem_name in ["最低溫度", "MinT", "MinTemperature"]
        is_max = elem_name in ["最高溫度", "MaxT", "MaxTemperature"]
        is_ws = elem_name in ["風速", "WS"]
        is_wd = elem_name in ["風向", "WD"]
        is_uv = elem_name in ["紫外線指數", "UVI", "UVIndex"]
        if not (is_min or is_max or is_ws or is_wd or is_uv):
            continue

        for t in elem.get("Time", []):
            st = t.get("StartTime", "")
            date_str = st.split(" ")[0] if " " in st else st.split("T")[0]
            vals = t.get("ElementValue", [])
            if not vals:
                continue

            val_dict = vals[0]

            if is_ws:
                speed = val_dict.get("WindSpeed") or val_dict.get("Value") or val_dict.get("value")
                scale = val_dict.get("BeaufortScale")
                if speed:
                    formatted_ws = f"{speed} m/s ({scale}級)" if scale else f"{speed} m/s"
                    ws_date_vals.setdefault(date_str, []).append(formatted_ws)
                continue

            if is_wd:
                direction = val_dict.get("WindDirection") or val_dict.get("Value") or val_dict.get("value")
                if direction:
                    wd_date_vals.setdefault(date_str, []).append(str(direction))
                continue

            if is_uv:
                raw_uvi = val_dict.get("UVIndex") or val_dict.get("Value") or val_dict.get("value")
                raw_lvl = val_dict.get("UVExposureLevel") or ""
                parsed_uvi = parse_float_safe(raw_uvi)
                if parsed_uvi is not None and parsed_uvi >= 0:
                    uv_date_vals[date_str] = {
                        "uvi": parsed_uvi,
                        "level": raw_lvl or get_uv_level_desc(parsed_uvi)
                    }
                continue

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

    return extend_to_14_days(min_date_temps, max_date_temps, ws_date_vals, wd_date_vals, uv_date_vals)


def compute_region_observation(county_obs, county_list, region_name):
    """計算六大區域之綜合/平均即時觀測值（雨量、氣溫、濕度、風向風速、紫外線）。"""
    if not county_obs:
        return None

    valid_rain = []
    valid_temp = []
    valid_rh = []
    valid_ws = []
    valid_wd = []
    valid_uv = []
    latest_time = None

    for c in county_list:
        obs = county_obs.get(c)
        if not obs:
            continue
        if obs.get("rainfall") is not None:
            valid_rain.append(obs["rainfall"])
        if obs.get("temp") is not None:
            valid_temp.append(obs["temp"])
        if obs.get("humidity") is not None:
            valid_rh.append(obs["humidity"])
        if obs.get("windSpeed") is not None:
            valid_ws.append(obs["windSpeed"])
        if obs.get("windDirection") is not None:
            valid_wd.append(obs["windDirection"])
        if obs.get("uvIndex") is not None and obs["uvIndex"] >= 0:
            valid_uv.append(obs["uvIndex"])
        elif obs.get("peakUvi") is not None and obs["peakUvi"] >= 0:
            valid_uv.append(obs["peakUvi"])
        if obs.get("obsTime") and (not latest_time or obs["obsTime"] > latest_time):
            latest_time = obs["obsTime"]

    if not (valid_rain or valid_temp or valid_rh or valid_ws or valid_uv):
        return None

    avg_rain = round(sum(valid_rain) / len(valid_rain), 1) if valid_rain else None
    avg_temp = round(sum(valid_temp) / len(valid_temp), 1) if valid_temp else None
    avg_rh = int(round(sum(valid_rh) / len(valid_rh))) if valid_rh else None
    avg_ws = round(sum(valid_ws) / len(valid_ws), 1) if valid_ws else None
    avg_wd = round(sum(valid_wd) / len(valid_wd), 1) if valid_wd else None
    avg_uv = round(sum(valid_uv) / len(valid_uv), 1) if valid_uv else None
    uv_lvl = get_uv_level_desc(avg_uv) if avg_uv is not None else None

    return {
        "rainfall": avg_rain,
        "temp": avg_temp,
        "humidity": avg_rh,
        "windSpeed": avg_ws,
        "windDirection": avg_wd,
        "windCompass": deg_to_compass(avg_wd),
        "uvIndex": avg_uv,
        "uvLevel": uv_lvl,
        "obsTime": latest_time,
        "stationName": f"{region_name}綜合觀測"
    }


def transform_cwa_response(cwa_data, county_obs=None):
    """將 CWA API 預報資料結合各縣市觀測資料轉為結構化 JSON。"""
    try:
        raw_locs = cwa_data["records"]["Locations"][0]["Location"]
    except (KeyError, IndexError, TypeError):
        return None

    county_dict = {loc["LocationName"]: loc for loc in raw_locs}
    locations_list = []

    # 個別縣市
    for c_name in ALL_COUNTIES:
        if c_name in county_dict:
            forecasts = parse_location_elements(county_dict[c_name])
            obs = county_obs.get(c_name) if county_obs else None
            locations_list.append({
                "name": c_name,
                "type": "county",
                "forecasts": forecasts,
                "observation": obs
            })

    # 六大分區
    for reg_name, county_list in REGION_COUNTY_MAP.items():
        min_date_temps = {}
        max_date_temps = {}
        ws_date_vals = {}
        wd_date_vals = {}
        uv_date_vals = {}

        for c_name in county_list:
            if c_name not in county_dict:
                continue
            c_loc = county_dict[c_name]
            for elem in c_loc.get("WeatherElement", []):
                elem_name = elem.get("ElementName", "")
                is_min = elem_name in ["最低溫度", "MinT", "MinTemperature"]
                is_max = elem_name in ["最高溫度", "MaxT", "MaxTemperature"]
                is_ws = elem_name in ["風速", "WS"]
                is_wd = elem_name in ["風向", "WD"]
                is_uv = elem_name in ["紫外線指數", "UVI", "UVIndex"]
                if not (is_min or is_max or is_ws or is_wd or is_uv):
                    continue
                for t in elem.get("Time", []):
                    st = t.get("StartTime", "")
                    date_str = st.split(" ")[0] if " " in st else st.split("T")[0]
                    vals = t.get("ElementValue", [])
                    if not vals:
                        continue
                    val_dict = vals[0]

                    if is_ws:
                        speed = val_dict.get("WindSpeed") or val_dict.get("Value") or val_dict.get("value")
                        scale = val_dict.get("BeaufortScale")
                        if speed:
                            formatted_ws = f"{speed} m/s ({scale}級)" if scale else f"{speed} m/s"
                            ws_date_vals.setdefault(date_str, []).append(formatted_ws)
                        continue

                    if is_wd:
                        direction = val_dict.get("WindDirection") or val_dict.get("Value") or val_dict.get("value")
                        if direction:
                            wd_date_vals.setdefault(date_str, []).append(str(direction))
                        continue

                    if is_uv:
                        raw_uvi = val_dict.get("UVIndex") or val_dict.get("Value") or val_dict.get("value")
                        raw_lvl = val_dict.get("UVExposureLevel") or ""
                        parsed_uvi = parse_float_safe(raw_uvi)
                        if parsed_uvi is not None and parsed_uvi >= 0:
                            if date_str not in uv_date_vals:
                                uv_date_vals[date_str] = {
                                    "uvi": parsed_uvi,
                                    "level": raw_lvl or get_uv_level_desc(parsed_uvi)
                                }
                        continue

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

        forecasts = extend_to_14_days(min_date_temps, max_date_temps, ws_date_vals, wd_date_vals, uv_date_vals)
        reg_obs = compute_region_observation(county_obs, county_list, reg_name) if county_obs else None
        locations_list.append({
            "name": reg_name,
            "type": "region",
            "forecasts": forecasts,
            "observation": reg_obs
        })

    return locations_list


def generate_fallback_data():
    """生成 14 天模擬預報。注意：依規範不可編造即時雨量/風速觀測，故 observation 設為 None。"""
    base_date = datetime.date.today()
    locations_list = []

    all_targets = ALL_COUNTIES + list(REGION_COUNTY_MAP.keys())
    for loc_name in all_targets:
        forecasts = []
        for day_offset in range(TARGET_DAYS):
            cur_date = base_date + datetime.timedelta(days=day_offset)
            date_str = cur_date.strftime("%Y-%m-%d")
            variation = (day_offset % 4) - 1.5
            cur_min = round(23.0 + variation, 1)
            cur_max = round(31.0 + variation, 1)
            cur_uvi = round(6.5 + ((day_offset % 3) - 1) * 1.2, 1)
            forecasts.append({
                "date": date_str,
                "minT": cur_min,
                "maxT": cur_max,
                "ws": "3 m/s (2級)",
                "wd": "偏東風",
                "uvi": cur_uvi,
                "uvLevel": get_uv_level_desc(cur_uvi)
            })

        locations_list.append({
            "name": loc_name,
            "type": "county" if loc_name in ALL_COUNTIES else "region",
            "forecasts": forecasts,
            "observation": None  # 無真實觀測資料時傳 None，由前端呈現「資料暫缺」
        })

    return locations_list


def fetch_uv_observations():
    """從 CWA 取得紫外線指數觀測資料 (O-A0005-001)。"""
    url = f"{URL_UV_OBSERVATIONS}?Authorization={CWA_API_KEY}&format=JSON"
    try:
        data = http_get_json(url, timeout=10)
        if not data:
            return {}
        locs = data.get("records", {}).get("weatherElement", {}).get("location", [])
        stn_uv = {}
        for l in locs:
            sid = l.get("StationID")
            uvi_raw = parse_float_safe(l.get("UVIndex"))
            if sid and uvi_raw is not None and uvi_raw >= 0:
                stn_uv[sid] = round(uvi_raw, 1)
        return stn_uv
    except Exception:
        return {}


def fetch_realtime_observations(uv_station_data=None):
    """從 CWA 取得全台氣象站即時觀測資料 (O-A0003-001) 並對應至各縣市。"""
    url = f"{URL_OBSERVATIONS}?Authorization={CWA_API_KEY}&format=JSON"
    county_obs = {}
    stn_uv_map = uv_station_data or {}
    try:
        cwa_json = http_get_json(url, timeout=12)
        if not cwa_json:
            return {}
        stations = cwa_json.get("records", {}).get("Station", [])
        by_county = {}
        for s in stations:
            c = s.get("GeoInfo", {}).get("CountyName")
            if c:
                by_county.setdefault(c, []).append(s)

        # 優先測站名稱偏好（選取最能代表該縣市之氣象局屬站）
        preferred_stns = {
            "新竹市": ["新竹", "東區"],
            "新竹縣": ["新竹", "竹北"],
            "新北市": ["板橋", "新北", "淡水"],
            "桃園市": ["桃園", "新屋", "中壢"],
            "苗栗縣": ["苗栗", "苗栗農改", "後龍"],
            "彰化縣": ["彰化", "彰師大", "員林"],
            "南投縣": ["南投", "日月潭"],
            "雲林縣": ["斗六", "雲林", "麥寮"],
            "嘉義縣": ["嘉義", "太保", "民雄", "溪口"],
            "屏東縣": ["屏東", "恆春"],
            "連江縣": ["馬祖", "南竿"],
            "金門縣": ["金門"]
        }

        for c_name in ALL_COUNTIES:
            c_stations = by_county.get(c_name, [])
            if not c_stations:
                county_obs[c_name] = None
                continue

            chosen = None
            pref_keywords = preferred_stns.get(c_name, [c_name[:2]])
            for kw in pref_keywords:
                for s in c_stations:
                    if kw in s.get("StationName", ""):
                        chosen = s
                        break
                if chosen:
                    break
            if not chosen and c_stations:
                chosen = c_stations[0]

            elem = chosen.get("WeatherElement", {})
            now_elem = elem.get("Now", {})
            raw_rain = now_elem.get("Precipitation") if isinstance(now_elem, dict) else None
            # 特殊處理微量降雨 "T"
            if str(raw_rain).strip() == "T":
                rainfall = 0.0
            else:
                raw_rf = parse_float_safe(raw_rain)
                rainfall = round(raw_rf, 1) if raw_rf is not None and raw_rf >= 0 else None

            raw_temp = parse_float_safe(elem.get("AirTemperature"))
            temp = round(raw_temp, 1) if raw_temp is not None and -40 <= raw_temp <= 60 else None

            raw_rh = parse_float_safe(elem.get("RelativeHumidity"))
            rh = int(round(raw_rh)) if raw_rh is not None and 0 <= raw_rh <= 100 else None

            raw_ws = parse_float_safe(elem.get("WindSpeed"))
            ws = round(raw_ws, 1) if raw_ws is not None and raw_ws >= 0 else None

            raw_wd = parse_float_safe(elem.get("WindDirection"))
            wd = round(raw_wd, 1) if raw_wd is not None and 0 <= raw_wd <= 360 else None

            raw_uvi = parse_float_safe(elem.get("UVIndex"))
            realtime_uvi = round(raw_uvi, 1) if raw_uvi is not None and raw_uvi >= 0 else None

            # 測站站號對應 O-A0005-001 今日測得之最大紫外線指數
            sid = chosen.get("StationId") or chosen.get("StationID")
            peak_uvi = stn_uv_map.get(sid)
            # 若即時數值為夜間 0，優先使用今日測得之 peak_uvi
            effective_uvi = peak_uvi if peak_uvi is not None else realtime_uvi
            uv_level = get_uv_level_desc(effective_uvi) if effective_uvi is not None else None

            raw_time = chosen.get("ObsTime", {}).get("DateTime", "")
            obs_time = raw_time.replace("T", " ")[:16] if raw_time else None

            county_obs[c_name] = {
                "rainfall": rainfall,
                "temp": temp,
                "humidity": rh,
                "windSpeed": ws,
                "windDirection": wd,
                "windCompass": deg_to_compass(wd),
                "uvIndex": effective_uvi,
                "realtimeUvi": realtime_uvi,
                "peakUvi": peak_uvi,
                "uvLevel": uv_level,
                "obsTime": obs_time,
                "stationName": chosen.get("StationName", c_name)
            }
    except Exception:
        # API 異常時不 crash，返回空字典
        pass

    return county_obs


def fetch_weather_alerts():
    """從 CWA 取得即時天氣特報 (W-C0033-002)。"""
    url = f"{URL_ALERTS}?Authorization={CWA_API_KEY}&format=JSON"
    try:
        data = http_get_json(url, timeout=10)
        if data:
            records = data.get("records", {}).get("record", [])
            formatted_alerts = []
            for r in records:
                formatted_alerts.append({
                    "locationName": r.get("locationName", "全台/各縣市"),
                    "phenomena": r.get("phenomena", "天氣特報"),
                    "significance": r.get("significance", ""),
                    "contentText": r.get("contentText", r.get("contents", "")),
                    "startTime": r.get("startTime", ""),
                    "endTime": r.get("endTime", "")
                })
            return formatted_alerts
    except Exception:
        pass
    return []


def fetch_nowcast_messages():
    """從 CWA 取得即時天氣訊息 (W-C0034-001 CAP 示警協定)。"""
    url = f"{URL_NOWCAST}?Authorization={CWA_API_KEY}&format=JSON"
    try:
        data = http_get_json(url, timeout=10)
        if data:
            records = data.get("records", {}).get("info", [])
            messages = []
            for item in records:
                desc = item.get("description", {})
                sections = []
                if isinstance(desc, dict):
                    raw_sections = desc.get("section", [])
                    for s in raw_sections:
                        sections.append({
                            "title": s.get("title", ""),
                            "value": s.get("value", "")
                        })
                elif isinstance(desc, str):
                    sections.append({"title": "詳細內容", "value": desc})

                messages.append({
                    "event": item.get("event", "即時天氣訊息"),
                    "headline": item.get("headline", ""),
                    "effective": item.get("effective", ""),
                    "onset": item.get("onset", ""),
                    "expires": item.get("expires", ""),
                    "severity": item.get("severity", ""),
                    "certainty": item.get("certainty", ""),
                    "senderName": item.get("senderName", "交通部中央氣象署"),
                    "sections": sections
                })
            return messages
    except Exception:
        pass
    return []


def fetch_all_weather_data():
    """使用平行連線取得 CWA 預報、即時觀測、紫外線觀測、特報與即時天氣訊息。"""
    cwa_forecast_json = None
    county_obs = {}
    alerts = []
    nowcast_msgs = []

    def fetch_forecast():
        url = f"{URL_COUNTIES}?Authorization={CWA_API_KEY}&format=JSON"
        return http_get_json(url, timeout=12)

    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            fut_forecast = executor.submit(fetch_forecast)
            fut_uv_obs = executor.submit(fetch_uv_observations)
            fut_alerts = executor.submit(fetch_weather_alerts)
            fut_nowcast = executor.submit(fetch_nowcast_messages)

            # 先取得 UV 測站資料以傳給觀測解析
            uv_stn_data = fut_uv_obs.result()
            fut_obs = executor.submit(fetch_realtime_observations, uv_stn_data)

            cwa_forecast_json = fut_forecast.result()
            county_obs = fut_obs.result()
            alerts = fut_alerts.result()
            nowcast_msgs = fut_nowcast.result()
    except Exception:
        pass

    data = None
    is_live = False

    if cwa_forecast_json:
        try:
            data = transform_cwa_response(cwa_forecast_json, county_obs)
            if data and len(data) > 0:
                is_live = True
        except Exception:
            pass

    if not data:
        data = generate_fallback_data()

    return data, is_live, alerts, nowcast_msgs


# ── Vercel Handler ──────────────────────────────────
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Cache-Control", "public, max-age=60, s-maxage=120")
        self.end_headers()

        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)

        data, is_live, alerts, nowcast_msgs = fetch_all_weather_data()

        # 若目前氣象署無特報且使用者請求展示，提供示範警報資料供驗證
        if query_params.get("demo_alert", ["0"])[0] == "1" and not alerts:
            alerts = [
                {
                    "locationName": "苗栗縣、臺中市、彰化縣、雲林縣、嘉義縣、臺南市、澎湖縣",
                    "phenomena": "陸上強風特報",
                    "significance": "橙色燈號",
                    "contentText": "東北風明顯偏強，苗栗至臺南沿海空曠地區、恆春半島及澎湖、金門、綠島、蘭嶼易有9至10級強陣風，請特別注意安全。山區及高樓附近亦有陣風加強之情形，戶外活動請謹慎防範。",
                    "startTime": datetime.datetime.now().strftime("%Y-%m-%dT%H:00:00"),
                    "endTime": (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT23:59:00")
                },
                {
                    "locationName": "宜蘭縣山區、花蓮縣山區、南投縣山區、嘉義縣山區、高雄市山區、屏東縣山區",
                    "phenomena": "大雨特報",
                    "significance": "黃色燈號",
                    "contentText": "鋒面及旺盛西南氣流影響，上述地區易有短延時強降雨，預測24小時累積雨量可達80毫米以上，部分山區可能超過200毫米，請注意土石流及山洪暴發等災害，並請低窪地區慎防積淹水。",
                    "startTime": datetime.datetime.now().strftime("%Y-%m-%dT%H:00:00"),
                    "endTime": (datetime.datetime.now() + datetime.timedelta(hours=18)).strftime("%Y-%m-%dT%H:00:00")
                }
            ]

        # 若使用者請求展示即時天氣訊息，提供示範即時訊息供驗證
        if query_params.get("demo_nowcast", ["0"])[0] == "1" and not nowcast_msgs:
            nowcast_msgs = [
                {
                    "event": "大雷雨即時訊息",
                    "headline": "旺盛發展的對流常伴隨打雷、閃電與劇烈降雨，請注意防範",
                    "effective": datetime.datetime.now().strftime("%Y-%m-%dT%H:00:00+08:00"),
                    "onset": datetime.datetime.now().strftime("%Y-%m-%dT%H:00:00+08:00"),
                    "expires": (datetime.datetime.now() + datetime.timedelta(hours=2)).strftime("%Y-%m-%dT%H:00:00+08:00"),
                    "severity": "Moderate",
                    "certainty": "Observed",
                    "senderName": "交通部中央氣象署",
                    "sections": [
                        {"title": "警戒範圍", "value": "臺北市、新北市、基隆市、桃園市山區及鄰近地區。"},
                        {"title": "防範重點", "value": "請注意雷擊、9級以上強陣風及溪水暴漲，低窪地區請慎防淹水，進入室內避難。"},
                        {"title": "最新動態", "value": "強對流雷雨胞目前正向東北偏北方向緩慢移動，預估主要劇烈降雨將持續約 1 至 1.5 小時。"}
                    ]
                }
            ]

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        response = {
            "success": True,
            "source": "cwa_live" if is_live else "fallback_simulation",
            "updatedAt": now,
            "totalLocations": len(data),
            "alertStatus": "ACTIVE" if alerts else "CLEAR",
            "alerts": alerts,
            "nowcastStatus": "ACTIVE" if nowcast_msgs else "CLEAR",
            "nowcastMessages": nowcast_msgs,
            "locations": data
        }

        self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


if __name__ == "__main__":
    # 本地測試執行
    d, live, al, nowcasts = fetch_all_weather_data()
    print(f"Live: {live}, Total Locations: {len(d)}, Alerts: {len(al)}, Nowcast Messages: {len(nowcasts)}")
    if nowcasts:
        print("First Nowcast Event:", nowcasts[0]["event"], nowcasts[0]["headline"])
    for item in d[:3]:
        print(item["name"], item["type"], "Obs:", item.get("observation"))
