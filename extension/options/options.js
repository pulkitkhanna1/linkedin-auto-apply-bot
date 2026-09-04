/**
 * ApplyPilot AI - Options / Settings Management
 */

const FIELDS = [
  "llm_api_key",
  "llm_model",
  "llm_api_url",
  "first_name",
  "last_name",
  "email",
  "phone_number",
  "current_city",
  "state",
  "country",
  "years_of_experience",
  "max_experience_target",
  "require_visa",
  "desired_salary",
  "recent_employer",
  "linkedin_headline",
  "linkedin_summary"
];

const CHECKBOX_FIELDS = [
  "auto_cold_message_recruiter",
  "protect_inmail_credits",
  "pause_before_submit"
];

function showToast(msg = "Settings saved successfully!") {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}

async function loadSettings() {
  chrome.runtime.sendMessage({ action: "GET_SETTINGS" }, (res) => {
    const s = res?.settings || {};
    FIELDS.forEach((f) => {
      const el = document.getElementById(f);
      if (el && s[f] !== undefined) {
        el.value = s[f];
      }
    });
    CHECKBOX_FIELDS.forEach((f) => {
      const el = document.getElementById(f);
      if (el && s[f] !== undefined) {
        el.checked = Boolean(s[f]);
      }
    });
  });
}

async function saveSettings() {
  const settings = {};
  FIELDS.forEach((f) => {
    const el = document.getElementById(f);
    if (el) {
      settings[f] = el.value.trim();
    }
  });
  CHECKBOX_FIELDS.forEach((f) => {
    const el = document.getElementById(f);
    if (el) {
      settings[f] = el.checked;
    }
  });

  chrome.runtime.sendMessage({ action: "SAVE_SETTINGS", settings }, (res) => {
    if (res?.status === "success") {
      showToast();
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  document.getElementById("btn-save-top").addEventListener("click", saveSettings);
  document.getElementById("btn-save-bottom").addEventListener("click", saveSettings);
});
