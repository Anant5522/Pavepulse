// Interactive Midnight Blue Cyber-Themed Leaflet Hazard Map (No API Key Required!)
let map;
let markersLayer = L.layerGroup();
let heatLayer = null;
let heatmapActive = false;
let rawHazardsData = [];

const RISK_COLORS = {
  'Critical': '#ff334b',
  'High': '#fb923c',
  'Medium': '#facc15',
  'Low': '#34d399'
};

function initMap() {
  const mapElement = document.getElementById('map');
  if (!mapElement) return;

  // Default center at Greater Noida / Delhi NCR coordinates
  map = L.map('map', {
    maxZoom: 19
  }).setView([28.4744, 77.5040], 12);

  // 1. Standard Official OpenStreetMap (Leaflet.js Primary Base Layer)
  const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors | PavePulse'
  });

  // 2. High-Resolution Satellite Imagery (Optional Layer)
  const esriSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri, Maxar | PavePulse'
  });
  const esriLabels = L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19 });
  const esriRoads = L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19 });
  const satelliteLayer = L.layerGroup([esriSat, esriRoads, esriLabels]);

  // 3. Tactical Cyber Dark Map (Optional Layer)
  const darkLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    className: 'dark-tiles',
    attribution: '&copy; OpenStreetMap | PavePulse'
  });

  // Set Official OpenStreetMap as the Primary Active Layer
  streetLayer.addTo(map);

  // Layer control switcher with OpenStreetMap first
  const baseMaps = {
    "🗺️ OpenStreetMap (Default)": streetLayer,
    "🛰️ Satellite Imagery": satelliteLayer,
    "🌘 Cyber Obsidian Dark": darkLayer
  };
  L.control.layers(baseMaps, null, { position: 'topright' }).addTo(map);

  markersLayer.addTo(map);

  // Load hazards
  loadHazards();

  // Attach filter listeners
  const categoryFilter = document.getElementById('categoryFilter');
  const statusFilter = document.getElementById('statusFilter');
  const riskFilter = document.getElementById('riskFilter');

  if (categoryFilter) categoryFilter.addEventListener('change', loadHazards);
  if (statusFilter) statusFilter.addEventListener('change', loadHazards);
  if (riskFilter) riskFilter.addEventListener('change', loadHazards);

  // Setup Live Map Address Search (ArcGIS Engine)
  setupLiveMapSearch();
}

