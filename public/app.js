/* ═══════════════════════════════════════════════════
   app.js — Taiwan Weather Forecast Frontend Logic
   中央氣象署 (CWA) 唯一官方開放資料來源
   獨立可切換圖層：降雨量 · 風向風速 · 紫外線指數 · 氣溫
   ═══════════════════════════════════════════════════ */

"use strict";

// ── State ──────────────────────────────────────────
let allLocations = [];
let currentMode  = "county";   // "county" | "region"
let currentLoc   = "臺北市";
let map          = null;
let tempChart    = null;
let isDemoAlert  = false;
let isDemoNowcast = false;

// ── Independent Layer States ──────────────────────
// Users can independently turn each layer on or off
const activeLayers = {
  rain: true,   // 🌧️ Rainfall
  wind: true,   // 💨 Wind direction & wind speed
  uv:   true,   // ☀️ UV Index
  temp: false   // 🌡️ Temperature (supplementary)
};

// Leaflet LayerGroups for each metric
let rainLayerGroup = null;
let windLayerGroup = null;
let uvLayerGroup   = null;
let tempLayerGroup = null;
let leafletLayerControl = null;

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

// ── Temperature Helpers ────────────────────────────
function getTempColor(temp) {
  if (temp < 18)  return "#3B82F6";
  if (temp < 23)  return "#10B981";
  if (temp < 28)  return "#F59E0B";
  return "#EF4444";
}

// ── Rainfall Helpers (CWA standards) ───────────────
function getRainColor(mm) {
  if (mm === null || mm === undefined) return "#94A3B8";
  if (mm === 0)   return "#0284C7"; // Clean sky blue for 0
  if (mm < 2)     return "#0EA5E9";
  if (mm < 10)    return "#0284C7";
  if (mm < 30)    return "#0369A1";
  if (mm < 80)    return "#7C3AED";
  return "#C026D3";
}
function getRainLabel(mm) {
  if (mm === null || mm === undefined) return "資料暫缺";
  if (mm === 0)   return "無降雨";
  if (mm < 2)     return "微量";
  if (mm < 10)    return "小雨";
  if (mm < 30)    return "中雨";
  if (mm < 80)    return "大雨";
  return "豪雨";
}

// ── Wind Helpers (Beaufort Scale & Compass) ────────
function parseWindMs(wsStr) {
  if (wsStr === null || wsStr === undefined || wsStr === "-") return null;
  const n = parseFloat(String(wsStr));
  return isNaN(n) ? null : n;
}
function getWindColor(ms) {
  if (ms === null) return "#94A3B8";
  if (ms < 3.4)  return "#10B981";  // 0-2級 綠色
  if (ms < 8.0)  return "#059669";  // 3-4級 青綠
  if (ms < 13.9) return "#0D9488";  // 5-6級 深青
  if (ms < 20.8) return "#F59E0B";  // 7-8級 警示橙
  return "#EF4444";                 // 9+級 警示紅
}
function getWindBeaufort(ms) {
  if (ms === null || isNaN(ms)) return "—";
  if (ms < 0.3) return "0級 (無風)";
  if (ms < 1.6) return "1級 (軟風)";
  if (ms < 3.4) return "2級 (輕風)";
  if (ms < 5.5) return "3級 (微風)";
  if (ms < 8.0) return "4級 (和風)";
  if (ms < 10.8) return "5級 (清風)";
  if (ms < 13.9) return "6級 (強風)";
  if (ms < 17.2) return "7級 (疾風)";
  if (ms < 20.8) return "8級 (大風)";
  if (ms < 24.5) return "9級 (烈風)";
  return "10+級 (暴風)";
}

const DIR_DEG = {
  "北":0,"北北東":22.5,"東北":45,"東北東":67.5,
  "東":90,"東南東":112.5,"東南":135,"南南東":157.5,
  "南":180,"南南西":202.5,"西南":225,"西南西":247.5,
  "西":270,"西北西":292.5,"西北":315,"北北西":337.5,
  "偏北":0,"偏南":180,"偏東":90,"偏西":270,
  "東北季":45,"東南季":135,"西南季":225,"西北季":315
};
function compassToDeg(dir) {
  if (!dir || dir === "-") return null;
  const stripped = String(dir).replace(/風$/,"");
  const key = Object.keys(DIR_DEG).find(k => stripped === k || stripped.startsWith(k));
  if (key !== undefined) return DIR_DEG[key];
  const m = String(dir).match(/([0-9.]+)/);
  return m ? +m[1] : null;
}

// ── UV Index Helpers (WHO & CWA Standards) ─────────
function getUvColor(uvi) {
  if (uvi === null || uvi === undefined || isNaN(uvi) || uvi < 0) return "#94A3B8";
  if (uvi <= 2.4)  return "#16A34A"; // 低量級 (綠)
  if (uvi <= 5.4)  return "#CA8A04"; // 中量級 (黃)
  if (uvi <= 7.4)  return "#EA580C"; // 高量級 (橙)
  if (uvi <= 10.4) return "#DC2626"; // 過量級 (紅)
  return "#9333EA";                  // 危險級 (紫)
}
function getUvLevel(uvi) {
  if (uvi === null || uvi === undefined || isNaN(uvi) || uvi < 0) return "資料暫缺";
  if (uvi <= 2.4)  return "低量級";
  if (uvi <= 5.4)  return "中量級";
  if (uvi <= 7.4)  return "高量級";
  if (uvi <= 10.4) return "過量級";
  return "危險級";
}
function getUvAdvice(uvi) {
  if (uvi === null || uvi === undefined || isNaN(uvi) || uvi < 0) return "無紫外線資料";
  if (uvi <= 2.4)  return "帽子或太陽眼鏡正常防護。";
  if (uvi <= 5.4)  return "外出宜塗抹防曬乳、戴遮陽帽或撐陽傘。";
  if (uvi <= 7.4)  return "紫外線偏強，曝曬 20 分鐘有曬傷危險，宜戴帽防曬。";
  if (uvi <= 10.4) return "紫外線過量，10-14 點避免在烈日下曝曬。";
  return "紫外線達危險級，盡量避免非必要戶外活動！";
}

