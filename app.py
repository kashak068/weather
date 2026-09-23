"""
app.py - Gate 4 & Gate 5: Streamlit 氣溫預報 Web App 與台灣地圖視覺化
從本機 SQLite (data.db) 讀取資料，提供：
1. 六大區域下拉選單
2. 溫度趨勢折線圖 (MaxT / MinT)
3. 一週天氣預報數據表格與統計指標
4. Folium 互動式台灣地圖與 4 階色階標記 (加分項)
"""

import os
import sqlite3
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium


# 頁面配置
st.set_page_config(
    page_title="HW10 Taiwan Weather Forecast",
    page_icon="⛅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 資料庫路徑
DB_FILE = "data.db"
TABLE_NAME = "TemperatureForecasts"

# 六大區域座標 (緯度, 經度)
REGION_COORDINATES = {
    "北部地區": (25.04, 121.55),
    "中部地區": (24.15, 120.67),
    "南部地區": (22.99, 120.21),
    "東北部地區": (24.75, 121.75),
    "東部地區": (23.99, 121.60),
    "東南部地區": (22.75, 121.15),
}


def get_db_connection():
    """建立 SQLite 資料庫連線。"""
    if not os.path.exists(DB_FILE):
        return None
    return sqlite3.connect(DB_FILE)


def fetch_regions():
    """從 SQLite 查詢所有不重複地區名稱。"""
    conn = get_db_connection()
    if conn is None:
        return []
    try:
        query = f"SELECT DISTINCT regionName FROM {TABLE_NAME} ORDER BY regionName;"
        df = pd.read_sql_query(query, conn)
        return df["regionName"].tolist()
    except Exception as e:
        st.error(f"讀取地區清單失敗: {e}")
        return []
    finally:
        conn.close()


def fetch_forecast_data(region_name: str) -> pd.DataFrame:
    """使用 SQL 查詢指定地區的一週氣溫預報。"""
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
        df = pd.read_sql_query(query, conn, params=(region_name,))
        if not df.empty:
            df["AvgT"] = ((df["MinT"] + df["MaxT"]) / 2).round(1)
        return df
    except Exception as e:
        st.error(f"查詢氣溫資料失敗: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def fetch_all_latest_data() -> pd.DataFrame:
    """查詢所有地區最新一日氣溫預報供地圖使用。"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        query = f"""
        SELECT t.regionName, t.dataDate, t.minT, t.maxT
        FROM {TABLE_NAME} t
        INNER JOIN (
            SELECT regionName, MIN(dataDate) as minDate
            FROM {TABLE_NAME}
            GROUP BY regionName
        ) m ON t.regionName = m.regionName AND t.dataDate = m.minDate;
        """
        df = pd.read_sql_query(query, conn)
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
    25 - 30°C: 黃色/橙色 (orange)
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


def render_map(map_data: pd.DataFrame):
    """繪製 Folium 台灣溫度分布互動式地圖。"""
    # 台灣中心座標
    m = folium.Map(location=[23.7, 120.95], zoom_start=7, tiles="CartoDB positron")

    for _, row in map_data.iterrows():
        reg_name = row["regionName"]
        coords = REGION_COORDINATES.get(reg_name)
        if not coords:
            continue

        min_t = row["minT"]
        max_t = row["maxT"]
        avg_t = row["avgT"]
        date_str = row["dataDate"]
        color = get_temp_color(avg_t)

        popup_html = f"""
        <div style="font-family: Arial, sans-serif; min-width: 140px; padding: 4px;">
            <h4 style="margin: 0 0 6px 0; color: #333;">{reg_name}</h4>
            <p style="margin: 2px 0; font-size: 12px; color: #666;">預報日期: <b>{date_str}</b></p>
            <hr style="margin: 4px 0;">
            <p style="margin: 2px 0; font-size: 13px;">平均溫: <b style="color:{color};">{avg_t} °C</b></p>
            <p style="margin: 2px 0; font-size: 12px; color: #1E88E5;">最低溫: <b>{min_t} °C</b></p>
            <p style="margin: 2px 0; font-size: 12px; color: #E53935;">最高溫: <b>{max_t} °C</b></p>
        </div>
        """

        folium.CircleMarker(
            location=coords,
            radius=12,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=2,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{reg_name}: {avg_t}°C ({date_str})",
        ).add_to(m)

    st_folium(m, width="100%", height=480, returned_objects=[])


def main():
    # 標題與簡介
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E88E5, #1565C0); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 28px;">⛅ HW10 Taiwan Weather Forecast</h1>
            <p style="margin: 8px 0 0 0; opacity: 0.9; font-size: 14px;">
                中央氣象署 (CWA) 一週天氣預報視覺化儀表板 | SQLite 資料查詢 × Streamlit × Folium 地圖
            </p>
        </div>
    """, unsafe_allow_html=True)

    # 檢查資料庫是否存在
    if not os.path.exists(DB_FILE):
        st.warning("⚠️ 尚未偵測到 `data.db` 資料庫！請先執行資料擷取與儲存管線。")
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
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

    # 讀取地區清單
    regions = fetch_regions()
    if not regions:
        st.error("資料庫內無可用的地區資料。")
        st.stop()

    # 側邊欄配置
    st.sidebar.header("🔍 控制台 (Controls)")
    selected_region = st.sidebar.selectbox(
        "選擇預報地區 (Select Region):",
        options=regions,
        index=regions.index("中部地區") if "中部地區" in regions else 0
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 資料同步與重整")
    if st.sidebar.button("重新整理資料庫 (Fetch & Sync)"):
        with st.spinner("同步氣象署最新預報中..."):
            from fetch_weather import fetch_cwa_weather
            from parse_weather import parse_weather_json
            from database import insert_forecasts
            
            fetch_cwa_weather()
            records = parse_weather_json("raw_weather.json")
            insert_forecasts(records, DB_FILE)
        st.sidebar.success("資料已成功更新！")
        st.rerun()

    st.sidebar.info("""
    **資料來源**: 交通部中央氣象署 CWA
    **資料集**: `F-A0010-001` 一週天氣預報
    **架構**: 本地 SQLite 資料庫快取
    """)

    # 主內容區：Tab 分頁 (預報趨勢 vs 全台地圖)
    tab1, tab2 = st.tabs(["📈 地區一週氣溫預報", "🗺️ 台灣地圖溫度分布 (加分項)"])

    with tab1:
        st.subheader(f"📍 {selected_region} - 一週氣溫趨勢預報")
        df_forecast = fetch_forecast_data(selected_region)

        if df_forecast.empty:
            st.info(f"查無 {selected_region} 之預報資料。")
        else:
            # KPI 指標卡
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            avg_all = df_forecast["AvgT"].mean()
            max_all = df_forecast["MaxT"].max()
            min_all = df_forecast["MinT"].min()
            temp_range = max_all - min_all

            kpi1.metric("一週平均氣溫", f"{avg_all:.1f} °C")
            kpi2.metric("一週最高溫", f"{max_all:.1f} °C", delta=f"+{(max_all - avg_all):.1f}°C", delta_color="inverse")
            kpi3.metric("一週最低溫", f"{min_all:.1f} °C", delta=f"-{(avg_all - min_all):.1f}°C")
            kpi4.metric("最大日夜/週期溫差", f"{temp_range:.1f} °C")

            st.markdown("---")

            # 佈局：折線圖與表格並列
            col_chart, col_table = st.columns([3, 2])

            with col_chart:
                st.markdown("#### 🌡️ 最高溫 (MaxT) 與 最低溫 (MinT) 折線圖")
                chart_data = df_forecast.set_index("Date")[["MaxT", "MinT"]]
                st.line_chart(
                    chart_data,
                    color=["#E53935", "#1E88E5"],
                    use_container_width=True
                )

            with col_table:
                st.markdown("#### 📋 預報詳細數據")
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
        st.subheader("🗺️ 台灣六大區域即時/今日平均氣溫分布")
        map_df = fetch_all_latest_data()
        
        if map_df.empty:
            st.info("尚無地圖展示資料。")
        else:
            col_m, col_info = st.columns([3, 1])
            with col_m:
                render_map(map_df)
            with col_info:
                st.markdown("#### 🎨 平均溫度圖例 (Legend)")
                st.markdown("""
                - 🔵 **< 20°C** : 偏涼 / 寒冷
                - 🟢 **20°C - 25°C** : 舒適
                - 🟠 **25°C - 30°C** : 溫暖 / 偏熱
                - 🔴 **> 30°C** : 炎熱高溫
                """)
                st.markdown("---")
                st.markdown("#### 💡 操作提示")
                st.caption("點擊地圖上的各區圓形標記，可查看該區域完整預報數值與高低溫資訊。")


if __name__ == "__main__":
    main()