function setupLiveMapSearch() {
  const searchInput = document.getElementById('liveMapSearchInput');
  const searchBtn = document.getElementById('btnLiveMapSearch');
  const suggestionsBox = document.getElementById('liveMapSearchSuggestions');
  const feedback = document.getElementById('liveMapSearchFeedback');

  if (!searchInput || !searchBtn) return;

  let debounceTimer;

  searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    const q = e.target.value.trim();
    if (q.length < 2) {
      if (suggestionsBox) suggestionsBox.style.display = 'none';
      return;
    }
    debounceTimer = setTimeout(() => {
      searchLiveMapLocation(q);
    }, 300);
  });

  searchBtn.addEventListener('click', () => {
    searchLiveMapLocation(searchInput.value.trim(), true);
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      searchLiveMapLocation(searchInput.value.trim(), true);
    }
  });

  document.addEventListener('click', (e) => {
    if (suggestionsBox && !suggestionsBox.contains(e.target) && e.target !== searchInput) {
      suggestionsBox.style.display = 'none';
    }
  });

  async function searchLiveMapLocation(query, autoSelect) {
    if (!query) return;
    searchBtn.innerText = '...';

    try {
      const arcGisUrl = `https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?f=json&singleLine=${encodeURIComponent(query)}&countryCode=IND&maxLocations=6&outFields=Match_addr,Addr_type,DisplayX,DisplayY,PlaceName,District,Postal`;
      const res = await fetch(arcGisUrl).then(r => r.json());
      const cands = res.candidates || [];

      if (cands.length === 0) {
        if (feedback) {
          feedback.style.display = 'block';
          feedback.style.color = '#fbbf24';
          feedback.innerText = `No exact match for "${query}". Try adding city name (e.g. "${query}, Greater Noida").`;
        }
        if (suggestionsBox) suggestionsBox.style.display = 'none';
        return;
      }

      if (autoSelect && cands.length > 0) {
        selectLiveMapCand(cands[0]);
        if (suggestionsBox) suggestionsBox.style.display = 'none';
        return;
      }

      if (suggestionsBox) {
        suggestionsBox.innerHTML = '';
        cands.forEach(c => {
          const div = document.createElement('div');
          div.className = 'search-suggestion-item';
          div.style.padding = '0.65rem 1rem';
          div.style.cursor = 'pointer';
          div.style.borderBottom = '1px solid var(--border-subtle)';
          div.innerHTML = `
            <div style="font-weight:700; color:#ffffff; font-size:0.88rem;">📍 ${c.address}</div>
            <div style="font-size:0.75rem; color:#38bdf8; margin-top:2px;">Sub-Meter Pinpoint (ArcGIS)</div>
          `;
          div.addEventListener('click', () => {
            selectLiveMapCand(c);
            suggestionsBox.style.display = 'none';
          });
          suggestionsBox.appendChild(div);
        });
        suggestionsBox.style.display = 'block';
      }
    } catch (err) {
      console.error('Live map search failed:', err);
    } finally {
      searchBtn.innerText = 'Find Location';
    }
  }

  function selectLiveMapCand(c) {
    const loc = c.location || {};
    const lat = parseFloat(loc.y);
    const lon = parseFloat(loc.x);
    if (!lat || !lon) return;

    map.flyTo([lat, lon], 17, { duration: 1.5 });
    if (searchInput) searchInput.value = c.address;
    if (feedback) {
      feedback.style.display = 'block';
      feedback.style.color = '#34d399';
      feedback.innerText = `✓ Focused ${c.address} at street level (17x)!`;
      setTimeout(() => { feedback.style.display = 'none'; }, 5000);
    }
  }
}