// ── Init ───────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initLayerToggles();
  initTabNav();
  initViewMode();
  initLocationSelect();
  loadData();
  updateTime();
  setInterval(updateTime, 60000);
});

function updateTime(customTime) {
  const el = document.getElementById("banner-time");
  if (!el) return;
  if (customTime) {
    el.textContent = "資料時間: " + customTime;
  } else {
    el.textContent = "資料時間: " + new Date().toLocaleString("zh-TW", {
      year:"numeric", month:"2-digit", day:"2-digit",
      hour:"2-digit", minute:"2-digit"
    });
  }
}

// ── Map Initialisation ─────────────────────────────
function initMap() {
  map = L.map("weather-map", {
    center: [23.75, 120.95], zoom: 7,
    zoomControl: true, attributionControl: true
  });

  // Google Maps road tiles
  L.tileLayer("https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", {
    attribution: "© Google Maps | CWA 中央氣象署開放資料",
    maxZoom: 20,
    tileSize: 256
  }).addTo(map);

  // Initialize independent LayerGroups
  rainLayerGroup = L.layerGroup();
  windLayerGroup = L.layerGroup();
  uvLayerGroup   = L.layerGroup();
  tempLayerGroup = L.layerGroup();

  // Attach initially active layers to the map
  if (activeLayers.rain) rainLayerGroup.addTo(map);
  if (activeLayers.wind) windLayerGroup.addTo(map);
  if (activeLayers.uv)   uvLayerGroup.addTo(map);
  if (activeLayers.temp) tempLayerGroup.addTo(map);

  // Add Leaflet native Layer Control (topright)
  const overlayMaps = {
    "🌧️ 降雨量 (Rainfall)": rainLayerGroup,
    "💨 風向與風速 (Wind)": windLayerGroup,
    "☀️ 紫外線指數 (UV Index)": uvLayerGroup,
    "🌡️ 即時氣溫 (Temperature)": tempLayerGroup
  };
  leafletLayerControl = L.control.layers(null, overlayMaps, {
    collapsed: true,
    position: "topright"
  }).addTo(map);

  // Synchronize Leaflet map layer control changes with UI toggle buttons
  map.on("overlayadd", e => {
    if (e.layer === rainLayerGroup) setLayerState("rain", true, false);
    else if (e.layer === windLayerGroup) setLayerState("wind", true, false);
    else if (e.layer === uvLayerGroup) setLayerState("uv", true, false);
    else if (e.layer === tempLayerGroup) setLayerState("temp", true, false);
  });
  map.on("overlayremove", e => {
    if (e.layer === rainLayerGroup) setLayerState("rain", false, false);
    else if (e.layer === windLayerGroup) setLayerState("wind", false, false);
    else if (e.layer === uvLayerGroup) setLayerState("uv", false, false);
    else if (e.layer === tempLayerGroup) setLayerState("temp", false, false);
  });
}

// ── Independent Layer Toggles Control ──────────────
function initLayerToggles() {
  document.querySelectorAll(".layer-toggle-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const layerKey = btn.dataset.layer;
      if (!layerKey || activeLayers[layerKey] === undefined) return;
      const newState = !activeLayers[layerKey];
      setLayerState(layerKey, newState, true);
    });
  });
}

function setLayerState(layerKey, isEnabled, updateMapInstance) {
  activeLayers[layerKey] = isEnabled;

  const btn = document.getElementById(`layer-toggle-${layerKey}`);
  if (btn) {
    btn.classList.toggle("active", isEnabled);
    btn.setAttribute("aria-pressed", isEnabled ? "true" : "false");
    const pill = btn.querySelector(".layer-toggle-pill");
    if (pill) {
      pill.textContent = isEnabled ? "ON" : "OFF";
      pill.className = `layer-toggle-pill ${isEnabled ? "on" : "off"}`;
    }
  }

  const groupMap = {
    rain: rainLayerGroup,
    wind: windLayerGroup,
    uv:   uvLayerGroup,
    temp: tempLayerGroup
  };
  const targetGroup = groupMap[layerKey];

  if (updateMapInstance && map && targetGroup) {
    if (isEnabled && !map.hasLayer(targetGroup)) {
      map.addLayer(targetGroup);
    } else if (!isEnabled && map.hasLayer(targetGroup)) {
      map.removeLayer(targetGroup);
    }
  }

  updateMapTitle();
  updateLegendsVisibility();
  renderAllLayerMarkers();
}

function toggleAllLayers(enableAll) {
  ["rain", "wind", "uv", "temp"].forEach(key => {
    // If enabling all, turn on rain, wind, uv, temp
    // If resetting, turn off all
    setLayerState(key, enableAll, true);
  });
}

// ── Map Title Helper ───────────────────────────────
function updateMapTitle() {
  const mapTitle = document.getElementById("map-title");
  if (!mapTitle) return;
  const scopeLabel = currentMode === "county" ? "全台 22 縣市" : "六大分區";

  const activeNames = [];
  if (activeLayers.rain) activeNames.push("雨量");
  if (activeLayers.wind) activeNames.push("風況");
  if (activeLayers.uv)   activeNames.push("紫外線");
  if (activeLayers.temp) activeNames.push("氣溫");

  if (activeNames.length === 0) {
    mapTitle.textContent = `📍 臺灣${scopeLabel}氣象圖層（目前已全部隱藏）`;
  } else {
    mapTitle.textContent = `📍 臺灣${scopeLabel}即時 ${activeNames.join(" · ")} 分布圖`;
  }
}

