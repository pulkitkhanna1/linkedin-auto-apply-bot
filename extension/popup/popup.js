/**
 * ApplyPilot AI - Extension Popup Logic
 */

document.addEventListener("DOMContentLoaded", async () => {
  const statApplied = document.getElementById("stat-applied");
  const statRecruiters = document.getElementById("stat-recruiters");
  const btnStartTab = document.getElementById("btn-start-tab");
  const btnOpenLinkedin = document.getElementById("btn-open-linkedin");
  const btnExportCsv = document.getElementById("btn-export-csv");
  const btnSettings = document.getElementById("btn-settings");

  // Load Stats
  chrome.runtime.sendMessage({ action: "GET_STATS" }, (res) => {
    if (res?.status === "success") {
      statApplied.textContent = res.applied_count || 0;
      statRecruiters.textContent = res.recruiter_count || 0;
    }
  });

  // Run on Active Tab
  btnStartTab.addEventListener("click", async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id) {
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          window.dispatchEvent(new CustomEvent("applypilot:start"));
        }
      });
      window.close();
    }
  });

  // Open LinkedIn Jobs
  btnOpenLinkedin.addEventListener("click", () => {
    chrome.tabs.create({
      url: "https://www.linkedin.com/jobs/search/?f_AL=true&keywords=Program%20Manager"
    });
    window.close();
  });

  // Open Settings
  btnSettings.addEventListener("click", () => {
    if (chrome?.runtime?.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    } else {
      window.open(chrome.runtime.getURL("options/options.html"));
    }
    window.close();
  });

  // Export CSV
  btnExportCsv.addEventListener("click", async () => {
    const data = await chrome.storage.local.get(["applied_jobs", "contacted_recruiters"]);
    const jobs = data.applied_jobs || [];

    if (jobs.length === 0) {
      alert("No applied jobs recorded yet!");
      return;
    }

    let csvContent = "data:text/csv;charset=utf-8,Title,Company,Location,URL,Applied At\n";
    jobs.forEach((j) => {
      const row = [
        `"${(j.title || "").replace(/"/g, '""')}"`,
        `"${(j.company || "").replace(/"/g, '""')}"`,
        `"${(j.location || "").replace(/"/g, '""')}"`,
        `"${(j.url || "").replace(/"/g, '""')}"`,
        `"${j.applied_at || ""}"`
      ].join(",");
      csvContent += row + "\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `applied_jobs_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });
});
