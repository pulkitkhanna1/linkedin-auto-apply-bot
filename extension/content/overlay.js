/**
 * ApplyPilot AI - Floating HUD Controller
 * Injects a floating control pill into LinkedIn and Google Forms tabs.
 */

(function () {
  if (document.getElementById("applypilot-hud")) return;

  const hud = document.createElement("div");
  hud.id = "applypilot-hud";
  hud.innerHTML = `
    <div id="applypilot-hud-header">
      <div id="applypilot-hud-brand">
        <span>🚀</span>
        <span>ApplyPilot AI</span>
      </div>
      <div id="applypilot-hud-status-badge">
        <span class="status-dot"></span>
        <span id="hud-status-text">Ready</span>
      </div>
    </div>
    <div id="applypilot-hud-body">
      <div class="applypilot-stat-grid">
        <div class="applypilot-stat-card">
          <div class="applypilot-stat-val" id="hud-stat-applied">0</div>
          <div class="applypilot-stat-label">Applied</div>
        </div>
        <div class="applypilot-stat-card">
          <div class="applypilot-stat-val" id="hud-stat-messaged">0</div>
          <div class="applypilot-stat-label">Outreach</div>
        </div>
        <div class="applypilot-stat-card">
          <div class="applypilot-stat-val" id="hud-stat-skipped">0</div>
          <div class="applypilot-stat-label">Skipped</div>
        </div>
      </div>
      <div id="applypilot-hud-log">Ready. Click Start to begin auto-applying.</div>
      <div class="applypilot-btn-group">
        <button class="applypilot-btn applypilot-btn-primary" id="hud-btn-start">
          ▶ Start
        </button>
        <button class="applypilot-btn applypilot-btn-danger" id="hud-btn-stop" style="display: none;">
          ⏹ Stop
        </button>
        <button class="applypilot-btn applypilot-btn-secondary" id="hud-btn-options">
          ⚙️ Settings
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(hud);

  // State management
  let stats = { applied: 0, messaged: 0, skipped: 0 };
  let isRunning = false;

  const statusText = document.getElementById("hud-status-text");
  const statusBadge = document.getElementById("applypilot-hud-status-badge");
  const logBox = document.getElementById("applypilot-hud-log");
  const btnStart = document.getElementById("hud-btn-start");
  const btnStop = document.getElementById("hud-btn-stop");
  const btnOptions = document.getElementById("hud-btn-options");

  window.ApplyPilotHUD = {
    setStatus(status) {
      statusText.textContent = status;
      statusBadge.className = ``;
      if (status.toLowerCase().includes("running") || status.toLowerCase().includes("applying")) {
        statusBadge.classList.add("running");
        isRunning = true;
        btnStart.style.display = "none";
        btnStop.style.display = "inline-flex";
      } else if (status.toLowerCase().includes("paused")) {
        statusBadge.classList.add("paused");
      } else {
        isRunning = false;
        btnStart.style.display = "inline-flex";
        btnStop.style.display = "none";
      }
    },

    log(msg) {
      const line = `[${new Date().toLocaleTimeString()}] ${msg}`;
      logBox.textContent = line;
      console.log(`[ApplyPilot AI] ${msg}`);
    },

    increment(key) {
      if (stats[key] !== undefined) {
        stats[key]++;
        const el = document.getElementById(`hud-stat-${key}`);
        if (el) el.textContent = stats[key];
      }
    },

    get isRunning() {
      return isRunning;
    }
  };

  btnStart.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent("applypilot:start"));
  });

  btnStop.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent("applypilot:stop"));
  });

  btnOptions.addEventListener("click", () => {
    if (chrome?.runtime?.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    } else {
      window.open(chrome.runtime.getURL("options/options.html"));
    }
  });
})();