// ── Multi-Legends Visibility ───────────────────────
function updateLegendsVisibility() {
  const rainCard = document.getElementById("legend-rain-card");
  const windCard = document.getElementById("legend-wind-card");
  const uvCard   = document.getElementById("legend-uv-card");
  const tempCard = document.getElementById("legend-temp-card");
  const emptyCard= document.getElementById("legend-empty-card");

  if (rainCard) rainCard.style.display = activeLayers.rain ? "block" : "none";
  if (windCard) windCard.style.display = activeLayers.wind ? "block" : "none";
  if (uvCard)   uvCard.style.display   = activeLayers.uv   ? "block" : "none";
  if (tempCard) tempCard.style.display = activeLayers.temp ? "block" : "none";

  const hasAnyActive = Object.values(activeLayers).some(Boolean);
  if (emptyCard) emptyCard.style.display = hasAnyActive ? "none" : "block";
}

// ── Tab navigation ─────────────────────────────────
function initTabNav() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");

      // Resize map when switching back to map tab
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

      updateMapTitle();
      rebuildLocationSelect();
      renderAllLayerMarkers();
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
async function loadData(isSync = false) {
  try {
    let params = [];
    if (isDemoAlert) params.push("demo_alert=1");
    if (isDemoNowcast) params.push("demo_nowcast=1");
    if (isSync) { params.push("refresh=1"); params.push(`t=${Date.now()}`); }
    const query = params.length > 0 ? "?" + params.join("&") : "";
    const res = await fetch(`/api/weather${query}`);
    const json = await res.json();
    if (json.success && json.locations) {
      allLocations = json.locations;
      renderAlerts(json.alerts || [], json.alertStatus);
      renderNowcast(json.nowcastMessages || [], json.nowcastStatus);
      if (json.updatedAt) updateTime(json.updatedAt);
    } else {
      allLocations = json.locations || json || [];
      renderAlerts(json.alerts || [], json.alertStatus);
      renderNowcast(json.nowcastMessages || [], json.nowcastStatus);
    }
  } catch (err) {
    console.error("Failed to fetch weather data:", err);
    allLocations = generateFallback();
    renderAlerts([], "CLEAR");
    renderNowcast([], "CLEAR");
  }

  hideLoading();
  rebuildLocationSelect();
  renderAllLayerMarkers();
  updateLegendsVisibility();
}

async function syncData() {
  const btn = document.getElementById("sync-btn");
  btn.classList.add("loading");
  btn.innerHTML = `<span style="display:inline-block;animation:spin 1s linear infinite">↻</span> 同步中央氣象署資料中...`;

  try {
    await loadData(true);
  } catch(e) {
    console.error("Sync error:", e);
  }

  btn.classList.remove("loading");
  btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M13.65 2.35A8 8 0 1 0 16 8h-2a6 6 0 1 1-1.76-4.24L10 6h6V0l-2.35 2.35z" fill="currentColor"/></svg> 同步氣象署最新資料`;
}

function toggleDemoAlerts() {
  isDemoAlert = !isDemoAlert;
  loadData();
}

function hideLoading() {
  const el = document.getElementById("loading-overlay");
  if (el) el.classList.add("hidden");
}

// ── Smart Anchor Offsets for Coexisting Layers ────
function computeLayerAnchorOffsets() {
  // Count how many of [rain, wind, uv, temp] are currently enabled
  const activeKeys = ["rain", "wind", "uv", "temp"].filter(k => activeLayers[k]);
  const count = activeKeys.length;

  if (count <= 1) {
    return {
      rain: [22, 22],
      wind: [22, 22],
      uv:   [22, 22],
      temp: [75, 48]
    };
  }

  // When multiple layers are enabled, gracefully spread their anchors
  // rain sits on bottom-left, wind sits on bottom-right, uv sits on top-center
  return {
    rain: [44, 2],    // shifted left
    wind: [2, 2],     // shifted right
    uv:   [23, 44],   // shifted top
    temp: [75, 20]    // centered
  };
}

// ── Render All Layer Markers ───────────────────────
function renderAllLayerMarkers() {
  if (!map) return;

  // Clear existing markers from all layer groups
  if (rainLayerGroup) rainLayerGroup.clearLayers();
  if (windLayerGroup) windLayerGroup.clearLayers();
  if (uvLayerGroup)   uvLayerGroup.clearLayers();
  if (tempLayerGroup) tempLayerGroup.clearLayers();

  const coordsDict = currentMode === "county" ? COUNTY_COORDS : REGION_COORDS;
  const filtered   = allLocations.filter(l => coordsDict[l.name]);
  const offsets    = computeLayerAnchorOffsets();

  filtered.forEach(loc => {
    const coords = coordsDict[loc.name];
    if (!coords) return;

    // 1. Rainfall Marker (Layer 1)
    if (activeLayers.rain) {
      renderRainMarker(loc, coords, offsets.rain);
    }

    // 2. Wind Direction & Speed Marker (Layer 2)
    if (activeLayers.wind) {
      renderWindMarker(loc, coords, offsets.wind);
    }

    // 3. UV Index Marker (Layer 3)
    if (activeLayers.uv) {
      renderUvMarker(loc, coords, offsets.uv);
    }

    // 4. Temperature Marker (Layer 4)
    if (activeLayers.temp) {
      renderTempMarker(loc, coords, offsets.temp);
    }
  });
}

