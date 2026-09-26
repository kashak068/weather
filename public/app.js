/* ═══════════════════════════════════════════════════
   app.js — Taiwan Weather Forecast Frontend Logic
   ═══════════════════════════════════════════════════ */

"use strict";

// ── State ──────────────────────────────────────────
let allLocations = [];
let currentMode  = "county";   // "county" | "region"
let currentLoc   = "臺北市";
let map          = null;
let markers      = [];
let tempChart    = null;

// ── Coordinates ───────────────────────────────────
const COUNTY_COORDS = {
  "基隆市":[25.1276,121.7392],"臺北市":[25.0375,121.5637],"新北市":[25.0169,121.4628],
  "桃園市":[24.9936,121.3010],"新竹市":[24.8138,120.9675],"新竹縣":[24.8387,121.0177],
  "苗栗縣":[24.5602,120.8214],"臺中市":[24.1477,120.6736],"彰化縣":[24.0518,120.5161],
  "南投縣":[23.9609,120.9719],"雲林縣":[23.7092,120.4313],"嘉義市":[23.4800,120.4491],
  "嘉義縣":[23.4518,120.2555],"臺南市":[22.9997,120.2270],"高雄市":[22.6273,120.3014],
  "屏東縣":[22.5519,120.5487],"宜蘭縣":[24.7021,121.7377],"花蓮縣":[23.9871,121.6016],
  "臺東縣":[22.7583,121.1444],"澎湖縣":[23.5711,119.5793],"金門縣":[24.4492,118.3766],
  "連江縣":[26.1505,119.9499]
};
const REGION_COORDS = {
  "北部地區":[25.04,121.55],"中部地區":[24.15,120.67],"南部地區":[22.99,120.21],
  "東北部地區":[24.75,121.75],"東部地區":[23.99,121.60],"東南部地區":[22.75,121.15],
  "離島地區":[24.00,119.00]
};

const COUNTY_ORDER = {
  "基隆市":[0,0],"臺北市":[0,1],"新北市":[0,2],"桃園市":[0,3],"新竹市":[0,4],"新竹縣":[0,5],
  "苗栗縣":[1,0],"臺中市":[1,1],"彰化縣":[1,2],"南投縣":[1,3],"雲林縣":[1,4],
  "嘉義市":[2,0],"嘉義縣":[2,1],"臺南市":[2,2],"高雄市":[2,3],"屏東縣":[2,4],
  "宜蘭縣":[3,0],"花蓮縣":[3,1],"臺東縣":[3,2],
  "澎湖縣":[4,0],"金門縣":[4,1],"連江縣":[4,2]
};
const REGION_ORDER = {
  "北部地區":[0,0],"中部地區":[1,0],"南部地區":[2,0],
  "東北部地區":[3,0],"東部地區":[3,1],"東南部地區":[3,2],"離島地區":[4,0]
};
const REGION_LABELS = {
  0:"── 北部 ──", 1:"── 中部 ──", 2:"── 南部 ──", 3:"── 東部 ──", 4:"── 離島 ──"
};

// ── Colour helpers ─────────────────────────────────
function getTempColor(temp) {
  if (temp < 18)  return "#3B82F6";
  if (temp < 23)  return "#10B981";
  if (temp < 28)  return "#F59E0B";
  return "#EF4444";
}

// ── Init ───────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initTabNav();
  initViewMode();
  initLocationSelect();
  loadData();
  updateTime();
  setInterval(updateTime, 60000);
});

function updateTime() {
  const el = document.getElementById("banner-time");
  if (el) el.textContent = "資料時間: " + new Date().toLocaleString("zh-TW", {
    year:"numeric", month:"2-digit", day:"2-digit",
    hour:"2-digit", minute:"2-digit"
  });
}

// ── Map Initialisation ─────────────────────────────
function initMap() {
  map = L.map("weather-map", {
    center: [23.75, 120.95], zoom: 7,
    zoomControl: true, attributionControl: true
  });

  // Google Maps road tiles
  L.tileLayer("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", {
    attribution: "© Google Maps",
    maxZoom: 20,
    tileSize: 256
  }).addTo(map);
}

// ── Tab navigation ─────────────────────────────────
function initTabNav() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");

      // resize map when switching back to map tab
      if (btn.dataset.tab === "map-tab" && map) {
        setTimeout(() => map.invalidateSize(), 60);
      }
    });
  });
}

// ── View Mode Radio ────────────────────────────────
function initViewMode() {
  document.querySelectorAll(".radio-option").forEach(opt => {
    opt.addEventListener("click", () => {
      document.querySelectorAll(".radio-option").forEach(o => o.classList.remove("active"));
      opt.classList.add("active");
      currentMode = opt.dataset.value;

      const label = document.getElementById("location-label");
      if (label) label.textContent = `選擇觀測地點 (${currentMode === "county" ? "縣市" : "分區"})`;

      const mapTitle = document.getElementById("map-title");
      if (mapTitle) mapTitle.textContent = `📍 臺灣${currentMode === "county" ? "全台 22 縣市" : "六大分區"}即時氣溫分布圖`;

      rebuildLocationSelect();
      renderMapMarkers();
    });
  });
}

