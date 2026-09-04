/**
 * ApplyPilot AI - Google Forms Auto-Filler Engine
 * Automatically analyzes Google Form fields and fills them using candidate profile + Groq AI.
 */

(function () {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function setNativeValue(element, value) {
    element.value = value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function processGoogleForm() {
    window.ApplyPilotHUD?.setStatus("Analyzing Form");
    window.ApplyPilotHUD?.log("Scanning Google Form questions...");

    // Find all question blocks in Google Forms
    const questionBlocks = Array.from(
      document.querySelectorAll("div[role='listitem'], div[jsmodel='CP1oW']")
    );

    if (questionBlocks.length === 0) {
      window.ApplyPilotHUD?.log("No Google Form questions found on this page.");
      window.ApplyPilotHUD?.setStatus("Ready");
      return;
    }

    let filledCount = 0;

    for (const block of questionBlocks) {
      const titleEl = block.querySelector("div[role='heading'], span.M7eMe, .HoXoMd");
      const questionTitle = titleEl?.innerText?.replace(/\s*\*\s*$/, "").trim() || "";

      if (!questionTitle) continue;

      // 1. Text Inputs (Short answer or Paragraph)
      const input = block.querySelector("input[type='text'], input[type='email'], input[type='tel'], input[type='number']");
      const textarea = block.querySelector("textarea");

      if (input && !input.value) {
        window.ApplyPilotHUD?.log(`Answering: "${questionTitle.slice(0, 30)}..."`);
        const answer = await new Promise((res) => {
          chrome.runtime.sendMessage(
            { action: "ANSWER_QUESTION", questionText: questionTitle, options: [], fieldType: "text" },
            (r) => res(r?.answer || "")
          );
        });
        if (answer) {
          setNativeValue(input, answer);
          filledCount++;
          await sleep(200);
        }
      } else if (textarea && !textarea.value) {
        window.ApplyPilotHUD?.log(`Answering: "${questionTitle.slice(0, 30)}..."`);
        const answer = await new Promise((res) => {
          chrome.runtime.sendMessage(
            { action: "ANSWER_QUESTION", questionText: questionTitle, options: [], fieldType: "textarea" },
            (r) => res(r?.answer || "")
          );
        });
        if (answer) {
          setNativeValue(textarea, answer);
          filledCount++;
          await sleep(200);
        }
      }

      // 2. Radio Groups (Multiple Choice)
      const radios = block.querySelectorAll("div[role='radio']");
      if (radios.length > 0) {
        const isChecked = Array.from(radios).some((r) => r.getAttribute("aria-checked") === "true");
        if (!isChecked) {
          const options = Array.from(radios).map((r) => r.getAttribute("data-value") || r.innerText.trim());
          const answer = await new Promise((res) => {
            chrome.runtime.sendMessage(
              { action: "ANSWER_QUESTION", questionText: questionTitle, options, fieldType: "radio" },
              (r) => res(r?.answer || "")
            );
          });
          if (answer) {
            for (const r of radios) {
              const val = r.getAttribute("data-value") || r.innerText.trim();
              if (val.toLowerCase().includes(answer.toLowerCase()) || answer.toLowerCase().includes(val.toLowerCase())) {
                r.click();
                filledCount++;
                break;
              }
            }
          }
        }
      }

      // 3. Checkboxes
      const checkboxes = block.querySelectorAll("div[role='checkbox']");
      if (checkboxes.length > 0) {
        const isChecked = Array.from(checkboxes).some((c) => c.getAttribute("aria-checked") === "true");
        if (!isChecked) {
          const options = Array.from(checkboxes).map((c) => c.getAttribute("data-value") || c.innerText.trim());
          const answer = await new Promise((res) => {
            chrome.runtime.sendMessage(
              { action: "ANSWER_QUESTION", questionText: questionTitle, options, fieldType: "checkbox" },
              (r) => res(r?.answer || "")
            );
          });
          if (answer) {
            for (const c of checkboxes) {
              const val = c.getAttribute("data-value") || c.innerText.trim();
              if (val.toLowerCase().includes(answer.toLowerCase()) || answer.toLowerCase().includes(val.toLowerCase())) {
                c.click();
                filledCount++;
                break;
              }
            }
          }
        }
      }
    }

    window.ApplyPilotHUD?.increment("applied");
    window.ApplyPilotHUD?.setStatus("Form Filled");
    window.ApplyPilotHUD?.log(`✅ Completed ${filledCount} field(s). Review and click Submit!`);
  }

  window.addEventListener("applypilot:start", processGoogleForm);
})();