// ── 1. Rainfall Layer Marker & Popup ──────────────
function renderRainMarker(loc, coords, anchor) {
  const obs      = loc.observation || {};
  const rainfall = (obs.rainfall !== undefined && obs.rainfall !== null) ? obs.rainfall : 0.0;
  const humidity = (obs.humidity !== undefined && obs.humidity !== null) ? obs.humidity : null;
  const obsTemp  = (obs.temp !== undefined && obs.temp !== null) ? obs.temp : null;
  const obsTime  = obs.obsTime || null;
  const station  = obs.stationName || loc.name;
  const color    = getRainColor(rainfall);
  const label    = getRainLabel(rainfall);
  const mmText   = `${rainfall.toFixed(1)} mm`;

  const iconHtml = `
    <div class="cwa-map-marker rain-map-marker" title="${loc.name} 即時雨量: ${mmText} (${label})">
      <div class="marker-pill rain-pill" style="border-color:${color};">
        <span class="pill-icon">🌧️</span>
        <span class="pill-val" style="color:${color};">${mmText}</span>
        <span class="pill-name">${loc.name.slice(0,2)}</span>
      </div>
      <div class="marker-dot" style="background:${color};"></div>
    </div>`;

  const popupHtml = `
    <div class="custom-cwa-popup rain-popup">
      <div class="cwa-popup-header">
        <div class="cwa-popup-title">${loc.name} · CWA 即時降雨觀測</div>
        <span class="cwa-popup-badge" style="background:${color};">${label}</span>
      </div>
      <div class="cwa-popup-body">
        <div class="popup-metric-hero">
          <span class="hero-val" style="color:${color};">${rainfall.toFixed(1)}</span>
          <span class="hero-unit">毫米 mm</span>
        </div>
        <div class="popup-info-grid">
          <div class="info-row">
            <span class="info-label">測站名稱:</span>
            <span class="info-value"><strong>${station}</strong></span>
          </div>
          <div class="info-row">
            <span class="info-label">降雨等級:</span>
            <span class="info-value" style="color:${color}; font-weight:700;">${label}</span>
          </div>
          ${obsTemp !== null ? `
          <div class="info-row">
            <span class="info-label">測站氣溫:</span>
            <span class="info-value">${obsTemp}°C</span>
          </div>` : ""}
          ${humidity !== null ? `
          <div class="info-row">
            <span class="info-label">相對濕度:</span>
            <span class="info-value">${humidity}%</span>
          </div>` : ""}
        </div>
        <div class="popup-tip-box" style="background:#F0F9FF; border-color:#BAE6FD; color:#0369A1;">
          💡 <strong>降雨提示</strong>：${rainfall > 0 ? "外出請隨身攜帶雨具，留意路面濕滑。" : "目前測站觀測無降雨，天候良好。"}
        </div>
        ${obsTime ? `<div class="popup-time-note">中央氣象署觀測時間: ${obsTime}</div>` : ""}
      </div>
      <div class="cwa-popup-footer">
        <span class="popup-action-link" onclick="selectLocation('${loc.name}')">檢視 14 天預報數據 →</span>
      </div>
    </div>`;

  const icon = L.divIcon({ html: iconHtml, className: "", iconSize: [90, 36], iconAnchor: anchor || [45, 18] });
  const marker = L.marker(coords, { icon }).bindPopup(popupHtml, { maxWidth: 300 });
  rainLayerGroup.addLayer(marker);
}

// ── 2. Wind Layer Marker & Popup ──────────────────
function renderWindMarker(loc, coords, anchor) {
  const obs   = loc.observation || {};
  const today = (loc.forecasts && loc.forecasts[0]) ? loc.forecasts[0] : {};

  let wsMs  = (obs.windSpeed !== undefined && obs.windSpeed !== null) ? obs.windSpeed : parseWindMs(today.ws);
  let wdStr = obs.windCompass || today.wd || "-";
  if (wsMs === null) wsMs = 1.5;

  const color   = getWindColor(wsMs);
  const beaufort= getWindBeaufort(wsMs);
  const wsText  = `${wsMs.toFixed(1)} m/s`;
  const dirDeg  = compassToDeg(wdStr) ?? 45;
  const station = obs.stationName || loc.name;
  const obsTime = obs.obsTime || null;

  // Arrow points in direction of wind flow
  const iconHtml = `
    <div class="cwa-map-marker wind-map-marker" title="${loc.name} 風速: ${wsText} (${wdStr})">
      <div class="marker-pill wind-pill" style="border-color:${color};">
        <span class="wind-arrow-glyph" style="transform:rotate(${dirDeg}deg); color:${color};">➤</span>
        <span class="pill-val" style="color:${color};">${wsText}</span>
        <span class="pill-name">${loc.name.slice(0,2)}</span>
      </div>
      <div class="marker-dot" style="background:${color};"></div>
    </div>`;

  const popupHtml = `
    <div class="custom-cwa-popup wind-popup">
      <div class="cwa-popup-header">
        <div class="cwa-popup-title">${loc.name} · CWA 即時風向風速</div>
        <span class="cwa-popup-badge" style="background:${color};">${beaufort.split(" ")[0]}</span>
      </div>
      <div class="cwa-popup-body">
        <div class="popup-metric-hero" style="display:flex; align-items:center; gap:12px;">
          <div class="popup-wind-compass-circle" style="background:${color}18; border-color:${color};">
            <span class="wind-compass-arrow" style="transform:rotate(${dirDeg}deg); color:${color};">➤</span>
          </div>
          <div>
            <div class="hero-val" style="color:${color}; line-height:1;">${wsMs.toFixed(1)} <small style="font-size:14px; font-weight:600; color:#64748B;">m/s</small></div>
            <div style="font-size:13px; font-weight:700; color:#334155; margin-top:3px;">${wdStr} · ${beaufort}</div>
          </div>
        </div>
        <div class="popup-info-grid">
          <div class="info-row">
            <span class="info-label">測站名稱:</span>
            <span class="info-value"><strong>${station}</strong></span>
          </div>
          <div class="info-row">
            <span class="info-label">風向角度:</span>
            <span class="info-value">${dirDeg}° (${wdStr})</span>
          </div>
          <div class="info-row">
            <span class="info-label">蒲福等級:</span>
            <span class="info-value" style="font-weight:700; color:${color};">${beaufort}</span>
          </div>
        </div>
        <div class="popup-tip-box" style="background:#ECFDF5; border-color:#A7F3D0; color:#065F46;">
          💨 <strong>風況說明</strong>：箭頭表示風吹往之地理方位。若風力達 6 級以上強風，戶外活動與行車請多加留神。
        </div>
        ${obsTime ? `<div class="popup-time-note">中央氣象署觀測時間: ${obsTime}</div>` : ""}
      </div>
      <div class="cwa-popup-footer">
        <span class="popup-action-link" onclick="selectLocation('${loc.name}')">檢視 14 天預報數據 →</span>
      </div>
    </div>`;

  const icon = L.divIcon({ html: iconHtml, className: "", iconSize: [92, 36], iconAnchor: anchor || [46, 18] });
  const marker = L.marker(coords, { icon }).bindPopup(popupHtml, { maxWidth: 300 });
  windLayerGroup.addLayer(marker);
}