function loadHazards() {
  const cat = document.getElementById('categoryFilter')?.value || 'all';
  const stat = document.getElementById('statusFilter')?.value || 'all';
  const risk = document.getElementById('riskFilter')?.value || 'all';

  const url = `/api/hazards?category=${encodeURIComponent(cat)}&status=${encodeURIComponent(stat)}&risk_level=${encodeURIComponent(risk)}`;

  fetch(url)
    .then(res => res.json())
    .then(data => {
      rawHazardsData = data;
      markersLayer.clearLayers();

      if (heatmapActive) {
        renderHeatmap();
      }

      if (data.length === 0) return;

      const bounds = [];

      data.forEach(item => {
        if (!item.latitude || !item.longitude) return;

        const color = RISK_COLORS[item.risk_level] || '#38bdf8';
        const isCritical = item.risk_level === 'Critical';

        // Luminous glowing marker
        const marker = L.circleMarker([item.latitude, item.longitude], {
          radius: isCritical ? 12 : 9,
          fillColor: color,
          color: '#ffffff',
          weight: 2.5,
          opacity: 1,
          fillOpacity: 0.9
        });

        // Category Emoji
        const catEmoji = {
          'pothole': '🕳️',
          'waterlogging': '🌊',
          'damaged_road': '🛣️',
          'blocked_drain': '🚧',
          'broken_streetlight': '💡',
          'damaged_sign': '🪧',
          'other': '⚠️'
        }[item.category] || '📍';

        // Popup HTML - clean, legible on OSM
        const imageTag = item.image_url
          ? `<img src="${item.image_url}" alt="${item.title}" style="width:100%; height:115px; object-fit:cover; border-radius:8px; margin-top:8px; border:1px solid rgba(255,255,255,0.15);" />`
          : '';

        const upvotesBadge = item.upvotes_count > 0
          ? `<span style="font-size:0.72rem; padding:2px 7px; border-radius:999px; background:rgba(56,189,248,0.2); color:#38bdf8; border:1px solid rgba(56,189,248,0.4);">👍 ${item.upvotes_count}</span>`
          : '';

        const recurrenceBadge = item.recurrence_count > 1
          ? `<span style="font-size:0.72rem; padding:2px 7px; border-radius:999px; background:rgba(251,146,60,0.25); color:#fb923c; border:1px solid rgba(251,146,60,0.5);">🔥 ${item.recurrence_count}x reported</span>`
          : '';

        const popupContent = `
          <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-width: 230px; max-width: 270px; color: #f0f6fc;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px; flex-wrap:wrap; gap:4px;">
              <span style="font-size:0.75rem; text-transform:uppercase; font-weight:800; color:${color}; letter-spacing:0.05em;">
                ${item.risk_level} Risk · ${item.risk_score}/100
              </span>
              <div style="display:flex; gap:4px; flex-wrap:wrap;">
                ${upvotesBadge}
                ${recurrenceBadge}
              </div>
            </div>
            <h4 style="margin:0 0 4px 0; font-size:0.98rem; font-weight:700; color:#ffffff; line-height:1.35;">${catEmoji} ${item.title}</h4>
            <p style="margin:0 0 6px 0; font-size:0.78rem; color:#94a3b8; display:flex; gap:4px; align-items:flex-start;">
              📍 <span>${item.address || 'Reported Location'}</span>
            </p>
            <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:6px;">
              <span style="padding:2px 8px; font-size:0.72rem; border-radius:4px; background:rgba(255,255,255,0.08); color:#e2e8f0; border:1px solid rgba(255,255,255,0.1);">
                ${item.status}
              </span>
              <span style="padding:2px 8px; font-size:0.72rem; border-radius:4px; background:rgba(255,255,255,0.05); color:#94a3b8;">
                ${item.category.replace('_', ' ')}
              </span>
            </div>
            ${imageTag}
            <a href="/report/${item.id}" style="display:block; text-align:center; margin-top:10px; padding:7px 12px; font-size:0.82rem; border-radius:7px; font-weight:700; text-decoration:none; color:#fff; background: linear-gradient(135deg, #2563eb, #0284c7); box-shadow: 0 4px 14px rgba(37,99,235,0.4);">
              View Full Report →
            </a>
          </div>
        `;

        marker.bindPopup(popupContent);
        markersLayer.addLayer(marker);
        bounds.push([item.latitude, item.longitude]);
      });

      if (bounds.length > 0 && !radarActive) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
      }
    })
    .catch(err => console.error('Failed to load hazards:', err));
}

// --- Live Driving Radar & Audio Proximity Scanner (Waze-style) ---
let radarActive = false;
let voiceAlertsEnabled = true;
let vehicleMarker = null;
let radarRangeCircle = null;
let simulationInterval = null;
let lastSpokenHazardId = null;

// Route simulation coordinates around Pari Chowk / Greater Noida corridor
const SIM_ROUTE = [
  { lat: 28.4705, lon: 77.5015, speed: 48, loc: "Approaching Pari Chowk South Approach" },
  { lat: 28.4720, lon: 77.5028, speed: 42, loc: "Entering Pari Chowk Underpass Merge Lane" },
  { lat: 28.4735, lon: 77.5036, speed: 32, loc: "Passing Pari Chowk Underpass" },
  { lat: 28.4744, lon: 77.5040, speed: 28, loc: "Near Critical Pothole Zone" },
  { lat: 28.4755, lon: 77.5058, speed: 40, loc: "Exiting Pari Chowk toward Alpha 1" },
  { lat: 28.4770, lon: 77.5090, speed: 38, loc: "Alpha 1 Commercial Belt Sector Road" },
  { lat: 28.4795, lon: 77.5110, speed: 45, loc: "Knowledge Park Sector Link" }
];
let simIndex = 0;

