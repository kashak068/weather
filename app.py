"""
app.py - HW10 Taiwan Weather Forecast (類 Windy / 暗色玻璃擬態風格)
視覺設計參考: https://taiwan-weather-map.vercel.app/
技術棧: Streamlit × SQLite (data.db) × Folium × 現代暗黑玻璃擬態設計
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
    page_title="台灣即時與 14 天氣象視覺化地圖",
    page_icon="🌪️",
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
    """注入類 Windy 風格的暗黑毛玻璃設計系統 CSS。"""
    st.markdown("""
        <style>
        /* 全域字體與背景 */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+TC:wght@300;400;500;700;900&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .stApp {
            background-color: #030712;
            color: #F3F4F6;
        }

        /* 側邊欄暗黑美化 */
        section[data-testid="stSidebar"] {
            background-color: #0B0F19 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        /* 玻璃擬態卡片容器 */
        .glass-card {
            background: rgba(17, 24, 39, 0.7);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
            margin-bottom: 18px;
        }

        /* 頂部 Header Banner */
        .windy-header {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 58, 138, 0.5) 50%, rgba(13, 148, 136, 0.3) 100%);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 0 35px rgba(14, 165, 233, 0.15);
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .windy-title {
            font-size: 26px;
            font-weight: 800;
            background: linear-gradient(to right, #38BDF8, #818CF8, #34D399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0 0 6px 0;
            letter-spacing: -0.5px;
        }

        .badge-online {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 9999px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: #10B981;
            border-radius: 50%;
            box-shadow: 0 0 10px #10B981;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        /* 溫標色彩漸層長條 */
        .color-scale-bar {
            height: 10px;
            width: 100%;
            border-radius: 9999px;
            background: linear-gradient(to right, #2c7bb6, #5aa2cf, #abd9e9, #7fcdbb, #d9ef8b, #fee08b, #fdae61, #f46d43, #d73027);
            margin: 8px 0 4px 0;
            box-shadow: 0 0 15px rgba(253, 174, 97, 0.3);
        }

        /* KPI 指標卡片美化 */
        [data-testid="stMetric"] {
            background: rgba(17, 24, 39, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 14px !important;
            padding: 16px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 28px !important;
            font-weight: 700 !important;
            color: #F8FAFC !important;
        }

        /* 按鈕美化 */
        .stButton>button {
            background: linear-gradient(135deg, #0284C7, #0369A1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.2s ease;
            box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3);
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #0369A1, #075985);
            border-color: #38BDF8;
            box-shadow: 0 6px 20px rgba(56, 189, 248, 0.4);
            transform: translateY(-1px);
        }

        /* Tab 選單樣式 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(17, 24, 39, 0.8);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .stTabs [data-baseweb="tab"] {
            height: 42px;
            border-radius: 8px;
            color: #94A3B8;
            font-weight: 600;
            padding: 0 20px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0284C7 !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);
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


def get_windy_temp_color(temp: float) -> str:
    """依 Windy 精確多階色彩光譜回傳顏色 HEX。"""
    if temp < 15.0:
        return "#2C7BB6"  # 寒冷深藍
    elif temp < 18.0:
        return "#5AA2CF"  # 偏冷淺藍
    elif temp < 21.0:
        return "#ABD9E9"  # 涼爽青藍
    elif temp < 24.0:
        return "#7FCDBB"  # 舒適嫩綠
    elif temp < 26.0:
        return "#D9EF8B"  # 溫和黃綠
    elif temp < 28.0:
        return "#FEE08B"  # 暖色淡黃
    elif temp < 30.0:
        return "#FDAE61"  # 偏熱亮橙
    elif temp < 32.0:
        return "#F46D43"  # 炎熱橙紅
    else:
        return "#D73027"  # 酷熱鮮紅


def render_windy_map(map_data: pd.DataFrame, is_county: bool = True):
    """繪製類 Windy 風格的高質感 Dark Matter 地圖與數值 Badge 標籤。"""
    coords_dict = COUNTY_COORDINATES if is_county else REGION_COORDINATES
    
    # 使用暗黑風格底圖
    m = folium.Map(
        location=[23.75, 120.95],
        zoom_start=7 if not is_county else 7.5,
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://carto.com/">CARTO</a> | Data &copy; CWA',
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
        color = get_windy_temp_color(avg_t)

        # 類 Windy 風格數值發光徽章標籤 (DivIcon)
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
                color: #0F172A;
                font-weight: 800;
                font-size: 11px;
                padding: 2px 7px;
                border-radius: 12px;
                box-shadow: 0 0 12px {color}CC, 0 2px 6px rgba(0,0,0,0.6);
                border: 1.5px solid rgba(255,255,255,0.85);
                white-space: nowrap;
            ">
                {avg_t}°
            </div>
            <div style="
                color: #F1F5F9;
                font-size: 10px;
                font-weight: 600;
                text-shadow: 0 1px 3px #000, 0 0 6px #000;
                margin-top: 2px;
                white-space: nowrap;
            ">
                {name}
            </div>
        </div>
        """

        popup_html = f"""
        <div style="
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            background: #0F172A;
            color: #F8FAFC;
            padding: 12px;
            border-radius: 12px;
            min-width: 170px;
            border: 1px solid rgba(255,255,255,0.15);
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        ">
            <div style="font-size: 15px; font-weight: 700; color: #38BDF8; margin-bottom: 4px;">
                📍 {name}
            </div>
            <div style="font-size: 11px; color: #94A3B8; margin-bottom: 8px;">
                預報日期: {date_str}
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 8px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 13px; margin-bottom: 4px;">
                    平均氣溫: <b style="color:{color}; font-size:15px;">{avg_t} °C</b>
                </div>
                <div style="font-size: 12px; color: #38BDF8;">
                    最低溫 (Min): <b>{min_t} °C</b>
                </div>
                <div style="font-size: 12px; color: #F87171;">
                    最高溫 (Max): <b>{max_t} °C</b>
                </div>
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

    # 頂部視覺 Banner
    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(f"""
        <div class="windy-header">
            <div>
                <h1 class="windy-title">🌪️ Taiwan Weather Map & Forecast</h1>
                <p style="margin: 0; color: #94A3B8; font-size: 14px;">
                    中央氣象署開放資料即時視覺化 · 類 Windy 暗色擬態互動儀表板
                </p>
            </div>
            <div style="text-align: right;">
                <span class="badge-online">
                    <span class="pulse-dot"></span>
                    CWA API ONLINE
                </span>
                <p style="margin: 6px 0 0 0; color: #64748B; font-size: 12px;">最後更新: {now_time}</p>
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

    # 側邊欄配置
    st.sidebar.markdown("""
        <div style="padding: 10px 0 15px 0;">
            <div style="font-size: 12px; font-weight: 700; color: #38BDF8; letter-spacing: 1px; text-transform: uppercase;">控制面板 CONTROLS</div>
        </div>
    """, unsafe_allow_html=True)

    view_mode = st.sidebar.radio(
        "選擇檢視維度 (Layer Mode):",
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
    st.sidebar.markdown("<div style='font-size: 12px; font-weight: 700; color: #38BDF8;'>同步與圖層</div>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 同步氣象署最新資料"):
        with st.spinner("正在同步中央氣象署最新預報..."):
            from fetch_weather import fetch_cwa_weather
            from parse_weather import parse_weather_json
            from database import insert_forecasts
            fetch_cwa_weather()
            records = parse_weather_json("raw_weather.json")
            insert_forecasts(records, DB_FILE)
        st.sidebar.success("同步完成！")
        st.rerun()

    st.sidebar.markdown("""
        <div style="margin-top: 20px; padding: 14px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;">
            <div style="font-size: 11px; color: #64748B; font-weight: 600;">資料來源</div>
            <div style="font-size: 13px; color: #E2E8F0; font-weight: 600; margin-top: 2px;">交通部中央氣象署 (CWA)</div>
            <div style="font-size: 11px; color: #64748B; margin-top: 6px;">預報長度: <b>未來 14 天滾動預報</b></div>
        </div>
    """, unsafe_allow_html=True)

    # 主分頁
    tab1, tab2 = st.tabs(["🗺️ 類 Windy 氣象地圖視覺化", "📈 14 天氣溫走勢與詳細數據"])

    with tab1:
        st.markdown(f"### 📍 臺灣{'全台 22 縣市' if is_county_mode else '六大分區'}即時氣溫分布圖")
        map_df = fetch_map_data(location_type=target_type)

        if not map_df.empty:
            col_map, col_panel = st.columns([3.2, 1.2])

            with col_map:
                render_windy_map(map_df, is_county=is_county_mode)

            with col_panel:
                # 類 Windy 氣溫色階圖例卡片
                st.markdown("""
                    <div class="glass-card">
                        <div style="font-size: 13px; font-weight: 700; color: #F1F5F9; margin-bottom: 8px;">
                            🌡️ 氣溫色階標籤 (°C)
                        </div>
                        <div class="color-scale-bar"></div>
                        <div style="display: flex; justify-content: space-between; font-size: 10px; color: #94A3B8; font-weight: 600;">
                            <span>15°</span>
                            <span>18°</span>
                            <span>21°</span>
                            <span>24°</span>
                            <span>27°</span>
                            <span>30°</span>
                            <span>33°+</span>
                        </div>
                        <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.08); margin: 14px 0 10px 0;">
                        <div style="font-size: 11px; color: #94A3B8; line-height: 1.6;">
                            💡 <b>互動提示</b>：<br>
                            地圖標記直接呈現各地氣溫數值，點擊任一標記可展開高低溫詳細資訊卡。
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # 當前選中地點快速預覽卡
                cur_loc_df = fetch_forecast_data(selected_location)
                if not cur_loc_df.empty:
                    today_row = cur_loc_df.iloc[0]
                    t_avg = today_row["AvgT"]
                    t_color = get_windy_temp_color(t_avg)
                    st.markdown(f"""
                        <div class="glass-card" style="border-left: 4px solid {t_color};">
                            <div style="font-size: 12px; color: #94A3B8; text-transform: uppercase;">選定觀測點焦點</div>
                            <div style="font-size: 20px; font-weight: 800; color: #F8FAFC; margin-top: 2px;">
                                {selected_location}
                            </div>
                            <div style="font-size: 32px; font-weight: 900; color: {t_color}; margin: 8px 0;">
                                {t_avg} <span style="font-size: 18px; font-weight: 600; color: #94A3B8;">°C</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #CBD5E1;">
                                <span>最低: <b style="color: #38BDF8;">{today_row['MinT']}°C</b></span>
                                <span>最高: <b style="color: #F87171;">{today_row['MaxT']}°C</b></span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    with tab2:
        st.markdown(f"### 📍 {selected_location} · 未來 14 天高低溫走勢")
        df_forecast = fetch_forecast_data(selected_location)

        if df_forecast.empty:
            st.info(f"查無 {selected_location} 之預報資料。")
        else:
            # 4 大 KPI 卡片
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
                    color=["#F87171", "#38BDF8"],
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