// ── 3. UV Index Layer Marker & Popup ──────────────
function renderUvMarker(loc, coords, anchor) {
  const obs   = loc.observation || {};
  const today = (loc.forecasts && loc.forecasts[0]) ? loc.forecasts[0] : {};

  // Prefer peak daytime UVI or forecast UVI
  let uvi = obs.uvIndex !== undefined && obs.uvIndex !== null ? obs.uvIndex : null;
  if (uvi === null || uvi === 0) {
    if (obs.peakUvi !== undefined && obs.peakUvi !== null && obs.peakUvi > 0) {
      uvi = obs.peakUvi;
    } else if (today.uvi !== undefined && today.uvi !== null) {
      uvi = today.uvi;
    }
  }
  if (uvi === null) uvi = 7.0;

  const color   = getUvColor(uvi);
  const level   = obs.uvLevel || today.uvLevel || getUvLevel(uvi);
  const advice  = getUvAdvice(uvi);
  const station = obs.stationName || loc.name;
  const obsTime = obs.obsTime || null;

  const iconHtml = `
    <div class="cwa-map-marker uv-map-marker" title="${loc.name} 紫外線指數: UVI ${uvi} (${level})">
      <div class="marker-pill uv-pill" style="border-color:${color};">
        <span class="pill-icon" style="color:${color};">☀️</span>
        <span class="pill-val" style="color:${color};">UVI ${uvi}</span>
        <span class="pill-name">${level.slice(0,2)}</span>
      </div>
      <div class="marker-dot uv-dot" style="background:${color};"></div>
    </div>`;

  const popupHtml = `
    <div class="custom-cwa-popup uv-popup">
      <div class="cwa-popup-header">
        <div class="cwa-popup-title">${loc.name} · CWA 紫外線指數</div>
        <span class="cwa-popup-badge" style="background:${color};">${level}</span>
      </div>
      <div class="cwa-popup-body">
        <div class="popup-metric-hero" style="display:flex; align-items:center; gap:12px;">
          <div class="popup-uv-shield" style="background:${color}20; border-color:${color};">
            <span style="font-size:24px;">☀️</span>
          </div>
          <div>
            <div class="hero-val" style="color:${color}; line-height:1;">${uvi} <small style="font-size:14px; font-weight:600; color:#64748B;">UVI</small></div>
            <div style="font-size:13px; font-weight:700; color:#334155; margin-top:3px;">${level} · WHO / CWA 標準</div>
          </div>
        </div>
        <div class="popup-info-grid">
          <div class="info-row">
            <span class="info-label">資料來源:</span>
            <span class="info-value"><strong>${station} (CWA 觀測/預報)</strong></span>
          </div>
          <div class="info-row">
            <span class="info-label">曝曬警戒:</span>
            <span class="info-value" style="font-weight:700; color:${color};">${level} (等級 ${uvi})</span>
          </div>
        </div>
        <div class="popup-tip-box" style="background:#FFFBEB; border-color:#FDE68A; color:#92400E;">
          🛡️ <strong>防曬建議</strong>：${advice}
        </div>
        ${obsTime ? `<div class="popup-time-note">中央氣象署觀測時間: ${obsTime}</div>` : ""}
      </div>
      <div class="cwa-popup-footer">
        <span class="popup-action-link" onclick="selectLocation('${loc.name}')">檢視 14 天預報數據 →</span>
      </div>
    </div>`;

  const icon = L.divIcon({ html: iconHtml, className: "", iconSize: [92, 36], iconAnchor: anchor || [46, 18] });
  const marker = L.marker(coords, { icon }).bindPopup(popupHtml, { maxWidth: 300 });
  uvLayerGroup.addLayer(marker);
}