function setupDrivingRadar() {
  const btnToggle = document.getElementById('btnToggleRadar');
  const btnClose = document.getElementById('btnCloseRadar');
  const btnSim = document.getElementById('btnSimulateDrive');
  const btnVoice = document.getElementById('btnToggleVoice');
  const hudPanel = document.getElementById('radarHudPanel');

  if (!btnToggle || !hudPanel) return;

  btnToggle.addEventListener('click', () => {
    toggleRadarMode(true);
  });

  if (btnClose) {
    btnClose.addEventListener('click', () => {
      toggleRadarMode(false);
    });
  }

  if (btnVoice) {
    btnVoice.addEventListener('click', () => {
      voiceAlertsEnabled = !voiceAlertsEnabled;
      const textSpan = document.getElementById('voiceStateText');
      if (textSpan) {
        textSpan.textContent = voiceAlertsEnabled ? 'ON' : 'OFF';
        textSpan.style.color = voiceAlertsEnabled ? '#22c55e' : '#94a3b8';
      }
    });
  }

  if (btnSim) {
    btnSim.addEventListener('click', () => {
      if (simulationInterval) {
        stopSimulation();
        btnSim.textContent = "▶️ Simulate Drive (Demo)";
      } else {
        startSimulation();
        btnSim.textContent = "⏹️ Stop Simulation";
      }
    });
  }

  // Check URL param mode=radar
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('mode') === 'radar') {
    toggleRadarMode(true);
    // Auto-start simulation for convenience
    setTimeout(startSimulation, 800);
  }
}

function toggleRadarMode(active) {
  radarActive = active;
  const hudPanel = document.getElementById('radarHudPanel');
  if (!hudPanel) return;

  if (active) {
    hudPanel.style.display = 'block';
    // Initialize vehicle marker at Pari Chowk default
    updateVehiclePosition(28.4705, 77.5015, 48, "Pari Chowk Approach");
    map.setView([28.4705, 77.5015], 16);
  } else {
    hudPanel.style.display = 'none';
    stopSimulation();
    if (vehicleMarker) { map.removeLayer(vehicleMarker); vehicleMarker = null; }
    if (radarRangeCircle) { map.removeLayer(radarRangeCircle); radarRangeCircle = null; }
    const alertBanner = document.getElementById('radarAlertBanner');
    if (alertBanner) alertBanner.style.display = 'none';
  }
}

function updateVehiclePosition(lat, lon, speed, locName) {
  if (!vehicleMarker) {
    // Custom Vehicle Icon
    const carHtml = `
      <div style="width:34px; height:34px; border-radius:50%; background:#f43f5e; border:3px solid #ffffff; display:flex; align-items:center; justify-content:center; box-shadow:0 0 15px #f43f5e; color:#ffffff; font-size:16px;">
        🚗
      </div>
    `;
    const carIcon = L.divIcon({
      html: carHtml,
      className: '',
      iconSize: [34, 34],
      iconAnchor: [17, 17]
    });

    vehicleMarker = L.marker([lat, lon], { icon: carIcon, zIndexOffset: 1000 }).addTo(map);
    radarRangeCircle = L.circle([lat, lon], {
      radius: 500,
      color: '#f43f5e',
      weight: 1.5,
      dashArray: '4, 4',
      fillColor: '#f43f5e',
      fillOpacity: 0.08
    }).addTo(map);
  } else {
    vehicleMarker.setLatLng([lat, lon]);
    radarRangeCircle.setLatLng([lat, lon]);
  }

  map.panTo([lat, lon]);

  // Update telemetry display
  const speedLoc = document.getElementById('radarSpeedLocation');
  if (speedLoc) {
    speedLoc.innerHTML = `GPS Active &bull; Speed: <strong style="color:#ffffff;">${speed} km/h</strong> &bull; ${locName}`;
  }

  // Scan proximity to hazards
  scanRadarProximity(lat, lon);
}

function startSimulation() {
  simIndex = 0;
  if (simulationInterval) clearInterval(simulationInterval);

  simulationInterval = setInterval(() => {
    const step = SIM_ROUTE[simIndex];
    updateVehiclePosition(step.lat, step.lon, step.speed, step.loc);
    simIndex = (simIndex + 1) % SIM_ROUTE.length;
  }, 2200);
}

function stopSimulation() {
  if (simulationInterval) {
    clearInterval(simulationInterval);
    simulationInterval = null;
  }
}

