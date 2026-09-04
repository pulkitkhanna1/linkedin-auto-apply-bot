/**
 * ApplyPilot AI - LinkedIn Recruiter Outreach & InMail Protection Engine
 * Runs natively in LinkedIn tabs to connect with hiring managers with personalized notes.
 */

(function () {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

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

  // Extract Job Poster from Current Job Details View
  function getJobPosterInfo() {
    const posterContainer = document.querySelector(
      ".hirer-card__hirer-information, .jobs-poster__information, div[data-view-name*='job-poster']"
    );
    if (!posterContainer) return null;

    const nameEl = posterContainer.querySelector(".jobs-poster__name, a[href*='/in/'], strong");
    const name = nameEl?.innerText?.trim() || "";
    const profileUrl = posterContainer.querySelector("a[href*='/in/']")?.href || "";
    const title = posterContainer.querySelector(".hirer-card__hirer-job-title, .jobs-poster__job-title")?.innerText?.trim() || "";

    return name ? { name, profileUrl, title } : null;
  }

  // Send Connection Request with Personalized Note
  async function sendConnectionRequest(recruiterName, company, roleTitle, jobSnippet) {
    window.ApplyPilotHUD?.log(`Drafting connection note for ${recruiterName}...`);

    // 1. Generate Personalized Note via Groq AI
    const note = await new Promise((resolve) => {
      chrome.runtime.sendMessage(
        {
          action: "GENERATE_RECRUITER_NOTE",
          recruiterName,
          company,
          roleTitle,
          jobSnippet
        },
        (res) => resolve(res?.note || "")
      );
    });

    if (!note) {
      window.ApplyPilotHUD?.log(`Could not generate note for ${recruiterName}.`);
      return false;
    }

    window.ApplyPilotHUD?.log(`Drafted note (${note.length}/300 chars): "${note.slice(0, 50)}..."`);

    // 2. Find Connect Button
    const connectBtn = document.querySelector(
      "button[aria-label*='Invite'][aria-label*='to connect'], button.artdeco-button--primary:not([aria-label*='Message'])"
    );

    if (connectBtn && connectBtn.innerText.toLowerCase().includes("connect")) {
      connectBtn.click();
      await sleep(1000);

      // Click "Add a note"
      const addNoteBtn = document.querySelector("button[aria-label='Add a note'], button.artdeco-button--secondary");
      if (addNoteBtn && addNoteBtn.innerText.toLowerCase().includes("note")) {
        addNoteBtn.click();
        await sleep(800);

        const textarea = document.querySelector("textarea[name='message'], #custom-message");
        if (textarea) {
          setNativeValue(textarea, note.slice(0, 300));
          await sleep(500);

          const sendBtn = document.querySelector("button[aria-label='Send invitation'], button[aria-label='Send now'], button.artdeco-button--primary");
          if (sendBtn) {
            sendBtn.click();
            await sleep(1500);

            // Log outreach
            chrome.runtime.sendMessage({
              action: "LOG_RECRUITER_OUTREACH",
              name: recruiterName,
              company,
              role: roleTitle,
              profile_url: window.location.href,
              message: note,
              method: "Connection Note"
            });

            window.ApplyPilotHUD?.increment("messaged");
            window.ApplyPilotHUD?.log(`🤝 Connection note sent to ${recruiterName} (${company})`);
            return true;
          }
        }
      }
    }

    return false;
  }

  // Trigger outreach directly from Easy Apply completion
  async function triggerJobPosterOutreach(roleTitle, companyName) {
    const poster = getJobPosterInfo();
    if (!poster) {
      window.ApplyPilotHUD?.log(`No hiring manager card visible for ${companyName}.`);
      return;
    }

    window.ApplyPilotHUD?.log(`Found hiring team member: ${poster.name} (${poster.title})`);

    // InMail credit protection: Check if message button exists vs connect
    const messageBtn = document.querySelector("button[aria-label*='Message']");
    const isFreeMessage = messageBtn && !messageBtn.querySelector("li-icon[type='inmail'], svg[data-test-icon='inmail']");

    if (isFreeMessage) {
      window.ApplyPilotHUD?.log(`Already connected to ${poster.name}. Free direct messaging available.`);
      // Direct message flow
    } else {
      await sendConnectionRequest(poster.name, companyName, roleTitle, "");
    }
  }

  window.ApplyPilotOutreach = {
    triggerJobPosterOutreach,
    sendConnectionRequest
  };
})();