// ── 4. Temperature Layer Marker & Popup ───────────
function renderTempMarker(loc, coords, anchor) {
  if (!loc.forecasts || !loc.forecasts.length) return;
  const today = loc.forecasts[0];
  const minT  = today.minT;
  const maxT  = today.maxT;
  const avgT  = +((minT + maxT) / 2).toFixed(1);
  const color = getTempColor(avgT);

  const iconHtml = `
    <div class="cwa-map-marker temp-map-marker" title="${loc.name} 氣溫: ${avgT}°C">
      <div class="marker-pill temp-pill" style="border-color:${color};">
        <span class="pill-icon">🌡️</span>
        <span class="pill-val" style="color:${color};">${avgT}°</span>
        <span class="pill-name">${loc.name.slice(0,2)}</span>
      </div>
      <div class="marker-dot" style="background:${color};"></div>
    </div>`;

  const popupHtml = `
    <div class="custom-cwa-popup temp-popup">
      <div class="cwa-popup-header">
        <div class="cwa-popup-title">${loc.name} · CWA 氣溫預報</div>
        <span class="cwa-popup-badge" style="background:${color};">${avgT}°C</span>
      </div>
      <div class="cwa-popup-body">
        <div class="popup-metric-hero">
          <span class="hero-val" style="color:${color};">${avgT}</span>
          <span class="hero-unit">°C</span>
        </div>
        <div class="popup-info-grid">
          <div class="info-row">
            <span class="info-label">當日最低溫:</span>
            <span class="info-value" style="color:#2563EB; font-weight:700;">${minT}°C</span>
          </div>
          <div class="info-row">
            <span class="info-label">當日最高溫:</span>
            <span class="info-value" style="color:#DC2626; font-weight:700;">${maxT}°C</span>
          </div>
        </div>
      </div>
      <div class="cwa-popup-footer">
        <span class="popup-action-link" onclick="selectLocation('${loc.name}')">檢視 14 天預報數據 →</span>
      </div>
    </div>`;

  const icon = L.divIcon({ html: iconHtml, className: "", iconSize: [84, 36], iconAnchor: anchor || [42, 18] });
  const marker = L.marker(coords, { icon }).bindPopup(popupHtml, { maxWidth: 280 });
  tempLayerGroup.addLayer(marker);
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
  const avgT  = +((today.minT + today.maxT) / 2).toFixed(1);
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

  const obs = loc.observation || {};

  // Rainfall
  const rainEl = document.getElementById("selected-rain");
  if (rainEl) {
    const rf = (obs.rainfall !== undefined && obs.rainfall !== null) ? obs.rainfall : 0.0;
    rainEl.textContent = `${rf.toFixed(1)} mm (${getRainLabel(rf)})`;
  }

  // Wind
  const windSummaryEl = document.getElementById("selected-wind-summary");
  if (windSummaryEl) {
    const ws = (obs.windSpeed !== undefined && obs.windSpeed !== null) ? `${obs.windSpeed} m/s` : (today.ws || "-");
    const wd = obs.windCompass || today.wd || "-";
    windSummaryEl.textContent = `${ws} · ${wd}`;
  }

  // UV Index
  const uvEl = document.getElementById("selected-uv");
  if (uvEl) {
    let uvi = obs.uvIndex !== undefined && obs.uvIndex !== null ? obs.uvIndex : null;
    if (uvi === null || uvi === 0) {
      if (obs.peakUvi !== undefined && obs.peakUvi !== null && obs.peakUvi > 0) uvi = obs.peakUvi;
      else if (today.uvi !== undefined && today.uvi !== null) uvi = today.uvi;
    }
    if (uvi === null) uvi = 7.0;
    const lvl = obs.uvLevel || today.uvLevel || getUvLevel(uvi);
    uvEl.textContent = `UVI ${uvi} (${lvl})`;
    uvEl.style.color = getUvColor(uvi);
  }

  // Humidity
  const rhEl = document.getElementById("selected-rh");
  if (rhEl) {
    rhEl.textContent = (obs.humidity !== null && obs.humidity !== undefined) ? `${obs.humidity}%` : "-";
  }

  // Station note
  const noteEl = document.getElementById("selected-station-note");
  if (noteEl) {
    const stn = obs.stationName || name;
    const time = obs.obsTime || "即時更新";
    noteEl.textContent = `測站: ${stn} ｜ 觀測時間: ${time} ｜ CWA 氣象署`;
  }
}

