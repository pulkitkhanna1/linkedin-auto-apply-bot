/**
 * ApplyPilot AI - Background Service Worker (Manifest V3)
 * Handles Groq & OpenAI LLM calls, storage management, and inter-tab communication.
 */

const DEFAULT_SETTINGS = {
  // AI Settings
  use_AI: true,
  ai_provider: "openai",
  llm_api_url: "https://api.groq.com/openai/v1",
  llm_api_key: "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",
  llm_model: "qwen/qwen3.6-27b",
  llm_temperature: 0.2,

  // Candidate Profile
  first_name: "Pulkit",
  last_name: "Khanna",
  phone_number: "7042680055",
  email: "pulkitkhanna1@gmail.com",
  current_city: "New Delhi",
  state: "Delhi",
  zipcode: "110001",
  country: "India",
  ethnicity: "Asian",
  gender: "Male",
  disability_status: "No",
  veteran_status: "No",

  // Experience & Preferences
  years_of_experience: "2",
  max_experience_target: 5,
  require_visa: "Yes",
  us_citizenship: "Non-citizen seeking work authorization",
  desired_salary: "150000",
  current_ctc: "20000",
  notice_period: "60",
  recent_employer: "Pocket FM",
  linkedin_headline: "Program Manager @ Pocket FM | ex-Bain & Co | Growth Strategy & Product",
  linkedin_summary: "Program & Growth Manager who scaled a U.S. vertical from $80M to $120M ARR while independently managing $1.5M+ in monthly ad spend at Pocket FM. Combines operating experience with Bain consulting rigor and D2C founder background. Strong at funnel optimization, performance marketing, cross-functional program leadership, and AI-driven content production.",

  // Automation Toggles
  auto_cold_message_recruiter: true,
  protect_inmail_credits: true,
  extract_recruiter_email: true,
  pause_before_submit: false,
  pause_at_failed_question: false,
  max_jobs_per_run: 25,
  delay_between_jobs: 3
};

// Initialize default storage on install
chrome.runtime.onInstalled.addListener(async () => {
  const existing = await chrome.storage.local.get("settings");
  if (!existing.settings) {
    await chrome.storage.local.set({ settings: DEFAULT_SETTINGS });
  }
  const history = await chrome.storage.local.get(["applied_jobs", "contacted_recruiters"]);
  if (!history.applied_jobs) {
    await chrome.storage.local.set({ applied_jobs: [] });
  }
  if (!history.contacted_recruiters) {
    await chrome.storage.local.set({ contacted_recruiters: [] });
  }
  console.log("ApplyPilot AI extension installed and storage initialized.");
});