async function scanRadarProximity(lat, lon) {
  try {
    const res = await fetch(`/api/radar/scan?lat=${lat}&lon=${lon}&radius=500`);
    const data = await res.json();

    const alertBanner = document.getElementById('radarAlertBanner');
    const alertTitle = document.getElementById('radarAlertTitle');
    const alertDesc = document.getElementById('radarAlertDesc');
    const distanceDisplay = document.getElementById('radarDistanceDisplay');

    if (data.hazards && data.hazards.length > 0) {
      const nearest = data.hazards[0];
      const dist = Math.round(nearest.distance_meters);

      if (dist <= 250) {
        if (alertBanner) alertBanner.style.display = 'block';
        if (alertTitle) alertTitle.textContent = `⚠️ ${nearest.risk_level.toUpperCase()} HAZARD DETECTED (${nearest.risk_score}/100)`;
        if (alertDesc) alertDesc.textContent = `${nearest.title} (${nearest.address})`;
        if (distanceDisplay) distanceDisplay.textContent = `${dist}m`;

        // Voice speech announcement if enabled and hasn't just spoken for this hazard
        if (voiceAlertsEnabled && window.speechSynthesis && lastSpokenHazardId !== nearest.id) {
          lastSpokenHazardId = nearest.id;
          const speech = new SpeechSynthesisUtterance(`Warning: ${nearest.category.replace('_', ' ')} ahead in ${dist} meters!`);
          speech.rate = 1.05;
          window.speechSynthesis.speak(speech);
        }
      } else {
        if (alertBanner) alertBanner.style.display = 'none';
      }
    } else {
      if (alertBanner) alertBanner.style.display = 'none';
    }
  } catch (err) {
    console.error('Radar proximity scan failed:', err);
  }
}

function renderHeatmap() {
  if (heatLayer) {
    map.removeLayer(heatLayer);
    heatLayer = null;
  }

  if (!rawHazardsData || rawHazardsData.length === 0) return;

  const heatPoints = rawHazardsData
    .filter(h => h.latitude && h.longitude)
    .map(h => {
      // Risk intensity scaled 0.3 - 1.0
      const score = typeof h.risk_score === 'number' ? h.risk_score : 50;
      const intensity = Math.min(1.0, Math.max(0.3, score / 100));
      return [h.latitude, h.longitude, intensity];
    });

  if (typeof L.heatLayer === 'function') {
    heatLayer = L.heatLayer(heatPoints, {
      radius: 30,
      blur: 20,
      maxZoom: 17,
      max: 1.0,
      minOpacity: 0.4,
      gradient: {
        0.2: '#06b6d4',
        0.4: '#38bdf8',
        0.6: '#eab308',
        0.8: '#f97316',
        1.0: '#ef4444'
      }
    }).addTo(map);
  }
}

function setupHeatmapToggle() {
  const btn = document.getElementById('btnToggleHeatmap');
  const btnText = document.getElementById('heatmapBtnText');
  if (!btn) return;

  btn.addEventListener('click', () => {
    heatmapActive = !heatmapActive;

    if (heatmapActive) {
      // Switch to Heatmap
      if (map.hasLayer(markersLayer)) {
        map.removeLayer(markersLayer);
      }
      renderHeatmap();
      if (btnText) btnText.textContent = "Pinpoint Markers View";
      btn.style.background = "rgba(56, 189, 248, 0.28)";
      btn.style.borderColor = "#38bdf8";
      btn.style.boxShadow = "0 0 15px rgba(56, 189, 248, 0.4)";
    } else {
      // Switch back to Markers
      if (heatLayer) {
        map.removeLayer(heatLayer);
        heatLayer = null;
      }
      if (!map.hasLayer(markersLayer)) {
        markersLayer.addTo(map);
      }
      if (btnText) btnText.textContent = "Density Heatmap";
      btn.style.background = "rgba(56, 189, 248, 0.12)";
      btn.style.borderColor = "rgba(56, 189, 248, 0.4)";
      btn.style.boxShadow = "none";
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  setupDrivingRadar();
  setupHeatmapToggle();
});

