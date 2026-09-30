"""
app.py - HW10 Taiwan Weather Forecast (Google Maps 風格)
技術棧: Streamlit × SQLite (data.db) × Folium (Google Maps 圖磚) × 現代清晰卡片設計
"""

import datetime
import os
import sqlite3
import folium
from folium.plugins import Fullscreen
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# 頁面配置
st.set_page_config(
    page_title="Taiwan Weather Forecast - 臺灣氣候觀測與預報",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 資料庫路徑
DB_FILE = "data.db"
TABLE_NAME = "TemperatureForecasts"

# 全台 22 縣市中心座標 (緯度, 經度)
COUNTY_COORDINATES = {
    "基隆市": (25.1276, 121.7392),
    "臺北市": (25.0375, 121.5637),
    "新北市": (25.0169, 121.4628),
    "桃園市": (24.9936, 121.3010),
    "新竹市": (24.8138, 120.9675),
    "新竹縣": (24.8387, 121.0177),
    "苗栗縣": (24.5602, 120.8214),
    "臺中市": (24.1477, 120.6736),
    "彰化縣": (24.0518, 120.5161),
    "南投縣": (23.9609, 120.9719),
    "雲林縣": (23.7092, 120.4313),
    "嘉義市": (23.4800, 120.4491),
    "嘉義縣": (23.4518, 120.2555),
    "臺南市": (22.9997, 120.2270),
    "高雄市": (22.6273, 120.3014),
    "屏東縣": (22.5519, 120.5487),
    "宜蘭縣": (24.7021, 121.7377),
    "花蓮縣": (23.9871, 121.6016),
    "臺東縣": (22.7583, 121.1444),
    "澎湖縣": (23.5711, 119.5793),
    "金門縣": (24.4492, 118.3766),
    "連江縣": (26.1505, 119.9499),
}

REGION_COORDINATES = {
    "北部地區": (25.04, 121.55),
    "中部地區": (24.15, 120.67),
    "南部地區": (22.99, 120.21),
    "東北部地區": (24.75, 121.75),
    "東部地區": (23.99, 121.60),
    "東南部地區": (22.75, 121.15),
    "離島地區": (24.00, 119.00),
}

# 縣市依地理分區排序 (北部 → 中部 → 南部 → 東部 → 離島)
COUNTY_REGION_ORDER = {
    # 北部
    "基隆市": (0, 0), "臺北市": (0, 1), "新北市": (0, 2),
    "桃園市": (0, 3), "新竹市": (0, 4), "新竹縣": (0, 5),
    # 中部
    "苗栗縣": (1, 0), "臺中市": (1, 1), "彰化縣": (1, 2),
    "南投縣": (1, 3), "雲林縣": (1, 4),
    # 南部
    "嘉義市": (2, 0), "嘉義縣": (2, 1), "臺南市": (2, 2),
    "高雄市": (2, 3), "屏東縣": (2, 4),
    # 東部
    "宜蘭縣": (3, 0), "花蓮縣": (3, 1), "臺東縣": (3, 2),
    # 離島
    "澎湖縣": (4, 0), "金門縣": (4, 1), "連江縣": (4, 2),
}

REGION_GROUP_ORDER = {
    "北部地區": (0, 0),
    "中部地區": (1, 0),
    "南部地區": (2, 0),
    "東北部地區": (3, 0), "東部地區": (3, 1), "東南部地區": (3, 2),
    "離島地區": (4, 0),
}

COUNTY_REGION_LABELS = {
    0: "── 北部 ──",
    1: "── 中部 ──",
    2: "── 南部 ──",
    3: "── 東部 ──",
    4: "── 離島 ──",
}

REGION_GROUP_LABELS = {
    0: "── 北部 ──",
    1: "── 中部 ──",
    2: "── 南部 ──",
    3: "── 東部 ──",
    4: "── 離島 ──",
}


def sort_locations_by_region(locations: list, is_county: bool = True) -> list:
    """依地理分區排序地點清單。"""
    order_dict = COUNTY_REGION_ORDER if is_county else REGION_GROUP_ORDER
    return sorted(locations, key=lambda loc: order_dict.get(loc, (99, 99)))


def apply_custom_css():
    """注入明亮、清爽、典雅的現代 UI 設計系統。"""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+TC:wght@400;500;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
        }

        /* 乾淨淺色卡片 */
        .clean-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
            margin-bottom: 16px;
        }

        /* 頂部清爽橫幅 */
        .weather-banner {
            background: linear-gradient(135deg, #1D4ED8 0%, #3B82F6 60%, #60A5FA 100%);
            border-radius: 14px;
            padding: 22px 26px;
            color: #FFFFFF;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.2);
            margin-bottom: 22px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .weather-banner-title {
            font-size: 26px;
            font-weight: 700;
            margin: 0 0 6px 0;
            letter-spacing: -0.3px;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 255, 255, 0.2);
            color: #FFFFFF;
            border: 1px solid rgba(255, 255, 255, 0.35);
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
        }

        .green-dot {
            width: 8px;
            height: 8px;
            background-color: #34D399;
            border-radius: 50%;
        }

        /* 溫標漸層色條 */
        .temp-bar-gradient {
            height: 10px;
            width: 100%;
            border-radius: 6px;
            background: linear-gradient(to right, #3B82F6, #60A5FA, #34D399, #FBBF24, #F97316, #EF4444);
            margin: 8px 0 4px 0;
        }

        /* 降雨量漸層色條 */
        .rain-bar-gradient {
            height: 10px;
            width: 100%;
            border-radius: 6px;
            background: linear-gradient(to right, #38BDF8 0%, #0284C7 25%, #1D4ED8 50%, #7E22CE 75%, #C026D3 100%);
            margin: 8px 0 4px 0;
        }

        /* 風速漸層色條 */
        .wind-bar-gradient {
            height: 10px;
            width: 100%;
            border-radius: 6px;
            background: linear-gradient(to right, #0D9488 0%, #2563EB 30%, #D97706 65%, #DC2626 85%, #7C3AED 100%);
            margin: 8px 0 4px 0;
        }

        /* 紫外線漸層色條 */
        .uv-bar-gradient {
            height: 10px;
            width: 100%;
            border-radius: 6px;
            background: linear-gradient(to right, #16A34A 0%, #CA8A04 28%, #EA580C 55%, #DC2626 80%, #9333EA 100%);
            margin: 8px 0 4px 0;
        }

        .legend-badge-unit {
            font-size: 11px;
            font-weight: 600;
            color: #64748B;
            background: #F1F5F9;
            padding: 2px 8px;
            border-radius: 12px;
            float: right;
        }

        /* KPI 指標卡片美化 */
        [data-testid="stMetric"] {
            background: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 12px !important;
            padding: 14px 18px !important;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03) !important;
        }

        /* 按鈕樣式 */
        .stButton>button {
            background-color: #2563EB;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            padding: 6px 16px;
            transition: all 0.2s;
        }
        .stButton>button:hover {
            background-color: #1D4ED8;
            color: white;
        }

        /* Tab 選單 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: #F1F5F9;
            padding: 6px;
            border-radius: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            font-weight: 600;
            padding: 8px 18px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFFFFF !important;
            color: #2563EB !important;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
        }

        /* ========== CWA 氣象特報公告樣式 (仿中央氣象署官方電子報) ========== */

        /* 特報總標題列 */
        .cwa-alert-title-bar {
            background: linear-gradient(135deg, #1a3a5c 0%, #2a5a8c 100%);
            color: #FFFFFF;
            padding: 14px 24px;
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 1px;
            border-radius: 6px 6px 0 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .cwa-alert-title-bar .cwa-icon {
            font-size: 24px;
        }

        /* 單一特報公告卡片 */
        .cwa-alert-bulletin {
            background: #FFFFFF;
            border: 2px solid #2a5a8c;
            border-top: none;
            margin-bottom: 20px;
            border-radius: 0 0 6px 6px;
            overflow: hidden;
        }

        /* 特報類型標題列 (每筆特報) */
        .cwa-alert-type-header {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 20px;
            border-bottom: 1px solid #dee2e6;
            background: #f0f4f8;
        }
        .cwa-alert-type-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 14px;
            border-radius: 4px;
            font-size: 15px;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: 0.5px;
        }
        .cwa-alert-type-badge.severity-red {
            background: #dc3545;
        }
        .cwa-alert-type-badge.severity-orange {
            background: #fd7e14;
        }
        .cwa-alert-type-badge.severity-yellow {
            background: #ffc107;
            color: #333;
        }
        .cwa-alert-type-badge.severity-default {
            background: #6c757d;
        }
        .cwa-alert-significance {
            font-size: 13px;
            color: #6c757d;
            font-weight: 500;
        }

        /* 公告內容區 (仿 CWA border-ltr-blue) */
        .cwa-alert-content {
            padding: 20px 24px;
            border-left: 4px solid #2a5a8c;
            margin: 0 16px 16px 16px;
            background: #fafcff;
        }

        /* 發佈時間 */
        .cwa-alert-datetime {
            font-size: 13px;
            color: #6c757d;
            margin-bottom: 14px;
            padding-bottom: 10px;
            border-bottom: 1px dashed #dee2e6;
        }
        .cwa-alert-datetime strong {
            color: #2a5a8c;
        }

        /* 特報詳細表格 */
        .cwa-alert-meta-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
            font-size: 14px;
        }
        .cwa-alert-meta-table td {
            padding: 8px 12px;
            border: 1px solid #dee2e6;
            vertical-align: top;
        }
        .cwa-alert-meta-table td.label-cell {
            background: #e8eef5;
            color: #2a5a8c;
            font-weight: 600;
            width: 120px;
            white-space: nowrap;
        }
        .cwa-alert-meta-table td.value-cell {
            color: #333;
            line-height: 1.6;
        }

        /* 特報內文 */
        .cwa-alert-body {
            font-size: 14px;
            line-height: 1.8;
            color: #333;
            padding: 14px 16px;
            background: #FFFFFF;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            margin-top: 12px;
        }

        /* 影響區域標籤 */
        .cwa-area-tag {
            display: inline-block;
            padding: 3px 10px;
            margin: 2px 4px 2px 0;
            background: #e8eef5;
            color: #2a5a8c;
            border-radius: 3px;
            font-size: 13px;
            font-weight: 500;
            border: 1px solid #c8d6e5;
        }

        /* 無特報狀態 */
        .cwa-no-alert {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            padding: 20px 24px;
            text-align: center;
            margin-bottom: 20px;
        }
        .cwa-no-alert .icon { font-size: 32px; margin-bottom: 6px; }
        .cwa-no-alert .msg { font-size: 15px; color: #166534; font-weight: 600; }
        .cwa-no-alert .sub { font-size: 12px; color: #6b7280; margin-top: 4px; }

        /* CWA 資訊來源 footer */
        .cwa-source-footer {
            font-size: 11px;
            color: #94a3b8;
            text-align: right;
            padding: 6px 16px;
            border-top: 1px solid #e2e8f0;
            background: #f8fafc;
        }
        </style>
    """, unsafe_allow_html=True)


def get_db_connection():
    if not os.path.exists(DB_FILE):
        return None
    return sqlite3.connect(DB_FILE)


def fetch_location_list(location_type: str = None):
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        if location_type:
            query = f"SELECT DISTINCT regionName FROM {TABLE_NAME} WHERE locationType = ? ORDER BY regionName;"
            df = pd.read_sql_query(query, conn, params=(location_type,))
        else:
            query = f"SELECT DISTINCT regionName FROM {TABLE_NAME} ORDER BY regionName;"
            df = pd.read_sql_query(query, conn)
        return df["regionName"].tolist()
    except Exception:
        return []
    finally:
        conn.close()


def fetch_forecast_data(location_name: str) -> pd.DataFrame:
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        query = f"""
        SELECT dataDate AS Date, minT AS MinT, maxT AS MaxT, ws AS WS, wd AS WD, uvi AS UVI
        FROM {TABLE_NAME}
        WHERE regionName = ?
        ORDER BY dataDate ASC;
        """
        df = pd.read_sql_query(query, conn, params=(location_name,))
        if not df.empty:
            df["AvgT"] = ((df["MinT"] + df["MaxT"]) / 2).round(1)
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def fetch_map_data(location_type: str = "county") -> pd.DataFrame:
    """從 CWA 即時觀測與預報資料彙整地圖所需之各項氣象指標 (雨量、風況、紫外線、氣溫)。"""
    try:
        from api.weather import fetch_all_weather_data, get_uv_level_desc, deg_to_compass
        cwa_data, is_live, alerts, nowcast_msgs = fetch_all_weather_data()
        rows = []
        for loc in cwa_data:
            if loc.get("type") != location_type:
                continue
            obs = loc.get("observation", {}) or {}
            fcsts = loc.get("forecasts", [])
            fcst_today = fcsts[0] if fcsts else {}

            # 降雨量 (mm)
            rainfall = obs.get("rainfall")
            if rainfall is None:
                rainfall = 0.0

            # 風向與風速
            wind_speed = obs.get("windSpeed")
            wind_dir = obs.get("windDirection")
            wind_compass = obs.get("windCompass") or fcst_today.get("windDirection") or "偏東風"
            if wind_speed is None:
                try:
                    wind_speed = float(fcst_today.get("windSpeed", 2))
                except Exception:
                    wind_speed = 2.0
            if wind_dir is None:
                wind_dir = 90.0

            # 紫外線指數
            uvi = obs.get("uvIndex")
            if uvi is None:
                try:
                    uvi = float(fcst_today.get("uvIndex", 5.0))
                except Exception:
                    uvi = 5.0
            uv_level = obs.get("uvLevel") or get_uv_level_desc(uvi)

            # 氣溫
            min_t = fcst_today.get("minT", 22.0)
            max_t = fcst_today.get("maxT", 28.0)
            avg_t = obs.get("temp")
            if avg_t is None:
                avg_t = round((min_t + max_t) / 2, 1)

            rows.append({
                "regionName": loc["name"],
                "locationType": loc["type"],
                "dataDate": fcst_today.get("date", datetime.datetime.now().strftime("%Y-%m-%d")),
                "minT": min_t,
                "maxT": max_t,
                "avgT": avg_t,
                "rainfall": float(rainfall),
                "windSpeed": float(wind_speed),
                "windDirection": float(wind_dir),
                "windCompass": str(wind_compass),
                "uvIndex": float(uvi),
                "uvLevel": str(uv_level),
                "obsTime": obs.get("obsTime", ""),
                "stationName": obs.get("stationName", loc["name"])
            })
        if rows:
            return pd.DataFrame(rows)
    except Exception:
        pass

    # 若 API 連線受限，從本地 data.db 讀取已同步之 CWA 預報資料
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        query = f"""
        SELECT t.regionName, t.locationType, t.dataDate, t.minT, t.maxT, t.ws, t.wd, t.uvi
        FROM {TABLE_NAME} t
        INNER JOIN (
            SELECT regionName, MIN(dataDate) as minDate
            FROM {TABLE_NAME}
            GROUP BY regionName
        ) m ON t.regionName = m.regionName AND t.dataDate = m.minDate
        WHERE t.locationType = ?;
        """
        df = pd.read_sql_query(query, conn, params=(location_type,))
        if not df.empty:
            df["avgT"] = ((df["minT"] + df["maxT"]) / 2).round(1)
            df["rainfall"] = 0.0
            def safe_float(v, default=0.0):
                try:
                    return float(v)
                except Exception:
                    return default
            df["windSpeed"] = df["ws"].apply(lambda v: safe_float(v, 2.0))
            df["windDirection"] = 90.0
            df["windCompass"] = df["wd"].fillna("偏東風")
            df["uvIndex"] = df["uvi"].apply(lambda v: safe_float(v, 5.0))
            from api.weather import get_uv_level_desc
            df["uvLevel"] = df["uvIndex"].apply(get_uv_level_desc)
            df["obsTime"] = ""
            df["stationName"] = df["regionName"]
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def fetch_nowcast_messages():
    """從 CWA 取得即時天氣訊息 (W-C0034-001 CAP 示警協定)。"""
    try:
        from api.weather import fetch_nowcast_messages as _fetch_nowcasts
        return _fetch_nowcasts()
    except Exception:
        return []


def render_cwa_nowcast_bulletin(nowcasts: list):
    """呈現中央氣象署即時天氣訊息 (W-C0034-001)。"""
    if not nowcasts:
        st.markdown("""
            <div style="background: #ECFEFF; border: 1px solid #A5F3FC; border-left: 5px solid #06B6D4; border-radius: 8px; padding: 12px 18px; margin-bottom: 16px; font-size: 13px; color: #0E7490; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 16px;">📢</span>
                <span><b>即時天氣訊息 (Nowcast)：</b>中央氣象署目前無突發性劇烈天氣訊息發布 (W-C0034-001 即時連線)。</span>
            </div>
        """, unsafe_allow_html=True)
        return

    for item in nowcasts:
        event = item.get("event", "即時天氣訊息")
        headline = item.get("headline", "")
        effective = item.get("effective", "").replace("T", " ")[:16]
        expires = item.get("expires", "").replace("T", " ")[:16]
        sender = item.get("senderName", "交通部中央氣象署")
        sections = item.get("sections", [])

        st.markdown(f"""
            <div style="border-radius: 8px; overflow: hidden; border: 1.5px solid #67E8F9; box-shadow: 0 4px 14px rgba(6, 182, 212, 0.15); margin-bottom: 16px;">
                <div style="background: linear-gradient(100deg, #0F172A 0%, #0369A1 50%, #0284C7 100%); padding: 12px 20px; color: #FFFFFF; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="background: #F59E0B; color: #1E293B; font-size: 12px; font-weight: 800; padding: 3px 10px; border-radius: 12px;">📢 {event}</span>
                        <span style="font-size: 16px; font-weight: 700;">{headline}</span>
                    </div>
                    <span style="font-size: 12px; color: #E0F2FE;">有效時間：{effective} 至 {expires}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if sections:
            with st.expander(f"📋 查看 {event} 詳細章節與防範指南", expanded=True):
                sec_cols = st.columns(min(len(sections), 3))
                for i, sec in enumerate(sections):
                    target_col = sec_cols[i % len(sec_cols)]
                    target_col.markdown(f"""
                        <div class="clean-card" style="border-left: 3px solid #0284C7; padding: 10px 14px; margin-bottom: 10px;">
                            <div style="font-size: 13px; font-weight: 700; color: #0369A1; margin-bottom: 4px;">📌 {sec.get('title')}</div>
                            <div style="font-size: 12px; color: #334155; line-height: 1.6;">{sec.get('value')}</div>
                        </div>
                    """, unsafe_allow_html=True)
                st.caption(f"資料來源：{sender} ｜ 資料集：W-C0034-001 即時天氣訊息 (CAP-TWP 示警協定)")


def fetch_weather_alerts():
    """從 CWA W-C0033-002 取得天氣特報資料，回傳結構化的警報清單。"""
    import requests
    from dotenv import load_dotenv
    load_dotenv()
    key = os.environ.get("CWA_API_KEY", "")
    if not key or key == "YOUR_CWA_API_KEY_HERE":
        return []
    try:
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-002?Authorization={key}&format=JSON"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("records", {}).get("record", [])
    except Exception:
        pass
    return []


def _get_alert_severity_class(phenomena: str, significance: str) -> str:
    """根據特報種類與嚴重程度回傳 CSS 類別。"""
    sig_lower = (significance or "").strip()
    phen_lower = (phenomena or "").strip()
    # 紅色: 豪雨/大豪雨/超大豪雨/颱風
    if any(kw in phen_lower for kw in ["豪雨", "颱風", "海嘯"]):
        return "severity-red"
    # 橙色: 強風/低溫
    if any(kw in phen_lower for kw in ["強風", "低溫", "大雨"]):
        return "severity-orange"
    # 黃色: 濃霧/高溫
    if any(kw in phen_lower for kw in ["濃霧", "高溫", "雷雨"]):
        return "severity-yellow"
    return "severity-default"


def _get_alert_icon(phenomena: str) -> str:
    """根據特報種類回傳對應圖示。"""
    phen = (phenomena or "").strip()
    icon_map = {
        "豪雨": "🌧️", "大雨": "🌦️", "大豪雨": "⛈️", "超大豪雨": "🌊",
        "強風": "💨", "低溫": "🥶", "濃霧": "🌫️", "高溫": "🌡️",
        "颱風": "🌀", "雷雨": "⚡", "海嘯": "🌊",
    }
    for kw, icon in icon_map.items():
        if kw in phen:
            return icon
    return "⚠️"


def render_cwa_alert_bulletin(alerts: list):
    """以中央氣象署官方電子報/公告格式呈現氣象特報監測。"""
    now_str = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")

    if not alerts:
        st.markdown(f"""
            <div class="cwa-no-alert">
                <div class="icon">✅</div>
                <div class="msg">目前無生效中之天氣特報</div>
                <div class="sub">資料來源：交通部中央氣象署 (CWA) ｜ 查詢時間：{now_str}</div>
            </div>
        """, unsafe_allow_html=True)
        return

    # 依特報種類 (phenomena) 分組，合併影響區域
    from collections import OrderedDict
    grouped = OrderedDict()
    for alert in alerts:
        phen = alert.get("phenomena", "未知特報")
        if phen not in grouped:
            grouped[phen] = {
                "phenomena": phen,
                "significance": alert.get("significance", ""),
                "contentText": alert.get("contentText", ""),
                "issueTime": alert.get("issueTime", ""),
                "startTime": alert.get("startTime", ""),
                "endTime": alert.get("endTime", ""),
                "locations": [],
                "datasetDescription": alert.get("datasetDescription", ""),
                "language": alert.get("language", ""),
            }
        loc_name = alert.get("locationName", "")
        if loc_name and loc_name not in grouped[phen]["locations"]:
            grouped[phen]["locations"].append(loc_name)
        # 使用最新的 contentText (較長者優先)
        current_text = alert.get("contentText", "")
        if len(current_text) > len(grouped[phen]["contentText"]):
            grouped[phen]["contentText"] = current_text
            grouped[phen]["issueTime"] = alert.get("issueTime", grouped[phen]["issueTime"])
            grouped[phen]["startTime"] = alert.get("startTime", grouped[phen]["startTime"])
            grouped[phen]["endTime"] = alert.get("endTime", grouped[phen]["endTime"])

    # 總標題列
    alert_count = len(grouped)
    st.markdown(f"""
        <div class="cwa-alert-title-bar">
            <span class="cwa-icon">⚠️</span>
            <span>天氣警特報 — 氣象特報監測</span>
            <span style="margin-left: auto; font-size: 12px; font-weight: 400; opacity: 0.8;">
                目前生效中 {alert_count} 類特報 ｜ {now_str}
            </span>
        </div>
    """, unsafe_allow_html=True)

    # 渲染各特報公告
    bulletin_cards = []
    for phen_name, info in grouped.items():
        severity_cls = _get_alert_severity_class(phen_name, info["significance"])
        icon = _get_alert_icon(phen_name)

        # 影響區域標籤
        area_tags = "".join(
            f'<span class="cwa-area-tag">{loc}</span>' for loc in info["locations"]
        ) if info["locations"] else '<span style="color: #999;">全區域</span>'

        # 格式化時間
        issue_time = info.get("issueTime", "—")
        start_time = info.get("startTime", "—")
        end_time = info.get("endTime", "—")
        validity = f"{start_time}　至　{end_time}" if start_time and end_time else "—"

        # 內文
        content_text = info.get("contentText", "").strip()
        if not content_text:
            content_text = "詳細內容請參閱中央氣象署官方公告。"

        card_html = f"""
        <div class="cwa-alert-bulletin">
            <div class="cwa-alert-type-header">
                <span class="cwa-alert-type-badge {severity_cls}">
                    {icon} {phen_name}
                </span>
                <span class="cwa-alert-significance">{info.get('significance', '')}</span>
            </div>
            <div class="cwa-alert-content">
                <div class="cwa-alert-datetime">
                    <strong>發佈時間：</strong>{issue_time}
                </div>
                <table class="cwa-alert-meta-table">
                    <tr>
                        <td class="label-cell">特報種類</td>
                        <td class="value-cell">{phen_name}</td>
                    </tr>
                    <tr>
                        <td class="label-cell">有效期間</td>
                        <td class="value-cell">{validity}</td>
                    </tr>
                    <tr>
                        <td class="label-cell">影響區域</td>
                        <td class="value-cell">{area_tags}</td>
                    </tr>
                </table>
                <div class="cwa-alert-body">
                    {content_text}
                </div>
            </div>
            <div class="cwa-source-footer">
                資料來源：交通部中央氣象署 ｜ 資料集：W-C0033-002 天氣特報
            </div>
        </div>
        """
        bulletin_cards.append(card_html)

    st.markdown("".join(bulletin_cards), unsafe_allow_html=True)

def get_clean_temp_color(temp: float) -> str:
    """明亮清晰的溫度色階。"""
    if temp < 18.0:
        return "#3B82F6"  # 藍色 (涼冷)
    elif temp < 23.0:
        return "#10B981"  # 綠色 (舒適)
    elif temp < 28.0:
        return "#F59E0B"  # 橙黃 (溫暖)
    else:
        return "#EF4444"  # 紅色 (炎熱)


def get_rain_color(rainfall: float) -> str:
    """降雨量色階 (中央氣象署標準)。"""
    if rainfall is None or rainfall == 0:
        return "#38BDF8"  # 無雨/晴 天藍
    elif rainfall < 10.0:
        return "#0284C7"  # 小雨 湛藍
    elif rainfall < 40.0:
        return "#1D4ED8"  # 中雨 深藍
    elif rainfall < 80.0:
        return "#7E22CE"  # 大雨 藍紫
    else:
        return "#C026D3"  # 豪雨 紫紅


def get_wind_color(speed: float) -> str:
    """風速色階 (蒲福風級對應)。"""
    if speed is None:
        return "#64748B"
    if speed < 3.4:
        return "#0D9488"  # 0-2級 靜/微風
    elif speed < 10.8:
        return "#2563EB"  # 3-5級 和/清風
    elif speed < 17.2:
        return "#D97706"  # 6-7級 強風
    elif speed < 24.5:
        return "#DC2626"  # 8-9級 疾/大風
    else:
        return "#7C3AED"  # 10+級 暴風


def get_uv_color(uvi: float) -> str:
    """WHO / CWA 紫外線指數 5 級色標。"""
    if uvi is None:
        return "#64748B"
    if uvi < 3.0:
        return "#16A34A"  # 0-2 低量 綠
    elif uvi < 6.0:
        return "#CA8A04"  # 3-5 中量 黃
    elif uvi < 8.0:
        return "#EA580C"  # 6-7 高量 橙
    elif uvi < 11.0:
        return "#DC2626"  # 8-10 過量 紅
    else:
        return "#9333EA"  # 11+ 危險 紫


def get_beaufort_scale(speed: float) -> int:
    """根據公尺/秒風速換算蒲福風級。"""
    if speed is None:
        return 0
    if speed < 0.3: return 0
    elif speed < 1.6: return 1
    elif speed < 3.4: return 2
    elif speed < 5.5: return 3
    elif speed < 8.0: return 4
    elif speed < 10.8: return 5
    elif speed < 13.9: return 6
    elif speed < 17.2: return 7
    elif speed < 20.8: return 8
    elif speed < 24.5: return 9
    elif speed < 28.5: return 10
    elif speed < 32.7: return 11
    else: return 12


def get_uv_advice(uvi: float) -> str:
    """中央氣象署紫外線防護指南。"""
    if uvi is None or uvi < 3.0:
        return "正常戶外活動，外出配戴太陽眼鏡保護眼睛。"
    elif uvi < 6.0:
        return "塗抹防曬乳、戴遮陽帽或打傘，盡量尋找陰涼處。"
    elif uvi < 8.0:
        return "曝曬 20 分鐘即有曬傷風險，應著長袖衣物並備遮陽防護。"
    elif uvi < 11.0:
        return "曝曬 15 分鐘有曬傷危險，盡量避免 10-14 點在烈日下曝曬。"
    else:
        return "曝曬 10 分鐘即有灼傷風險，應儘量留在室內，外出需全副武裝防曬。"


def render_clean_map(map_data: pd.DataFrame, is_county: bool = True,
                     show_rain: bool = True, show_wind: bool = True,
                     show_uv: bool = True, show_temp: bool = False):
    """繪製具有獨立切換圖層之 Google Maps 風格氣象地圖 (雨量 / 風況 / 紫外線 / 氣溫)。"""
    coords_dict = COUNTY_COORDINATES if is_county else REGION_COORDINATES

    m = folium.Map(
        location=[23.75, 120.95],
        zoom_start=7 if not is_county else 7.5,
        tiles=None,
        control_scale=True,
        zoom_control=True,
    )

    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google Maps",
        name="Google 地圖底圖",
        max_zoom=20,
    ).add_to(m)

    Fullscreen(
        position="topright",
        title="全螢幕",
        title_cancel="退出全螢幕",
    ).add_to(m)

    # 建立 4 個獨立可切換之 FeatureGroup 圖層
    fg_rain = folium.FeatureGroup(name="🌧️ 降雨量 (Rainfall)", show=show_rain)
    fg_wind = folium.FeatureGroup(name="💨 風向與風速 (Wind)", show=show_wind)
    fg_uv = folium.FeatureGroup(name="☀️ 紫外線指數 (UV Index)", show=show_uv)
    fg_temp = folium.FeatureGroup(name="🌡️ 氣溫 (Temperature)", show=show_temp)

    # 檢查有多少圖層同時開啟，以計算適度座標偏移避免標記互相重疊
    active_count = sum([show_rain, show_wind, show_uv, show_temp])

    for _, row in map_data.iterrows():
        name = row["regionName"]
        base_coords = coords_dict.get(name)
        if not base_coords:
            continue

        lat, lon = base_coords
        min_t = row.get("minT", 22.0)
        max_t = row.get("maxT", 28.0)
        avg_t = row.get("avgT", 25.0)
        date_str = row.get("dataDate", "")

        rainfall = float(row.get("rainfall", 0.0))
        wind_speed = float(row.get("windSpeed", 2.0))
        wind_dir = float(row.get("windDirection", 90.0))
        wind_compass = str(row.get("windCompass", "偏東風"))
        uvi = float(row.get("uvIndex", 5.0))
        uv_level = str(row.get("uvLevel", "中量級"))

        # 座標偏移計算 (當多圖層同時啟用時側向展開)
        if active_count > 1:
            rain_coords = (lat + 0.04, lon - 0.06)
            wind_coords = (lat + 0.04, lon + 0.06)
            uv_coords = (lat - 0.04, lon - 0.05)
            temp_coords = (lat - 0.04, lon + 0.05)
        else:
            rain_coords = wind_coords = uv_coords = temp_coords = (lat, lon)

        # ── 1. 降雨量圖層標記 (Rainfall Marker) ──
        rain_color = get_rain_color(rainfall)
        rain_desc = "無顯著降雨" if rainfall == 0 else ("微量降雨" if rainfall < 10 else ("中度降雨" if rainfall < 40 else "大雨/豪雨"))
        rain_icon_html = f"""
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: #FFFFFF;
            border: 2px solid {rain_color};
            border-radius: 18px;
            padding: 3px 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.22);
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            cursor: pointer;
        ">
            <span style="font-size: 13px;">💧</span>
            <span style="color: {rain_color};">{rainfall:.1f} mm</span>
            <span style="color: #64748B; font-weight: 500; font-size: 10px;">{name}</span>
        </div>
        """
        rain_popup_html = f"""
        <div style="font-family: 'Noto Sans TC', sans-serif; min-width: 200px; padding: 4px;">
            <div style="font-size: 15px; font-weight: 700; color: #0F172A; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px; margin-bottom: 8px;">
                💧 {name} · 即時雨量觀測
            </div>
            <div style="display: flex; align-items: baseline; gap: 4px; margin-bottom: 6px;">
                <span style="font-size: 28px; font-weight: 800; color: {rain_color};">{rainfall:.1f}</span>
                <span style="font-size: 14px; color: #64748B;">毫米 (mm)</span>
            </div>
            <div style="font-size: 12px; color: #475569; margin-bottom: 4px;">
                <b>降雨狀態</b>：<span style="color: {rain_color}; font-weight: 700;">{rain_desc}</span>
            </div>
            <div style="font-size: 11px; color: #94A3B8; margin-top: 6px; border-top: 1px dashed #E2E8F0; padding-top: 4px;">
                資料來源：中央氣象署 CWA 測站即時觀測
            </div>
        </div>
        """
        folium.Marker(
            location=rain_coords,
            icon=folium.DivIcon(html=rain_icon_html, icon_size=(110, 32), icon_anchor=(55, 16)),
            popup=folium.Popup(rain_popup_html, max_width=280),
            tooltip=f"{name} 雨量: {rainfall:.1f} mm ({rain_desc})",
        ).add_to(fg_rain)

        # ── 2. 風向風速圖層標記 (Wind Marker) ──
        wind_color = get_wind_color(wind_speed)
        beaufort = get_beaufort_scale(wind_speed)
        wind_icon_html = f"""
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: #FFFFFF;
            border: 2px solid {wind_color};
            border-radius: 18px;
            padding: 3px 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.22);
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            cursor: pointer;
        ">
            <span style="
                display: inline-block;
                transform: rotate({wind_dir}deg);
                color: {wind_color};
                font-size: 13px;
                line-height: 1;
                font-weight: 900;
            ">➤</span>
            <span style="color: {wind_color};">{wind_speed:.1f} m/s</span>
            <span style="color: #64748B; font-weight: 500; font-size: 10px;">{wind_compass}</span>
        </div>
        """
        wind_popup_html = f"""
        <div style="font-family: 'Noto Sans TC', sans-serif; min-width: 220px; padding: 4px;">
            <div style="font-size: 15px; font-weight: 700; color: #0F172A; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px; margin-bottom: 8px;">
                💨 {name} · 風向與風速觀測
            </div>
            <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px;">
                <span style="font-size: 28px; font-weight: 800; color: {wind_color};">{wind_speed:.1f}</span>
                <span style="font-size: 14px; color: #64748B;">m/s</span>
                <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #F1F5F9; color: #334155; font-weight: 600;">蒲福 {beaufort} 級</span>
            </div>
            <div style="font-size: 12px; color: #475569; margin-bottom: 4px;">
                <b>風向方位</b>：{wind_compass} ({wind_dir:.0f}°)
            </div>
            <div style="font-size: 11px; color: #94A3B8; margin-top: 6px; border-top: 1px dashed #E2E8F0; padding-top: 4px;">
                資料來源：中央氣象署 CWA 測站即時觀測
            </div>
        </div>
        """
        folium.Marker(
            location=wind_coords,
            icon=folium.DivIcon(html=wind_icon_html, icon_size=(130, 32), icon_anchor=(65, 16)),
            popup=folium.Popup(wind_popup_html, max_width=280),
            tooltip=f"{name} 風況: {wind_compass} {wind_speed:.1f} m/s (蒲福 {beaufort} 級)",
        ).add_to(fg_wind)

        # ── 3. 紫外線指數圖層標記 (UV Index Marker) ──
        uv_color = get_uv_color(uvi)
        uv_advice = get_uv_advice(uvi)
        uv_icon_html = f"""
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: #FFFFFF;
            border: 2px solid {uv_color};
            border-radius: 18px;
            padding: 3px 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.22);
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            cursor: pointer;
        ">
            <span style="font-size: 13px;">☀️</span>
            <span style="color: {uv_color};">UVI {uvi:.1f}</span>
            <span style="
                background: {uv_color};
                color: #FFFFFF;
                border-radius: 8px;
                padding: 1px 5px;
                font-size: 9px;
                font-weight: 700;
            ">{uv_level}</span>
        </div>
        """
        uv_popup_html = f"""
        <div style="font-family: 'Noto Sans TC', sans-serif; min-width: 220px; padding: 4px;">
            <div style="font-size: 15px; font-weight: 700; color: #0F172A; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px; margin-bottom: 8px;">
                ☀️ {name} · 紫外線指數 (UVI)
            </div>
            <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px;">
                <span style="font-size: 28px; font-weight: 800; color: {uv_color};">{uvi:.1f}</span>
                <span style="
                    background: {uv_color};
                    color: #FFFFFF;
                    border-radius: 12px;
                    padding: 2px 8px;
                    font-size: 12px;
                    font-weight: 700;
                ">{uv_level}</span>
            </div>
            <div style="font-size: 12px; color: #475569; margin-bottom: 6px; line-height: 1.5;">
                <b>防曬指南</b>：{uv_advice}
            </div>
            <div style="font-size: 11px; color: #94A3B8; margin-top: 6px; border-top: 1px dashed #E2E8F0; padding-top: 4px;">
                資料來源：中央氣象署 CWA 紫外線監測與預報 (WHO標準)
            </div>
        </div>
        """
        folium.Marker(
            location=uv_coords,
            icon=folium.DivIcon(html=uv_icon_html, icon_size=(120, 32), icon_anchor=(60, 16)),
            popup=folium.Popup(uv_popup_html, max_width=280),
            tooltip=f"{name} 紫外線: UVI {uvi:.1f} ({uv_level})",
        ).add_to(fg_uv)

        # ── 4. 氣溫圖層標記 (Temperature Marker) ──
        temp_color = get_clean_temp_color(avg_t)
        temp_icon_html = f"""
        <div style="
            width: 150px;
            height: 48px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
            cursor: pointer;
        ">
            <div style="
                background: #FFFFFF;
                color: #3C4043;
                font-family: 'Google Sans', Roboto, Arial, sans-serif;
                font-weight: 500;
                font-size: 12px;
                padding: 4px 10px;
                border-radius: 16px;
                white-space: nowrap;
                box-shadow: 0 1px 4px rgba(0,0,0,0.3);
                border: 1px solid #DADCE0;
                line-height: 1.3;
            ">
                <span style="font-weight: 700; color: {temp_color};">{avg_t}°</span>
                <span style="color: #5F6368; font-size: 11px; margin-left: 2px;">{name}</span>
            </div>
            <div style="
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid #FFFFFF;
            "></div>
            <div style="
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: {temp_color};
                border: 2px solid #FFFFFF;
                box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            "></div>
        </div>
        """
        temp_popup_html = f"""
        <div style="font-family: 'Google Sans', Roboto, Arial, sans-serif; min-width: 220px; max-width: 280px;">
            <div style="padding: 12px 16px 8px 16px; border-bottom: 1px solid #E8EAED;">
                <div style="font-size: 16px; font-weight: 500; color: #202124; margin: 0 0 2px 0;">{name}</div>
                <div style="font-size: 12px; color: #70757A; margin: 0;">氣象預報 · {date_str}</div>
            </div>
            <div style="padding: 12px 16px;">
                <div style="display: flex; align-items: baseline; margin-bottom: 10px;">
                    <span style="font-size: 36px; font-weight: 400; color: #202124; line-height: 1;">{avg_t}</span>
                    <span style="font-size: 18px; color: #70757A; margin-left: 2px;">°C</span>
                    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: {temp_color}; margin-left: 8px;"></span>
                </div>
                <div style="display: flex; gap: 16px; font-size: 13px; color: #3C4043;">
                    <div><span style="color: #70757A;">低溫</span><br><span style="font-weight: 500; color: #1A73E8;">{min_t}°C</span></div>
                    <div><span style="color: #70757A;">高溫</span><br><span style="font-weight: 500; color: #EA4335;">{max_t}°C</span></div>
                    <div><span style="color: #70757A;">溫差</span><br><span style="font-weight: 500; color: #3C4043;">{max_t - min_t:.1f}°C</span></div>
                </div>
            </div>
        </div>
        """
        folium.Marker(
            location=temp_coords,
            icon=folium.DivIcon(html=temp_icon_html, icon_size=(150, 48), icon_anchor=(75, 48)),
            popup=folium.Popup(temp_popup_html, max_width=300),
            tooltip=f"{name}: {avg_t}°C (低溫 {min_t}°C / 高溫 {max_t}°C)",
        ).add_to(fg_temp)

    # 將 4 個獨立圖層加入地圖
    fg_rain.add_to(m)
    fg_wind.add_to(m)
    fg_uv.add_to(m)
    fg_temp.add_to(m)

    # 啟用 Leaflet 原生圖層控制面板
    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    st_folium(m, width="100%", height=580, returned_objects=[])


def main():
    apply_custom_css()

    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 頂部清爽 Banner
    st.markdown(f"""
        <div class="weather-banner">
            <div>
                <h1 class="weather-banner-title">🌤️ Taiwan Weather Forecast</h1>
                <p style="margin: 0; opacity: 0.95; font-size: 14px;">
                    交通部中央氣象署 (CWA) 臺灣全台 22 縣市與分區 · 未來 14 天氣象預報
                </p>
            </div>
            <div style="text-align: right;">
                <span class="status-pill">
                    <span class="green-dot"></span>
                    CWA API ONLINE
                </span>
                <p style="margin: 6px 0 0 0; opacity: 0.85; font-size: 12px;">資料時間: {now_time}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    nowcasts = fetch_nowcast_messages()
    render_cwa_nowcast_bulletin(nowcasts)

    alerts = fetch_weather_alerts()
    render_cwa_alert_bulletin(alerts)

    if not os.path.exists(DB_FILE):
        st.warning("⚠️ 尚未偵測到本地資料庫 `data.db`！")
        if st.button("🚀 立即建立資料庫 (執行管線)"):
            with st.spinner("正在執行資料管線..."):
                from fetch_weather import fetch_cwa_weather
                from parse_weather import parse_weather_json
                from database import insert_forecasts
                fetch_cwa_weather()
                records = parse_weather_json("raw_weather.json")
                insert_forecasts(records, DB_FILE)
            st.success("資料庫建置完成！")
            st.rerun()
        st.stop()

    # 側邊欄控制
    st.sidebar.markdown("### 🔍 預報篩選控制台")

    view_mode = st.sidebar.radio(
        "選擇檢視維度 (View Mode):",
        options=["全台 22 縣市 (細項觀測)", "六大地理分區 (整合預報)"],
        index=0
    )
    is_county_mode = "22 縣市" in view_mode
    target_type = "county" if is_county_mode else "region"

    available_locations = fetch_location_list(location_type=target_type)
    if not available_locations:
        available_locations = fetch_location_list()

    # 依地理分區排序 (北部 → 中部 → 南部 → 東部 → 離島)
    available_locations = sort_locations_by_region(available_locations, is_county=is_county_mode)

    default_idx = 0
    if is_county_mode and "臺北市" in available_locations:
        default_idx = available_locations.index("臺北市")
    elif not is_county_mode and "北部地區" in available_locations:
        default_idx = available_locations.index("北部地區")

    # 產生帶分區標頭的格式化顯示名稱
    order_dict = COUNTY_REGION_ORDER if is_county_mode else REGION_GROUP_ORDER
    labels = COUNTY_REGION_LABELS if is_county_mode else REGION_GROUP_LABELS
    display_options = []
    seen_groups = set()
    for loc in available_locations:
        group_id = order_dict.get(loc, (99, 99))[0]
        if group_id not in seen_groups:
            seen_groups.add(group_id)
            label = labels.get(group_id, "")
            if label:
                display_options.append(label)
        display_options.append(loc)

    # 側邊欄分區顯示標頭 (用 markdown 呈現)
    selected_location = st.sidebar.selectbox(
        f"選擇觀測地點 ({'縣市' if is_county_mode else '分區'}):",
        options=display_options,
        index=display_options.index(available_locations[default_idx]) if available_locations else 0,
    )

    # 若選到分隔標頭，自動導向該區第一個地點
    if selected_location.startswith("──"):
        group_label = selected_location
        # 找到該標頭後面的第一個實際地點
        idx = display_options.index(group_label)
        if idx + 1 < len(display_options):
            selected_location = display_options[idx + 1]

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔄 資料同步")
    if st.sidebar.button("同步氣象署最新資料"):
        with st.spinner("正在同步中央氣象署最新 14 天預報..."):
            from fetch_weather import fetch_cwa_weather
            from parse_weather import parse_weather_json
            from database import insert_forecasts
            fetch_cwa_weather()
            records = parse_weather_json("raw_weather.json")
            insert_forecasts(records, DB_FILE)
        st.sidebar.success("同步完成！")
        st.rerun()

    st.sidebar.info("""
    **資料來源**: 交通部中央氣象署 (CWA)
    **涵蓋範圍**: 全台 22 縣市 + 大分區
    **預報長度**: 未來 14 天 (兩週) 滾動預報
    """)

    # 主分頁
    tab1, tab2 = st.tabs(["🗺️ 全台氣象獨立多圖層地圖 (降雨 / 風況 / 紫外線)", "📈 14 天氣象走勢與詳細數據"])

    with tab1:
        st.markdown(f"### 📍 臺灣{'全台 22 縣市' if is_county_mode else '六大分區'}即時氣象圖層觀測")
        st.caption("✨ 資料來源：交通部中央氣象署 (CWA) 唯一官方資料來源 · 支援降雨量、風向風速、紫外線指數獨立開關與專屬圖例")

        # 獨立氣象圖層開關 (非單選，各圖層皆可獨立開啟/關閉)
        st.markdown("**🎛️ 獨立圖層開關控制：**")
        col_t1, col_t2, col_t3, col_t4 = st.columns(4)
        with col_t1:
            show_rain = st.checkbox("🌧️ 降雨量 (Rainfall)", value=True, key="layer_rain")
        with col_t2:
            show_wind = st.checkbox("💨 風向與風速 (Wind)", value=True, key="layer_wind")
        with col_t3:
            show_uv = st.checkbox("☀️ 紫外線指數 (UV Index)", value=True, key="layer_uv")
        with col_t4:
            show_temp = st.checkbox("🌡️ 氣溫 (Temperature)", value=False, key="layer_temp")

        map_df = fetch_map_data(location_type=target_type)

        if not map_df.empty:
            col_map, col_panel = st.columns([3.2, 1.2])

            with col_map:
                render_clean_map(map_df, is_county=is_county_mode,
                                 show_rain=show_rain, show_wind=show_wind,
                                 show_uv=show_uv, show_temp=show_temp)

            with col_panel:
                # 依當前開啟圖層動態呈現獨立圖例
                if show_rain:
                    st.markdown("""
                        <div class="clean-card">
                            <div style="font-size: 14px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                                🌧️ 降雨量圖例 (Rainfall)
                                <span class="legend-badge-unit">毫米 mm</span>
                            </div>
                            <div class="rain-bar-gradient"></div>
                            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748B; font-weight: 600;">
                                <span>無雨 0</span>
                                <span>微量 2</span>
                                <span>中雨 30</span>
                                <span>>80 豪雨</span>
                            </div>
                            <div style="font-size: 11px; color: #64748B; margin-top: 6px; line-height: 1.4;">
                                💧 <b>中央氣象署實測雨量</b>：水滴數值標記即時雨量，顏色深淺對應雨量強度。
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                if show_wind:
                    st.markdown("""
                        <div class="clean-card">
                            <div style="font-size: 14px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                                💨 風向風速圖例 (Wind)
                                <span class="legend-badge-unit">m/s · 蒲福</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #0284C7; font-weight: 600; margin: 4px 0;">
                                <span style="font-size: 16px;">➤</span>
                                <span>動態箭頭順應氣象風向角度轉向</span>
                            </div>
                            <div class="wind-bar-gradient"></div>
                            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748B; font-weight: 600;">
                                <span><3 靜風</span>
                                <span>8 和風</span>
                                <span>14 強風</span>
                                <span>>20 暴風</span>
                            </div>
                            <div style="font-size: 11px; color: #64748B; margin-top: 6px; line-height: 1.4;">
                                💨 <b>氣象署實測風況</b>：箭頭即時指向吹拂方位，色標符合蒲福風級。
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                if show_uv:
                    st.markdown("""
                        <div class="clean-card">
                            <div style="font-size: 14px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                                ☀️ 紫外線指數圖例 (UVI)
                                <span class="legend-badge-unit">WHO 標準</span>
                            </div>
                            <div class="uv-bar-gradient"></div>
                            <div style="display: flex; justify-content: space-between; font-size: 10px; font-weight: 700;">
                                <span style="color: #16A34A;">0-2 低</span>
                                <span style="color: #CA8A04;">3-5 中</span>
                                <span style="color: #EA580C;">6-7 高</span>
                                <span style="color: #DC2626;">8-10 過量</span>
                                <span style="color: #9333EA;">11+ 危險</span>
                            </div>
                            <div style="font-size: 11px; color: #64748B; margin-top: 6px; line-height: 1.4;">
                                ☀️ <b>防曬指南</b>：高量級 (6-7) 曝曬 20 分鐘即有曬傷風險；過量/危險級建議避免中午烈日。
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                if show_temp:
                    st.markdown("""
                        <div class="clean-card">
                            <div style="font-size: 14px; font-weight: 700; color: #1E293B; margin-bottom: 4px;">
                                🌡️ 氣溫色階圖例 (Temperature)
                                <span class="legend-badge-unit">攝氏度 °C</span>
                            </div>
                            <div class="temp-bar-gradient"></div>
                            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748B; font-weight: 600;">
                                <span><18°C (涼冷)</span>
                                <span>23°C (舒適)</span>
                                <span>>28°C (炎熱)</span>
                            </div>
                            <div style="font-size: 11px; color: #64748B; margin-top: 6px; line-height: 1.4;">
                                🌡️ <b>氣溫分布</b>：中央氣象署預報溫度色標。
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                if not (show_rain or show_wind or show_uv or show_temp):
                    st.info("💡 目前所有圖層皆已關閉，請開啟上方圖層開關以檢視氣象標記。")

                # 當前選定地點即時全項觀測卡片
                cur_loc_data = map_df[map_df["regionName"] == selected_location]
                if not cur_loc_data.empty:
                    row_c = cur_loc_data.iloc[0]
                    t_avg = row_c["avgT"]
                    t_color = get_clean_temp_color(t_avg)
                    rf = row_c["rainfall"]
                    rf_color = get_rain_color(rf)
                    ws = row_c["windSpeed"]
                    wd_c = row_c["windCompass"]
                    w_color = get_wind_color(ws)
                    uvi_v = row_c["uvIndex"]
                    uv_lvl = row_c["uvLevel"]
                    uv_c = get_uv_color(uvi_v)

                    st.markdown(f"""
                        <div class="clean-card" style="border-left: 4px solid {t_color};">
                            <div style="font-size: 12px; color: #64748B; font-weight: 600;">當前選定觀測點 (CWA)</div>
                            <div style="font-size: 20px; font-weight: 700; color: #0F172A; margin-top: 2px;">
                                {selected_location}
                            </div>
                            <div style="font-size: 30px; font-weight: 800; color: {t_color}; margin: 6px 0 10px 0;">
                                {t_avg} <span style="font-size: 16px; font-weight: 600; color: #64748B;">°C</span>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr; gap: 8px; font-size: 12px; border-top: 1px solid #E2E8F0; padding-top: 10px;">
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #64748B;">🌧️ 即時雨量:</span>
                                    <b style="color: {rf_color};">{rf:.1f} mm</b>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #64748B;">💨 風向風速:</span>
                                    <b style="color: {w_color};">{wd_c} {ws:.1f} m/s</b>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #64748B;">☀️ 紫外線:</span>
                                    <b style="color: {uv_c};">UVI {uvi_v:.1f} ({uv_lvl})</b>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: #64748B;">🌡️ 預報溫差:</span>
                                    <span style="color: #334155;">{row_c['minT']}°C ~ {row_c['maxT']}°C</span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    with tab2:
        st.markdown(f"### 📍 {selected_location} · 未來 14 天高低溫走勢與氣象指標")
        df_forecast = fetch_forecast_data(selected_location)

        if df_forecast.empty:
            st.info(f"查無 {selected_location} 之預報資料。")
        else:
            kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
            avg_all = df_forecast["AvgT"].mean()
            max_all = df_forecast["MaxT"].max()
            min_all = df_forecast["MinT"].min()
            temp_range = max_all - min_all

            try:
                from api.weather import get_uv_level_desc
                uvi_numeric = pd.to_numeric(df_forecast["UVI"], errors="coerce").dropna()
                avg_uvi = uvi_numeric.mean() if not uvi_numeric.empty else 5.0
                uv_desc = get_uv_level_desc(avg_uvi)
            except Exception:
                avg_uvi = 5.0
                uv_desc = "中量級"

            kpi1.metric("14天 平均氣溫", f"{avg_all:.1f} °C")
            kpi2.metric("14天 最高溫", f"{max_all:.1f} °C", delta=f"+{(max_all - avg_all):.1f}°C", delta_color="inverse")
            kpi3.metric("14天 最低溫", f"{min_all:.1f} °C", delta=f"-{(avg_all - min_all):.1f}°C")
            kpi4.metric("週期最大溫差", f"{temp_range:.1f} °C")
            kpi5.metric("平均紫外線 (UVI)", f"{avg_uvi:.1f}", delta=uv_desc)

            st.markdown("---")

            col_c, col_t = st.columns([3, 2])

            with col_c:
                st.markdown(f"#### 🌡️ {selected_location} 14 天雙曲線走勢圖")
                chart_data = df_forecast.set_index("Date")[["MaxT", "MinT"]]
                st.line_chart(
                    chart_data,
                    color=["#EF4444", "#3B82F6"],
                    use_container_width=True
                )

            with col_t:
                st.markdown("#### 📋 14 天每日預報清單")
                rename_dict = {
                    "Date": "預報日期",
                    "MinT": "最低溫 (°C)",
                    "MaxT": "最高溫 (°C)",
                    "AvgT": "平均溫 (°C)",
                    "WS": "風速 (級)",
                    "WD": "風向",
                    "UVI": "紫外線 (UVI)"
                }
                display_df = df_forecast.rename(columns=rename_dict)
                st.dataframe(
                    display_df,
                    hide_index=True,
                    use_container_width=True,
                    height=450
                )


if __name__ == "__main__":
    main()