// Helper: Call LLM API (Groq / OpenAI compatible)
async function callLLM(prompt, systemInstruction = "You are an expert executive job application assistant.") {
  const { settings } = await chrome.storage.local.get("settings");
  const cfg = { ...DEFAULT_SETTINGS, ...(settings || {}) };

  if (!cfg.use_AI || !cfg.llm_api_key) {
    throw new Error("AI is disabled or API key is missing. Please configure in extension settings.");
  }

  const endpoint = cfg.llm_api_url.replace(/\/+$/, "") + "/chat/completions";
  const body = {
    model: cfg.llm_model || "qwen/qwen3.6-27b",
    messages: [
      { role: "system", content: systemInstruction },
      { role: "user", content: prompt }
    ],
    temperature: cfg.llm_temperature ?? 0.2
  };

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${cfg.llm_api_key.trim()}`
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`AI API request failed (${response.status}): ${errorText}`);
  }

  const data = await response.json();
  return data.choices?.[0]?.message?.content?.trim() || "";
}

// Generate Personalized Recruiter Note (Strictly <= 300 characters)
async function generateRecruiterNote(recruiterName, company, roleTitle, jobSnippet = "") {
  const { settings } = await chrome.storage.local.get("settings");
  const cfg = { ...DEFAULT_SETTINGS, ...(settings || {}) };

  const systemInstruction = `You are a world-class executive talent outreach specialist.
Your goal is to write a concise, compelling LinkedIn connection request note for a hiring manager or recruiter.
CRITICAL CONSTRAINT: The final output MUST BE STRICTLY UNDER 300 CHARACTERS including spaces, names, and punctuation.`;

  const prompt = `Candidate Profile:
- Name: ${cfg.first_name} ${cfg.last_name}
- Headline: ${cfg.linkedin_headline}
- Key Highlights: ${cfg.linkedin_summary}

Target Recruiter / Hiring Manager:
- Name: ${recruiterName || "Hiring Team"}
- Company: ${company || "your team"}
- Role: ${roleTitle || "this role"}
- Context: ${jobSnippet}

Instructions:
1. Write a direct, warm, high-converting LinkedIn note.
2. Mention 1 key metric (e.g., scaled US vertical $80M->$120M ARR, ex-Bain).
3. Express enthusiasm for ${company || "the company"}.
4. Sign off with "- ${cfg.first_name}".
5. Output ONLY the plain text note. Do NOT include quotes, explanations, or word counts.
6. MUST BE UNDER 300 CHARACTERS.`;

  let note = await callLLM(prompt, systemInstruction);
  note = note.replace(/^["']|["']$/g, "").trim();

  // Enforce 300 character safety margin
  if (note.length > 300) {
    const fallback = `Hi ${recruiterName || "there"}, I'm ${cfg.first_name}, a Program Manager at Pocket FM where I scaled US ARR from $80M to $120M (ex-Bain). I'd love to connect and bring my growth expertise to ${company || "your team"}! - ${cfg.first_name}`;
    note = fallback.slice(0, 300);
  }

  return note;
}

// Answer Application Question
async function answerApplicationQuestion(questionText, options = [], fieldType = "text") {
  const { settings } = await chrome.storage.local.get("settings");
  const cfg = { ...DEFAULT_SETTINGS, ...(settings || {}) };

  // Rule-based fast paths
  const qLower = questionText.toLowerCase();
  if (qLower.includes("visa") || qLower.includes("sponsorship")) {
    return cfg.require_visa || "Yes";
  }
  if (qLower.includes("authorized") || qLower.includes("work authorization")) {
    return "Yes";
  }
  if (qLower.includes("years of experience") || qLower.includes("how many years")) {
    return cfg.years_of_experience || "2";
  }
  if (qLower.includes("salary") || qLower.includes("compensation")) {
    return cfg.desired_salary || "150000";
  }
  if (qLower.includes("notice period")) {
    return cfg.notice_period || "60";
  }
  if (qLower.includes("city") || qLower.includes("location")) {
    return cfg.current_city || "New Delhi";
  }

  // LLM fallback for nuanced / custom questions
  const systemInstruction = `You are an AI assistant answering job application form fields on behalf of the candidate.
Return ONLY the exact answer string with no extra explanation. If options are provided, select the single best matching option.`;

  const prompt = `Candidate Information:
- Name: ${cfg.first_name} ${cfg.last_name}
- Total Experience: ${cfg.years_of_experience} years
- Recent Employer: ${cfg.recent_employer}
- Headline: ${cfg.linkedin_headline}
- Summary: ${cfg.linkedin_summary}
- Phone: ${cfg.phone_number}
- Email: ${cfg.email}
- Location: ${cfg.current_city}, ${cfg.state}, ${cfg.country}
- Visa Required: ${cfg.require_visa}
- Desired Salary: $${cfg.desired_salary}

Question: "${questionText}"
${options.length > 0 ? `Available Options: [${options.map(o => `"${o}"`).join(", ")}]` : ""}
Field Type: ${fieldType}

Output format: Return ONLY the exact answer to fill into this field.`;

  let answer = await callLLM(prompt, systemInstruction);
  answer = answer.replace(/^["']|["']$/g, "").trim();
  return answer;
}

// Message Dispatcher
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GET_SETTINGS") {
    chrome.storage.local.get("settings").then(data => {
      sendResponse({ status: "success", settings: { ...DEFAULT_SETTINGS, ...(data.settings || {}) } });
    });
    return true;
  }

  if (request.action === "SAVE_SETTINGS") {
    chrome.storage.local.set({ settings: request.settings }).then(() => {
      sendResponse({ status: "success" });
    });
    return true;
  }

  if (request.action === "GENERATE_RECRUITER_NOTE") {
    generateRecruiterNote(request.recruiterName, request.company, request.roleTitle, request.jobSnippet)
      .then(note => sendResponse({ status: "success", note }))
      .catch(err => sendResponse({ status: "error", message: err.message }));
    return true;
  }

  if (request.action === "ANSWER_QUESTION") {
    answerApplicationQuestion(request.questionText, request.options, request.fieldType)
      .then(answer => sendResponse({ status: "success", answer }))
      .catch(err => sendResponse({ status: "error", message: err.message }));
    return true;
  }

  if (request.action === "LOG_APPLIED_JOB") {
    chrome.storage.local.get("applied_jobs").then(data => {
      const list = data.applied_jobs || [];
      list.unshift({
        title: request.title,
        company: request.company,
        location: request.location,
        url: request.url,
        applied_at: new Date().toISOString()
      });
      chrome.storage.local.set({ applied_jobs: list.slice(0, 1000) });
      sendResponse({ status: "success", count: list.length });
    });
    return true;
  }

  if (request.action === "LOG_RECRUITER_OUTREACH") {
    chrome.storage.local.get("contacted_recruiters").then(data => {
      const list = data.contacted_recruiters || [];
      list.unshift({
        name: request.name,
        company: request.company,
        role: request.role,
        profile_url: request.profile_url,
        email: request.email || "",
        message: request.message,
        method: request.method,
        contacted_at: new Date().toISOString()
      });
      chrome.storage.local.set({ contacted_recruiters: list.slice(0, 1000) });
      sendResponse({ status: "success", count: list.length });
    });
    return true;
  }

  if (request.action === "GET_STATS") {
    Promise.all([
      chrome.storage.local.get("applied_jobs"),
      chrome.storage.local.get("contacted_recruiters")
    ]).then(([jobs, recruiters]) => {
      sendResponse({
        status: "success",
        applied_count: (jobs.applied_jobs || []).length,
        recruiter_count: (recruiters.contacted_recruiters || []).length
      });
    });
    return true;
  }
});
