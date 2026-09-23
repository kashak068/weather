"""
app.py - Gate 4 & Gate 5: Streamlit 氣溫預報 Web App 與全台 22 縣市地圖視覺化
從本機 SQLite (data.db) 讀取資料，提供：
1. 全台 22 縣市與六大分區切換選擇
2. 溫度趨勢折線圖 (MaxT / MinT)
3. 一週天氣預報數據表格與統計指標
4. Folium 互動式台灣全台縣市溫度地圖與 4 階色階標記
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium


# 頁面配置
st.set_page_config(
    page_title="Taiwan Weather Forecast - 全台各縣市氣溫預報",
    page_icon="⛅",
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

# 六大分區中心座標
REGION_COORDINATES = {
    "北部地區": (25.04, 121.55),
    "中部地區": (24.15, 120.67),
    "南部地區": (22.99, 120.21),
    "東北部地區": (24.75, 121.75),
    "東部地區": (23.99, 121.60),
    "東南部地區": (22.75, 121.15),
    "離島地區": (24.00, 119.00),
}


def get_db_connection():
    """建立 SQLite 資料庫連線。"""
    if not os.path.exists(DB_FILE):
        return None
    return sqlite3.connect(DB_FILE)


def fetch_location_list(location_type: str = None):
    """從 SQLite 查詢所有不重複地點/縣市名稱。"""
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
    except Exception as e:
        st.error(f"讀取地點清單失敗: {e}")
        return []
    finally:
        conn.close()


def fetch_forecast_data(location_name: str) -> pd.DataFrame:
    """使用 SQL 查詢指定縣市/地區的一週氣溫預報。"""
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
    except Exception as e:
        st.error(f"查詢氣溫資料失敗: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def fetch_map_data(location_type: str = "county") -> pd.DataFrame:
    """查詢所有縣市或區域最近一日氣溫預報供地圖使用。"""
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
    except Exception as e:
        st.error(f"讀取地圖資料失敗: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_temp_color(avg_temp: float) -> str:
    """根據平均氣溫判定色階顏色。
    < 20°C: 藍色 (blue)
    20 - 25°C: 綠色 (green)
    25 - 30°C: 橙黃色 (orange)
    > 30°C: 紅色 (red)
    """
    if avg_temp < 20.0:
        return "blue"
    elif 20.0 <= avg_temp < 25.0:
        return "green"
    elif 25.0 <= avg_temp <= 30.0:
        return "orange"
    else:
        return "red"


def render_map(map_data: pd.DataFrame, is_county: bool = True):
    """繪製 Folium 台灣溫度分布互動式地圖。"""
    coords_dict = COUNTY_COORDINATES if is_county else REGION_COORDINATES
    m = folium.Map(location=[23.7, 120.95], zoom_start=7 if not is_county else 7.5, tiles="CartoDB positron")

    for _, row in map_data.iterrows():
        name = row["regionName"]
        coords = coords_dict.get(name)
        if not coords:
            continue

        min_t = row["minT"]
        max_t = row["maxT"]
        avg_t = row["avgT"]
        date_str = row["dataDate"]
        color = get_temp_color(avg_t)

        popup_html = f"""
        <div style="font-family: Arial, sans-serif; min-width: 150px; padding: 4px;">
            <h4 style="margin: 0 0 6px 0; color: #1E88E5;">{name}</h4>
            <p style="margin: 2px 0; font-size: 12px; color: #666;">預報日期: <b>{date_str}</b></p>
            <hr style="margin: 4px 0;">
            <p style="margin: 2px 0; font-size: 13px;">平均溫: <b style="color:{color}; font-size:14px;">{avg_t} °C</b></p>
            <p style="margin: 2px 0; font-size: 12px; color: #1E88E5;">最低溫: <b>{min_t} °C</b></p>
            <p style="margin: 2px 0; font-size: 12px; color: #E53935;">最高溫: <b>{max_t} °C</b></p>
        </div>
        """

        folium.CircleMarker(
            location=coords,
            radius=10 if is_county else 14,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=2,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{name}: {avg_t}°C (Min:{min_t}°C / Max:{max_t}°C)",
        ).add_to(m)

    st_folium(m, width="100%", height=520, returned_objects=[])


def main():
    st.markdown("""
        <div style="background: linear-gradient(135deg, #0288D1, #1565C0); padding: 22px; border-radius: 12px; color: white; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 28px;">⛅ HW10 Taiwan Weather Forecast</h1>
            <p style="margin: 8px 0 0 0; opacity: 0.95; font-size: 15px;">
                中央氣象署 (CWA) 臺灣全台 22 縣市與六大分區 · 一週天氣預報視覺化儀表板
            </p>
        </div>
    """, unsafe_allow_html=True)

    if not os.path.exists(DB_FILE):
        st.warning("⚠️ 尚未偵測到 `data.db` 資料庫！請先執行資料擷取與儲存管線。")
        if st.button("🚀 立即建立資料庫 (執行管線)"):
            with st.spinner("正在執行資料管線 (fetch -> parse -> database)..."):
                from fetch_weather import fetch_cwa_weather
                from parse_weather import parse_weather_json
                from database import insert_forecasts
                
                fetch_cwa_weather()
                records = parse_weather_json("raw_weather.json")
                insert_forecasts(records, DB_FILE)
            st.success("資料庫已成功建立！")
            st.rerun()
        st.stop()

    # 側邊欄控制台
    st.sidebar.header("🔍 預報篩選控制台")
    
    # 模式切換：依縣市 vs 依分區
    view_mode = st.sidebar.radio(
        "選擇檢視維度 (View Mode):",
        options=["全台 22 縣市 (細項)", "六大地理分區 (整合)"],
        index=0
    )

    is_county_mode = "22 縣市" in view_mode
    target_type = "county" if is_county_mode else "region"
    
    available_locations = fetch_location_list(location_type=target_type)
    if not available_locations:
        available_locations = fetch_location_list()

    # 預設選中
    default_idx = 0
    if is_county_mode and "臺北市" in available_locations:
        default_idx = available_locations.index("臺北市")
    elif not is_county_mode and "中部地區" in available_locations:
        default_idx = available_locations.index("中部地區")

    selected_location = st.sidebar.selectbox(
        f"選擇{'縣市' if is_county_mode else '分區'}:",
        options=available_locations,
        index=default_idx
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 資料同步")
    if st.sidebar.button("更新最新預報 (Sync Live Data)"):
        with st.spinner("正在從中央氣象署抓取最新預報..."):
            from fetch_weather import fetch_cwa_weather
            from parse_weather import parse_weather_json
            from database import insert_forecasts
            
            fetch_cwa_weather()
            records = parse_weather_json("raw_weather.json")
            insert_forecasts(records, DB_FILE)
        st.sidebar.success("資料已成功更新至最新！")
        st.rerun()

    st.sidebar.info("""
    **資料來源**: 中央氣象署 CWA Open Data
    **涵蓋範圍**: 全台 22 縣市 + 6 大分區
    **更新頻率**: 7 天滾動預報
    """)

    # 主分頁
    tab1, tab2 = st.tabs(["📈 一週氣溫趨勢預報", "🗺️ 全台互動氣溫地圖"])

    with tab1:
        st.subheader(f"📍 {selected_location} - 未來一週氣溫預報趨勢")
        df_forecast = fetch_forecast_data(selected_location)

        if df_forecast.empty:
            st.info(f"查無 {selected_location} 之預報資料。")
        else:
            # KPI 指標卡
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            avg_all = df_forecast["AvgT"].mean()
            max_all = df_forecast["MaxT"].max()
            min_all = df_forecast["MinT"].min()
            temp_range = max_all - min_all

            kpi1.metric("一週平均氣溫", f"{avg_all:.1f} °C")
            kpi2.metric("一週最高氣溫", f"{max_all:.1f} °C", delta=f"+{(max_all - avg_all):.1f}°C", delta_color="inverse")
            kpi3.metric("一週最低氣溫", f"{min_all:.1f} °C", delta=f"-{(avg_all - min_all):.1f}°C")
            kpi4.metric("週期最大溫差", f"{temp_range:.1f} °C")

            st.markdown("---")

            col_chart, col_table = st.columns([3, 2])

            with col_chart:
                st.markdown(f"#### 🌡️ {selected_location} 高低溫折線圖")
                chart_data = df_forecast.set_index("Date")[["MaxT", "MinT"]]
                st.line_chart(
                    chart_data,
                    color=["#E53935", "#1E88E5"],
                    use_container_width=True
                )

            with col_table:
                st.markdown("#### 📋 每日詳細預報數據")
                display_df = df_forecast.rename(columns={
                    "Date": "預報日期",
                    "MinT": "最低溫 (°C)",
                    "MaxT": "最高溫 (°C)",
                    "AvgT": "平均溫 (°C)"
                })
                st.dataframe(
                    display_df,
                    hide_index=True,
                    use_container_width=True
                )

    with tab2:
        st.subheader(f"🗺️ 台灣{'全台 22 縣市' if is_county_mode else '六大分區'}即時氣溫分布圖")
        map_df = fetch_map_data(location_type=target_type)
        
        if map_df.empty:
            st.info("尚無地圖展示資料。")
        else:
            col_m, col_info = st.columns([3, 1])
            with col_m:
                render_map(map_df, is_county=is_county_mode)
            with col_info:
                st.markdown("#### 🎨 溫度色階圖例 (Legend)")
                st.markdown("""
                - 🔵 **< 20°C** : 偏涼 / 寒冷
                - 🟢 **20°C - 25°C** : 舒適
                - 🟠 **25°C - 30°C** : 溫暖 / 偏熱
                - 🔴 **> 30°C** : 炎熱高溫
                """)
                st.markdown("---")
                st.markdown("#### 💡 提示")
                st.caption(f"地圖共標註 **{len(map_df)}** 個{'縣市' if is_county_mode else '分區'}，點擊各圓形標記可檢視該地詳細預報與高低溫數值。")


if __name__ == "__main__":
    main()
