"""
app.py - HW10 Taiwan Weather Forecast (清爽現代明亮風格)
技術棧: Streamlit × SQLite (data.db) × Folium × 現代清晰卡片設計
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
        SELECT dataDate AS Date, minT AS MinT, maxT AS MaxT
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
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        query = f"""
        SELECT t.regionName, t.locationType, t.dataDate, t.minT, t.maxT
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
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


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


def render_clean_map(map_data: pd.DataFrame, is_county: bool = True):
    """繪製明亮乾淨的 CartoDB Positron 互動地圖。"""
    coords_dict = COUNTY_COORDINATES if is_county else REGION_COORDINATES
    
    # 使用清晰明亮的淺色底圖
    m = folium.Map(
        location=[23.75, 120.95],
        zoom_start=7 if not is_county else 7.5,
        tiles="CartoDB positron",
        control_scale=True
    )
    Fullscreen().add_to(m)

    for _, row in map_data.iterrows():
        name = row["regionName"]
        coords = coords_dict.get(name)
        if not coords:
            continue

        min_t = row["minT"]
        max_t = row["maxT"]
        avg_t = row["avgT"]
        date_str = row["dataDate"]
        color = get_clean_temp_color(avg_t)

        # 乾淨清晰的數值徽章標籤 (DivIcon)
        icon_html = f"""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transform: translate(-50%, -50%);
        ">
            <div style="
                background: {color};
                color: #FFFFFF;
                font-weight: 700;
                font-size: 11px;
                padding: 3px 8px;
                border-radius: 12px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.25);
                border: 2px solid #FFFFFF;
                white-space: nowrap;
            ">
                {avg_t}°
            </div>
            <div style="
                color: #1E293B;
                font-size: 11px;
                font-weight: 600;
                margin-top: 2px;
                white-space: nowrap;
                background: rgba(255,255,255,0.85);
                padding: 1px 4px;
                border-radius: 4px;
                border: 1px solid #CBD5E1;
            ">
                {name}
            </div>
        </div>
        """

        popup_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 10px; min-width: 160px;">
            <h4 style="margin: 0 0 4px 0; color: #1E293B; font-size: 15px;">📍 {name}</h4>
            <p style="margin: 0 0 8px 0; font-size: 12px; color: #64748B;">日期: {date_str}</p>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px;">
                <p style="margin: 2px 0; font-size: 13px;">平均溫: <b style="color:{color}; font-size: 15px;">{avg_t} °C</b></p>
                <p style="margin: 2px 0; font-size: 12px; color: #2563EB;">最低溫: <b>{min_t} °C</b></p>
                <p style="margin: 2px 0; font-size: 12px; color: #DC2626;">最高溫: <b>{max_t} °C</b></p>
            </div>
        </div>
        """

        folium.Marker(
            location=coords,
            icon=folium.DivIcon(html=icon_html),
            popup=folium.Popup(popup_html, max_width=240),
            tooltip=f"{name}: {avg_t}°C (低溫 {min_t}°C / 高溫 {max_t}°C)",
        ).add_to(m)

    st_folium(m, width="100%", height=560, returned_objects=[])


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

    default_idx = 0
    if is_county_mode and "臺北市" in available_locations:
        default_idx = available_locations.index("臺北市")
    elif not is_county_mode and "中部地區" in available_locations:
        default_idx = available_locations.index("中部地區")

    selected_location = st.sidebar.selectbox(
        f"選擇觀測地點 ({'縣市' if is_county_mode else '分區'}):",
        options=available_locations,
        index=default_idx
    )

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
    tab1, tab2 = st.tabs(["🗺️ 全台氣溫地圖視覺化", "📈 14 天氣溫走勢與詳細數據"])

    with tab1:
        st.markdown(f"### 📍 臺灣{'全台 22 縣市' if is_county_mode else '六大分區'}即時氣溫分布圖")
        map_df = fetch_map_data(location_type=target_type)

        if not map_df.empty:
            col_map, col_panel = st.columns([3.2, 1.2])

            with col_map:
                render_clean_map(map_df, is_county=is_county_mode)

            with col_panel:
                # 清爽圖例卡片
                st.markdown("""
                    <div class="clean-card">
                        <div style="font-size: 14px; font-weight: 700; color: #1E293B; margin-bottom: 8px;">
                            🌡️ 氣溫色階圖例
                        </div>
                        <div class="temp-bar-gradient"></div>
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748B; font-weight: 600;">
                            <span><18°C (涼冷)</span>
                            <span>23°C (舒適)</span>
                            <span>>28°C (炎熱)</span>
                        </div>
                        <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 14px 0 10px 0;">
                        <div style="font-size: 12px; color: #64748B; line-height: 1.6;">
                            💡 <b>操作說明</b>：<br>
                            地圖標記顯示各地氣溫數值，點擊任一標記可查看最高溫與最低溫資訊。
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                cur_loc_df = fetch_forecast_data(selected_location)
                if not cur_loc_df.empty:
                    today_row = cur_loc_df.iloc[0]
                    t_avg = today_row["AvgT"]
                    t_color = get_clean_temp_color(t_avg)
                    st.markdown(f"""
                        <div class="clean-card" style="border-left: 4px solid {t_color};">
                            <div style="font-size: 12px; color: #64748B; font-weight: 600;">當前選定觀測點</div>
                            <div style="font-size: 20px; font-weight: 700; color: #0F172A; margin-top: 2px;">
                                {selected_location}
                            </div>
                            <div style="font-size: 32px; font-weight: 800; color: {t_color}; margin: 8px 0;">
                                {t_avg} <span style="font-size: 18px; font-weight: 600; color: #64748B;">°C</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #334155;">
                                <span>最低溫: <b style="color: #2563EB;">{today_row['MinT']}°C</b></span>
                                <span>最高溫: <b style="color: #DC2626;">{today_row['MaxT']}°C</b></span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    with tab2:
        st.markdown(f"### 📍 {selected_location} · 未來 14 天高低溫走勢")
        df_forecast = fetch_forecast_data(selected_location)

        if df_forecast.empty:
            st.info(f"查無 {selected_location} 之預報資料。")
        else:
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            avg_all = df_forecast["AvgT"].mean()
            max_all = df_forecast["MaxT"].max()
            min_all = df_forecast["MinT"].min()
            temp_range = max_all - min_all

            kpi1.metric("14天 平均氣溫", f"{avg_all:.1f} °C")
            kpi2.metric("14天 最高溫", f"{max_all:.1f} °C", delta=f"+{(max_all - avg_all):.1f}°C", delta_color="inverse")
            kpi3.metric("14天 最低溫", f"{min_all:.1f} °C", delta=f"-{(avg_all - min_all):.1f}°C")
            kpi4.metric("週期最大溫差", f"{temp_range:.1f} °C")

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
                display_df = df_forecast.rename(columns={
                    "Date": "預報日期",
                    "MinT": "最低溫 (°C)",
                    "MaxT": "最高溫 (°C)",
                    "AvgT": "平均溫 (°C)"
                })
                st.dataframe(
                    display_df,
                    hide_index=True,
                    use_container_width=True,
                    height=450
                )


if __name__ == "__main__":
    main()