// ── Location Select ────────────────────────────────
function initLocationSelect() {
  document.getElementById("location-select").addEventListener("change", e => {
    const val = e.target.value;
    if (!val || val.startsWith("──")) return;
    currentLoc = val;
    renderChartTab(currentLoc);
    updateSelectedCard(currentLoc);
  });
}

function rebuildLocationSelect() {
  const sel = document.getElementById("location-select");
  sel.innerHTML = "";

  const isCounty = currentMode === "county";
  const orderDict = isCounty ? COUNTY_ORDER : REGION_ORDER;
  const filteredLocs = allLocations.filter(l => {
    if (isCounty) return COUNTY_COORDS[l.name] !== undefined;
    return REGION_COORDS[l.name] !== undefined;
  });

  filteredLocs.sort((a, b) => {
    const oa = orderDict[a.name] || [99,99];
    const ob = orderDict[b.name] || [99,99];
    return oa[0] !== ob[0] ? oa[0] - ob[0] : oa[1] - ob[1];
  });

  let lastGroup = -1;
  filteredLocs.forEach(loc => {
    const group = (orderDict[loc.name] || [99,99])[0];
    if (group !== lastGroup) {
      lastGroup = group;
      const label = REGION_LABELS[group];
      if (label) {
        const opt = document.createElement("option");
        opt.value = label; opt.textContent = label;
        opt.disabled = true; opt.style.color = "#94A3B8";
        sel.appendChild(opt);
      }
    }
    const opt = document.createElement("option");
    opt.value = loc.name; opt.textContent = loc.name;
    sel.appendChild(opt);
  });

  // Set default
  const defaultLoc = isCounty ? "臺北市" : "北部地區";
  if (filteredLocs.find(l => l.name === defaultLoc)) {
    sel.value = defaultLoc;
    currentLoc = defaultLoc;
  } else if (filteredLocs.length > 0) {
    sel.value = filteredLocs[0].name;
    currentLoc = filteredLocs[0].name;
  }

  renderChartTab(currentLoc);
  updateSelectedCard(currentLoc);
}

// ── Load Data ──────────────────────────────────────
async function loadData() {
  try {
    const res = await fetch("/api/weather");
    const json = await res.json();
    if (json.success && json.locations) {
      allLocations = json.locations;
      renderAlerts(json.alerts);
    } else {
      allLocations = json.locations || json || [];
      renderAlerts(json.alerts);
    }
  } catch (err) {
    console.error("Failed to fetch weather data:", err);
    allLocations = generateFallback();
  }

  hideLoading();
  rebuildLocationSelect();
  renderMapMarkers();
}

async function syncData() {
  const btn = document.getElementById("sync-btn");
  btn.classList.add("loading");
  btn.innerHTML = `<span style="display:inline-block;animation:spin 1s linear infinite">↻</span> 同步中...`;

  try {
    const res = await fetch("/api/weather?refresh=1");
    const json = await res.json();
    if (json.locations) allLocations = json.locations;
    rebuildLocationSelect();
    renderMapMarkers();
  } catch(e) { /* silent */ }

  btn.classList.remove("loading");
  btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M13.65 2.35A8 8 0 1 0 16 8h-2a6 6 0 1 1-1.76-4.24L10 6h6V0l-2.35 2.35z" fill="currentColor"/></svg> 同步氣象署最新資料`;
}

function hideLoading() {
  const el = document.getElementById("loading-overlay");
  if (el) el.classList.add("hidden");
}

