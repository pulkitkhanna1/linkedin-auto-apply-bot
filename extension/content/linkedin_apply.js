/**
 * ApplyPilot AI - LinkedIn Easy Apply Automation Engine
 * Runs natively in the LinkedIn tab, automating Easy Apply modals with Groq AI.
 */

(function () {
  let isRunning = false;
  let shouldStop = false;
  let settings = null;

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  async function loadSettings() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ action: "GET_SETTINGS" }, (res) => {
        settings = res?.settings || {};
        resolve(settings);
      });
    });
  }

  // Experience level check from job description text
  function exceedsExperienceRequirement(jobText, maxExp) {
    if (!maxExp || maxExp < 0) return false;
    const expRegex = /(\d+)\s*\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)(?:\s+of)?\s+experience/gi;
    let match;
    while ((match = expRegex.exec(jobText)) !== null) {
      const years = parseInt(match[1], 10);
      if (years > maxExp) {
        return { exceeds: true, required: years };
      }
    }
    return { exceeds: false };
  }

  // Simulate typing into form input for React
  function setNativeValue(element, value) {
    const valueSetter = Object.getOwnPropertyDescriptor(element, 'value')?.set;
    const prototype = Object.getPrototypeOf(element);
    const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;

    if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
      prototypeValueSetter.call(element, value);
    } else if (valueSetter) {
      valueSetter.call(element, value);
    } else {
      element.value = value;
    }
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }

  // Answer a specific form field
  async function fillFormField(container) {
    // 1. Text Inputs / Textarea
    const textInput = container.querySelector("input[type='text'], input[type='number'], textarea");
    if (textInput && (!textInput.value || textInput.value.trim() === "")) {
      const label = container.querySelector("label")?.innerText?.trim() ||
                    textInput.getAttribute("aria-label") || "";

      if (label) {
        const response = await new Promise((res) => {
          chrome.runtime.sendMessage(
            { action: "ANSWER_QUESTION", questionText: label, options: [], fieldType: textInput.type },
            (r) => res(r?.answer || "")
          );
        });
        if (response) {
          setNativeValue(textInput, response);
          await sleep(200);
        }
      }
    }

    // 2. Select / Dropdowns
    const select = container.querySelector("select");
    if (select && select.selectedIndex <= 0) {
      const label = container.querySelector("label")?.innerText?.trim() || "";
      const options = Array.from(select.options).map((o) => o.text.trim()).filter(Boolean);
      const answer = await new Promise((res) => {
        chrome.runtime.sendMessage(
          { action: "ANSWER_QUESTION", questionText: label, options, fieldType: "select" },
          (r) => res(r?.answer || "")
        );
      });
      if (answer) {
        const matchOpt = Array.from(select.options).find((o) =>
          o.text.toLowerCase().includes(answer.toLowerCase()) || answer.toLowerCase().includes(o.text.toLowerCase())
        );
        if (matchOpt) {
          select.value = matchOpt.value;
          select.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
    }

    // 3. Radio Buttons
    const radios = container.querySelectorAll("input[type='radio']");
    if (radios.length > 0) {
      const checked = Array.from(radios).some((r) => r.checked);
      if (!checked) {
        const legend = container.querySelector("legend, label, .fb-dash-form-element__label")?.innerText?.trim() || "";
        const options = Array.from(container.querySelectorAll("label")).map((l) => l.innerText.trim());
        const answer = await new Promise((res) => {
          chrome.runtime.sendMessage(
            { action: "ANSWER_QUESTION", questionText: legend, options, fieldType: "radio" },
            (r) => res(r?.answer || "Yes")
          );
        });
        for (const r of radios) {
          const rLabel = container.querySelector(`label[for='${r.id}']`)?.innerText?.trim() || "";
          if (rLabel.toLowerCase().includes(answer.toLowerCase()) || (answer.toLowerCase() === "yes" && rLabel.toLowerCase().includes("yes"))) {
            r.click();
            break;
          }
        }
      }
    }
  }

  // Handle Multi-Step Modal Form
  async function handleEasyApplyModal(jobTitle, companyName, jobLocation, jobUrl) {
    let stepCount = 0;
    const maxSteps = 10;

    while (stepCount < maxSteps && isRunning) {
      stepCount++;
      await sleep(1000);

      const modal = document.querySelector(".jobs-easy-apply-modal, div[data-test-modal]");
      if (!modal) break;

      // Find all form field containers
      const fieldContainers = modal.querySelectorAll(
        ".fb-dash-form-element, .jobs-easy-apply-form-section__grouping, .jobs-easy-apply-form-element"
      );
      for (const container of fieldContainers) {
        await fillFormField(container);
      }

      // Check Buttons: Submit vs Next vs Review
      const submitBtn = modal.querySelector(
        "button[aria-label*='Submit application'], button.artdeco-button--primary[data-easy-apply-next-button='false']"
      );
      const nextBtn = modal.querySelector(
        "button[aria-label*='Continue to next step'], button[aria-label*='Review your application'], button.artdeco-button--primary"
      );

      if (submitBtn && submitBtn.innerText.toLowerCase().includes("submit")) {
        window.ApplyPilotHUD?.log(`Submitting application for ${jobTitle}...`);
        if (settings.pause_before_submit) {
          window.ApplyPilotHUD?.setStatus("Paused: Review Form");
          await sleep(5000);
        }
        submitBtn.click();
        await sleep(2000);

        // Close confirmation if open
        const dismissBtn = document.querySelector("button[aria-label='Dismiss']");
        if (dismissBtn) dismissBtn.click();

        // Log success
        chrome.runtime.sendMessage({
          action: "LOG_APPLIED_JOB",
          title: jobTitle,
          company: companyName,
          location: jobLocation,
          url: jobUrl
        });

        window.ApplyPilotHUD?.increment("applied");
        window.ApplyPilotHUD?.log(`✅ Applied: ${jobTitle} @ ${companyName}`);

        // Trigger Instant Recruiter Outreach if enabled
        if (settings.auto_cold_message_recruiter && window.ApplyPilotOutreach) {
          window.ApplyPilotOutreach.triggerJobPosterOutreach(jobTitle, companyName);
        }

        return true;
      }

      if (nextBtn) {
        nextBtn.click();
        await sleep(1200);
      } else {
        // Modal stuck or completed
        break;
      }
    }
    return false;
  }

  // Main Loop
  async function startAutoApplyLoop() {
    if (isRunning) return;
    isRunning = true;
    shouldStop = false;
    await loadSettings();

    window.ApplyPilotHUD?.setStatus("Running");
    window.ApplyPilotHUD?.log("Starting LinkedIn Easy Apply scan...");

    const jobCards = Array.from(document.querySelectorAll(".job-card-container, .jobs-search-results__list-item"));
    if (jobCards.length === 0) {
      window.ApplyPilotHUD?.log("No job cards found on this page. Please navigate to LinkedIn Jobs search.");
      window.ApplyPilotHUD?.setStatus("Ready");
      isRunning = false;
      return;
    }

    let processed = 0;
    const maxJobs = settings.max_jobs_per_run || 25;

    for (const card of jobCards) {
      if (shouldStop || !isRunning) break;
      if (processed >= maxJobs) {
        window.ApplyPilotHUD?.log(`Batch limit of ${maxJobs} jobs reached.`);
        break;
      }

      // Scroll card into view and click
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      const titleLink = card.querySelector("a.job-card-list__title, a.job-card-container__link");
      const title = titleLink?.innerText?.trim() || "Target Role";
      const company = card.querySelector(".job-card-container__company-name, .artdeco-entity-lockup__subtitle")?.innerText?.trim() || "";
      const location = card.querySelector(".job-card-container__metadata-item")?.innerText?.trim() || "";
      const jobUrl = titleLink?.href || window.location.href;

      titleLink?.click();
      await sleep(1500);

      // Check job description experience requirement
      const detailsContainer = document.querySelector(".jobs-search__job-details, .jobs-description-content__text");
      const jobText = detailsContainer?.innerText || "";
      const expCheck = exceedsExperienceRequirement(jobText, settings.max_experience_target || 5);

      if (expCheck.exceeds) {
        window.ApplyPilotHUD?.increment("skipped");
        window.ApplyPilotHUD?.log(`⏩ Skipped: ${title} (Requires ${expCheck.required}y > ${settings.max_experience_target}y max)`);
        continue;
      }

      // Find Easy Apply button
      const applyBtn = document.querySelector(".jobs-apply-button--top-card button, button.jobs-apply-button");
      if (!applyBtn || !applyBtn.innerText.toLowerCase().includes("easy apply")) {
        window.ApplyPilotHUD?.increment("skipped");
        window.ApplyPilotHUD?.log(`⏩ Skipped: ${title} (External application)`);
        continue;
      }

      window.ApplyPilotHUD?.log(`Opening Easy Apply for: ${title}...`);
      applyBtn.click();
      await sleep(1500);

      const applied = await handleEasyApplyModal(title, company, location, jobUrl);
      processed++;

      const delay = (settings.delay_between_jobs || 3) * 1000;
      await sleep(delay);
    }

    window.ApplyPilotHUD?.setStatus("Completed");
    window.ApplyPilotHUD?.log("Batch completed.");
    isRunning = false;
  }

  function stopAutoApplyLoop() {
    shouldStop = true;
    isRunning = false;
    window.ApplyPilotHUD?.setStatus("Stopped");
    window.ApplyPilotHUD?.log("Automation stopped by user.");
  }

  window.addEventListener("applypilot:start", startAutoApplyLoop);
  window.addEventListener("applypilot:stop", stopAutoApplyLoop);
})();