// ── Chart Tab ──────────────────────────────────────
function renderChartTab(name) {
  const loc = allLocations.find(l => l.name === name);
  if (!loc || !loc.forecasts || !loc.forecasts.length) return;

  const forecasts = loc.forecasts;

  // Update titles
  setText("chart-title", `📍 ${name} · 未來 14 天氣象走勢`);
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

  // Wind KPI
  const obs     = loc.observation || {};
  const todayWs = (obs.windSpeed !== null && obs.windSpeed !== undefined)
    ? `${obs.windSpeed} m/s` : (forecasts[0].ws || "-");
  const todayWd = obs.windCompass || forecasts[0].wd || "-";
  setText("kpi-wind", todayWs);
  setText("kpi-wind-dir", "風向: " + todayWd);

  // UV KPI
  let todayUvi = obs.uvIndex !== undefined && obs.uvIndex !== null ? obs.uvIndex : null;
  if (todayUvi === null || todayUvi === 0) {
    if (obs.peakUvi) todayUvi = obs.peakUvi;
    else if (forecasts[0].uvi) todayUvi = forecasts[0].uvi;
  }
  if (todayUvi === null) todayUvi = 7.0;
  const todayUvLevel = obs.uvLevel || forecasts[0].uvLevel || getUvLevel(todayUvi);
  const uvValEl = document.getElementById("kpi-uv");
  if (uvValEl) {
    uvValEl.textContent = `UVI ${todayUvi}`;
    uvValEl.style.color = getUvColor(todayUvi);
  }
  const uvLvlEl = document.getElementById("kpi-uv-level");
  if (uvLvlEl) {
    uvLvlEl.textContent = `等級: ${todayUvLevel}`;
    uvLvlEl.style.color = getUvColor(todayUvi);
  }

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
      const uviVal = f.uvi !== undefined && f.uvi !== null ? f.uvi : 7;
      const uviLvl = f.uvLevel || getUvLevel(uviVal);
      const uviColor = getUvColor(uviVal);
      return `<tr>
        <td><strong>${f.date}</strong></td>
        <td class="td-min">${f.minT}°C</td>
        <td class="td-max">${f.maxT}°C</td>
        <td>${avg}°C</td>
        <td><span class="wind-badge">💨 ${f.ws || "-"}</span></td>
        <td><span class="dir-badge">🧭 ${f.wd || "-"}</span></td>
        <td><span class="uv-table-badge" style="background:${uviColor}18; color:${uviColor}; border:1px solid ${uviColor}40;">☀️ UVI ${uviVal} (${uviLvl})</span></td>
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
      const curUvi = +(6.5 + ((i % 3) - 1.0) * 1.5).toFixed(1);
      forecasts.push({
        date: dateStr,
        minT: +(23 + v).toFixed(1),
        maxT: +(31 + v).toFixed(1),
        ws: "3 m/s (2級)",
        wd: "偏東風",
        uvi: curUvi,
        uvLevel: getUvLevel(curUvi)
      });
    }
    const rainVal = Math.random() < 0.25 ? +(Math.random() * 8).toFixed(1) : 0;
    const wsVal   = +(1.8 + Math.random() * 6).toFixed(1);
    const wdDirs  = ["偏北風","東北風","偏東風","東南風","偏南風","西南風","偏西風","西北風"];
    return {
      name, type, forecasts,
      observation: {
        rainfall: rainVal,
        temp: +(25 + Math.random() * 6).toFixed(1),
        humidity: Math.round(65 + Math.random() * 25),
        windSpeed: wsVal,
        windDirection: 45,
        windCompass: wdDirs[Math.floor(Math.random() * wdDirs.length)],
        uvIndex: 7.0,
        peakUvi: 7.0,
        uvLevel: "高量級",
        obsTime: null,
        stationName: name
      }
    };
  });
}

// ── Utility ────────────────────────────────────────
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// ── Weather Alerts Rendering (CWA Bulletin Format) ──
function getSeverityClass(significance) {
  const s = (significance || "").toLowerCase();
  if (s.includes("紅") || s.includes("red"))    return { bar: "severity-red",    lamp: "lamp-red",    badge: "badge-red" };
  if (s.includes("橙") || s.includes("orange")) return { bar: "severity-orange", lamp: "lamp-orange", badge: "badge-orange" };
  if (s.includes("黃") || s.includes("yellow")) return { bar: "severity-yellow", lamp: "lamp-yellow", badge: "badge-yellow" };
  return { bar: "severity-default", lamp: "lamp-default", badge: "badge-default" };
}

function renderAlerts(alerts, alertStatus) {
  const container = document.getElementById("alerts-container");
  const statusPill = document.getElementById("alert-status-pill");
  const statusDot  = document.getElementById("alert-status-dot");
  const statusText = document.getElementById("alert-status-text");

  if (!container) return;

  if (alerts && alerts.length > 0) {
    if (statusDot)  statusDot.className  = "alert-status-dot alert-active";
    if (statusText) statusText.textContent = `${alerts.length} 項特報生效`;
    if (statusPill) statusPill.className = "alert-status-pill active";

    const now = new Date().toLocaleString("zh-TW", {
      year:"numeric", month:"2-digit", day:"2-digit",
      hour:"2-digit", minute:"2-digit"
    });

    const cardsHtml = alerts.map((alert, idx) => {
      const phenomena   = alert.phenomena   || "天氣特報";
      const significance= alert.significance|| "";
      const loc         = alert.locationName|| "全台各縣市";
      const text        = alert.contentText || "";
      const sev         = getSeverityClass(significance);
      const sigLabel    = significance ? significance : "特報";
      const startFmt    = alert.startTime  ? alert.startTime.replace("T"," ").slice(0,16) : "—";
      const endFmt      = alert.endTime    ? alert.endTime.replace("T"," ").slice(0,16)   : "—";
      const bulletinNo  = `第 ${String(idx+1).padStart(2,"0")} 號公報`;

      return `
        <div class="cwa-alert-card">
          <div class="cwa-card-topbar ${sev.bar}">
            <div class="cwa-topbar-left">
              <span class="cwa-severity-lamp ${sev.lamp}"></span>
              <span class="cwa-phenomena-tag">▍${phenomena}</span>
              <span class="cwa-significance-badge ${sev.badge}">● ${sigLabel}</span>
            </div>
            <div class="cwa-topbar-right">
              <span class="cwa-bulletin-no">${bulletinNo}</span>
            </div>
          </div>
          <div class="cwa-card-body">
            <div class="cwa-card-location-row">
              <span class="cwa-location-icon">📍</span>
              <div>
                <span class="cwa-location-label">警戒地區</span>
                <div class="cwa-location-counties">${loc}</div>
              </div>
            </div>
            <hr class="cwa-card-divider">
            <div class="cwa-content-block">
              <span class="cwa-content-icon">📋</span>
              <div class="cwa-content-text-wrap">
                <span class="cwa-content-label">公報內容</span>
                <div class="cwa-content-text">${text}</div>
              </div>
            </div>
            ${(alert.startTime || alert.endTime) ? `
            <div class="cwa-card-time-row">
              <div class="cwa-time-item">
                <span class="cwa-time-label">⏱ 生效時間</span>
                <span class="cwa-time-value">${startFmt}</span>
              </div>
              <div class="cwa-time-item">
                <span class="cwa-time-label">⏹ 解除時間</span>
                <span class="cwa-time-value">${endFmt}</span>
              </div>
            </div>` : ""}
          </div>
        </div>`;
    }).join("");

    container.innerHTML = `
      <div class="cwa-bulletin-wrap">
        <div class="cwa-bulletin-masthead">
          <div class="cwa-masthead-left">
            <div class="cwa-masthead-emblem">🌀</div>
            <div class="cwa-masthead-text-wrap">
              <span class="cwa-masthead-agency">交通部中央氣象署 CWA</span>
              <div class="cwa-masthead-title">
                即時氣象特報公報
                <span class="cwa-masthead-count-badge">${alerts.length} 項警戒</span>
              </div>
            </div>
          </div>
          <div class="cwa-masthead-right">
            <span class="cwa-masthead-issue-time">監控時間：${now}</span>
            <button class="alert-toggle-btn" onclick="toggleDemoAlerts()" title="退出示範模式">
              ${isDemoAlert ? "✕ 退出示範" : "切換模式"}
            </button>
          </div>
        </div>
        <div class="cwa-bulletin-body">
          ${cardsHtml}
        </div>
      </div>`;

  } else {
    if (statusDot)  statusDot.className  = "alert-status-dot alert-clear";
    if (statusText) statusText.textContent = "特報：全台無警戒";
    if (statusPill) statusPill.className = "alert-status-pill";

    container.innerHTML = `
      <div class="alert-banner-normal">
        <div class="alert-normal-content">
          <span class="alert-normal-icon">🟢</span>
          <span><strong>氣象特報監測：</strong>中央氣象署目前未對全台各縣市發布特殊天氣警報，天候狀況正常。</span>
        </div>
        <button class="alert-demo-action-btn" onclick="toggleDemoAlerts()" title="模擬氣象特報發布時的頁面外觀">
          ⚡ 預覽示範警報公報
        </button>
      </div>`;
  }
}

// ── Nowcast Weather Messages Rendering (CWA W-C0034-001 CAP) ──
function toggleDemoNowcast() {
  isDemoNowcast = !isDemoNowcast;
  loadData();
}

function renderNowcast(nowcasts, nowcastStatus) {
  const container = document.getElementById("nowcast-container");
  const statusPill = document.getElementById("nowcast-status-pill");
  const statusDot  = document.getElementById("nowcast-status-dot");
  const statusText = document.getElementById("nowcast-status-text");

  if (!container) return;

  if (nowcasts && nowcasts.length > 0) {
    if (statusDot)  statusDot.className  = "nowcast-status-dot active";
    if (statusText) statusText.textContent = `${nowcasts.length} 則即時訊息`;
    if (statusPill) statusPill.className = "nowcast-status-pill active";

    const cardsHtml = nowcasts.map((item, idx) => {
      const event = item.event || "即時天氣訊息";
      const headline = item.headline || "";
      const effective = item.effective ? item.effective.replace("T", " ").slice(0, 16) : "";
      const expires = item.expires ? item.expires.replace("T", " ").slice(0, 16) : "";
      const sender = item.senderName || "交通部中央氣象署";

      const sectionsHtml = (item.sections && item.sections.length > 0)
        ? item.sections.map(s => `
            <div class="nowcast-section-card">
              <div class="nowcast-section-title">
                <span>📌</span>
                <span>${s.title}</span>
              </div>
              <div class="nowcast-section-val">${s.value}</div>
            </div>
          `).join("")
        : `<div class="nowcast-section-card"><div class="nowcast-section-val">詳細訊息請參閱中央氣象署官方說明。</div></div>`;

      return `
        <div class="nowcast-bulletin-wrap">
          <div class="nowcast-bulletin-header">
            <div class="nowcast-header-left">
              <span class="nowcast-event-badge">📢 ${event}</span>
              <span class="nowcast-headline-text">${headline}</span>
            </div>
            <div class="nowcast-header-right">
              ${effective ? `<span class="nowcast-time-badge">有效時間：${effective} ${expires ? '至 ' + expires : ''}</span>` : ""}
            </div>
          </div>
          <div class="nowcast-body-content">
            ${sectionsHtml}
          </div>
          <div class="nowcast-footer-info">
            <span>資料來源：${sender} ｜ 資料集：W-C0034-001 即時天氣訊息 (CAP)</span>
            <button class="nowcast-demo-btn" onclick="toggleDemoNowcast()" style="padding: 2px 8px; font-size: 11px;">
              ${isDemoNowcast ? "✕ 關閉測試" : "模擬測試"}
            </button>
          </div>
        </div>
      `;
    }).join("");

    container.innerHTML = cardsHtml;
  } else {
    if (statusDot)  statusDot.className  = "nowcast-status-dot";
    if (statusText) statusText.textContent = "即時訊息：正常";
    if (statusPill) statusPill.className = "nowcast-status-pill";

    container.innerHTML = `
      <div class="nowcast-banner-normal">
        <div class="nowcast-normal-content">
          <span class="nowcast-normal-icon">📢</span>
          <span><strong>即時天氣訊息 (Nowcast)：</strong>中央氣象署目前無突發性劇烈天氣訊息發布 (W-C0034-001 即時連線)。</span>
        </div>
        <button class="nowcast-demo-btn" onclick="toggleDemoNowcast()" title="模擬即時天氣訊息發布效果">
          ⚡ 預覽即時天氣訊息範例
        </button>
      </div>
    `;
  }
}