// ── Map Markers ────────────────────────────────────
function renderMapMarkers() {
  if (!map) return;
  markers.forEach(m => m.remove());
  markers = [];

  const isCounty = currentMode === "county";
  const coordsDict = isCounty ? COUNTY_COORDS : REGION_COORDS;
  const filtered = allLocations.filter(l => l.type === currentMode ||
    (currentMode === "county" && coordsDict[l.name]) ||
    (currentMode === "region" && coordsDict[l.name])
  );

  filtered.forEach(loc => {
    const coords = coordsDict[loc.name];
    if (!coords || !loc.forecasts || !loc.forecasts.length) return;

    const today = loc.forecasts[0];
    const minT = today.minT;
    const maxT = today.maxT;
    const avgT = +((minT + maxT) / 2).toFixed(1);
    const color = getTempColor(avgT);
    const dateStr = today.date;

    const iconHtml = `
      <div style="width:150px;height:48px;display:flex;flex-direction:column;
        align-items:center;justify-content:flex-end;
        filter:drop-shadow(0 2px 4px rgba(0,0,0,0.28));cursor:pointer;">
        <div style="background:#fff;color:#3C4043;font-family:'Inter',Roboto,Arial,sans-serif;
          font-weight:500;font-size:12px;padding:4px 10px;border-radius:16px;
          white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,0.28);
          border:1px solid #DADCE0;line-height:1.3;">
          <span style="font-weight:700;color:${color};">${avgT}°</span>
          <span style="color:#5F6368;font-size:11px;margin-left:2px;">${loc.name}</span>
        </div>
        <div style="width:0;height:0;border-left:6px solid transparent;
          border-right:6px solid transparent;border-top:8px solid #fff;"></div>
        <div style="width:8px;height:8px;border-radius:50%;background:${color};
          border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,0.28);"></div>
      </div>`;

    const popupHtml = `
      <div style="font-family:'Inter',Roboto,Arial,sans-serif;min-width:220px;max-width:280px;">
        <div style="padding:12px 16px 8px;border-bottom:1px solid #E8EAED;">
          <div style="font-size:16px;font-weight:600;color:#202124;margin-bottom:2px;">${loc.name}</div>
          <div style="font-size:12px;color:#70757A;">氣象預報 · ${dateStr}</div>
        </div>
        <div style="padding:12px 16px;">
          <div style="display:flex;align-items:baseline;margin-bottom:10px;">
            <span style="font-size:36px;font-weight:400;color:#202124;line-height:1;">${avgT}</span>
            <span style="font-size:18px;color:#70757A;margin-left:2px;">°C</span>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;
              background:${color};margin-left:8px;"></span>
          </div>
          <div style="display:flex;gap:16px;font-size:13px;color:#3C4043;">
            <div><span style="color:#70757A;">低溫</span><br>
              <span style="font-weight:600;color:#1A73E8;">${minT}°C</span></div>
            <div><span style="color:#70757A;">高溫</span><br>
              <span style="font-weight:600;color:#EA4335;">${maxT}°C</span></div>
            <div><span style="color:#70757A;">溫差</span><br>
              <span style="font-weight:600;color:#3C4043;">${(maxT-minT).toFixed(1)}°C</span></div>
          </div>
        </div>
        <div style="padding:8px 16px;border-top:1px solid #E8EAED;text-align:right;">
          <span style="font-size:11px;color:#1A73E8;font-weight:600;cursor:pointer;"
            onclick="selectLocation('${loc.name}')">查看詳細預報 →</span>
        </div>
      </div>`;

    const icon = L.divIcon({
      html: iconHtml,
      className: "",
      iconSize: [150, 48],
      iconAnchor: [75, 48]
    });

    const marker = L.marker(coords, { icon })
      .addTo(map)
      .bindPopup(popupHtml, { maxWidth: 300 });

    markers.push(marker);
  });
}

// Called from inline popup onclick
function selectLocation(name) {
  currentLoc = name;
  const sel = document.getElementById("location-select");
  if (sel) sel.value = name;

  // Switch to chart tab
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
  document.getElementById("tab-btn-chart").classList.add("active");
  document.getElementById("chart-tab").classList.add("active");

  renderChartTab(name);
  updateSelectedCard(name);
}

// ── Selected Card ──────────────────────────────────
function updateSelectedCard(name) {
  const loc = allLocations.find(l => l.name === name);
  const card = document.getElementById("selected-card");
  if (!loc || !loc.forecasts || !loc.forecasts.length) {
    if (card) card.style.display = "none";
    return;
  }

  const today = loc.forecasts[0];
  const avgT = +((today.minT + today.maxT) / 2).toFixed(1);
  const color = getTempColor(avgT);

  if (card) {
    card.style.display = "block";
    card.style.borderLeft = `4px solid ${color}`;
  }
  setText("selected-name", name);
  const tempEl = document.getElementById("selected-temp");
  if (tempEl) { tempEl.textContent = avgT + " °C"; tempEl.style.color = color; }
  setText("selected-min", today.minT + "°C");
  setText("selected-max", today.maxT + "°C");
}

// ── Chart Tab ──────────────────────────────────────
function renderChartTab(name) {
  const loc = allLocations.find(l => l.name === name);
  if (!loc || !loc.forecasts || !loc.forecasts.length) return;

  const forecasts = loc.forecasts;

  // Update titles
  setText("chart-title", `📍 ${name} · 未來 14 天高低溫走勢`);
  setText("chart-subtitle", `🌡️ ${name} 14 天雙曲線走勢圖`);

  // KPI
  const avgs   = forecasts.map(f => (f.minT + f.maxT) / 2);
  const avgAll = (avgs.reduce((a,b) => a+b, 0) / avgs.length).toFixed(1);
  const maxAll = Math.max(...forecasts.map(f => f.maxT));
  const minAll = Math.min(...forecasts.map(f => f.minT));
  const range  = (maxAll - minAll).toFixed(1);

  setText("kpi-avg",   avgAll + " °C");
  setText("kpi-max",   maxAll + " °C");
  setText("kpi-min",   minAll + " °C");
  setText("kpi-range", range  + " °C");
  setText("kpi-max-delta", `+${(maxAll - avgAll).toFixed(1)}°C`);
  setText("kpi-min-delta", `-${(avgAll - minAll).toFixed(1)}°C`);

  // Chart
  const labels = forecasts.map(f => f.date.slice(5)); // MM-DD
  const maxTs  = forecasts.map(f => f.maxT);
  const minTs  = forecasts.map(f => f.minT);

  const ctx = document.getElementById("temp-chart").getContext("2d");
  if (tempChart) tempChart.destroy();

  tempChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "最高溫 (°C)",
          data: maxTs,
          borderColor: "#EF4444",
          backgroundColor: "rgba(239,68,68,0.10)",
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 7,
          pointBackgroundColor: "#EF4444",
          borderWidth: 2.5,
        },
        {
          label: "最低溫 (°C)",
          data: minTs,
          borderColor: "#3B82F6",
          backgroundColor: "rgba(59,130,246,0.10)",
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 7,
          pointBackgroundColor: "#3B82F6",
          borderWidth: 2.5,
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", labels: { font: { size: 12, weight: "600" }, usePointStyle: true } },
        tooltip: {
          backgroundColor: "#1E293B",
          titleFont: { size: 13, weight: "700" },
          bodyFont: { size: 12 },
          padding: 12,
          cornerRadius: 8,
          callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}°C` }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(0,0,0,0.04)" },
          ticks: { font: { size: 11 }, color: "#64748B" }
        },
        y: {
          grid: { color: "rgba(0,0,0,0.04)" },
          ticks: { font: { size: 11 }, color: "#64748B", callback: v => v + "°C" }
        }
      }
    }
  });

  // Table
  const tbody = document.getElementById("forecast-tbody");
  if (tbody) {
    tbody.innerHTML = forecasts.map(f => {
      const avg = ((f.minT + f.maxT) / 2).toFixed(1);
      return `<tr>
        <td>${f.date}</td>
        <td class="td-min">${f.minT}</td>
        <td class="td-max">${f.maxT}</td>
        <td>${avg}</td>
        <td>${f.ws || "-"}</td>
        <td>${f.wd || "-"}</td>
      </tr>`;
    }).join("");
  }
}

// ── Sidebar mobile ─────────────────────────────────
function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("open");
}

// ── Fallback data ──────────────────────────────────
function generateFallback() {
  const counties = ["基隆市","臺北市","新北市","桃園市","新竹市","新竹縣","苗栗縣",
    "臺中市","彰化縣","南投縣","雲林縣","嘉義市","嘉義縣","臺南市","高雄市",
    "屏東縣","宜蘭縣","花蓮縣","臺東縣","澎湖縣","金門縣","連江縣"];
  const regions = ["北部地區","中部地區","南部地區","東北部地區","東部地區","東南部地區","離島地區"];
  const all = [...counties.map(n => ({name:n,type:"county"})), ...regions.map(n => ({name:n,type:"region"}))];

  return all.map(({name, type}) => {
    const forecasts = [];
    const today = new Date();
    for (let i = 0; i < 14; i++) {
      const d = new Date(today); d.setDate(d.getDate() + i);
      const dateStr = d.toISOString().slice(0,10);
      const v = (i % 4) - 1.5;
      forecasts.push({ date: dateStr, minT: +(23 + v).toFixed(1), maxT: +(31 + v).toFixed(1) });
    }
    return { name, type, forecasts };
  });
}

// ── Utility ────────────────────────────────────────
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function renderAlerts(alerts) {
  const container = document.getElementById("alerts-container");
  if (!container) return;
  if (!alerts || !alerts.length) {
    container.innerHTML = "";
    return;
  }
  
  container.innerHTML = alerts.map(alert => {
    const loc = alert.locationName || "未知區域";
    const phenomena = alert.phenomena || "特報";
    const text = alert.contentText || "";
    return `
      <div style="background-color: #FEE2E2; border-left: 4px solid #EF4444; color: #991B1B; padding: 12px 16px; margin-bottom: 12px; border-radius: 4px; font-size: 14px; font-weight: 500; display: flex; align-items: flex-start; gap: 8px;">
        <span style="font-size: 16px;">⚠️</span>
        <div><strong>${loc} ${phenomena}：</strong> ${text}</div>
      </div>
    `;
  }).join("");
}
