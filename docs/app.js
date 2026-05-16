/* ============================================================
   Data
   ============================================================ */

const tutorials = [
  {
    title: "1. Clone and install",
    tags: ["Python 3.11+", "Virtualenv", "Requirements"],
    summary: "Prepare the local environment and install runtime dependencies before touching credentials.",
    steps: [
      "Clone the repo and enter the project directory.",
      "Create a virtual environment: <code>python -m venv .venv</code>.",
      "Install runtime packages: <code>pip install -r requirements.txt</code>.",
      "For development (linting + type checking): <code>pip install -r requirements-dev.txt</code>."
    ]
  },
  {
    title: "2. Connect Google services",
    tags: ["Sheets API", "Drive API", "OAuth2"],
    summary: "Create service-account access for Sheets and OAuth2 user credentials for Drive uploads.",
    steps: [
      "Enable Google Sheets API and Google Drive API in one Google Cloud project.",
      "Create service account, download JSON key, copy full JSON into <code>GOOGLE_SERVICE_ACCOUNT</code>.",
      "Create desktop OAuth client, run refresh-token script, save printed <code>GOOGLE_OAUTH_*</code> values.",
      "Share the spreadsheet with the service-account email (Editor access)."
    ]
  },
  {
    title: "3. Prepare spreadsheet and resumes",
    tags: ["Sheet Schema", "PDF Intake", "Resume Types"],
    summary: "Match input sheet columns and supply compact text profiles — from a PDF or written by hand.",
    steps: [
      "Create spreadsheet headers: <code>status</code>, <code>company</code>, <code>role</code>, <code>job_id</code>, <code>link</code>, <code>description</code>, <code>job_full_desc</code>, <code>resume_type</code>, and the four <code>will_ai_generate_*</code> columns.",
      "If <code>job_full_desc</code> has 20+ words, automation uses it directly and skips scraping.",
      "Use <code>yes</code> or <code>no</code> in AI output columns. Blank defaults to <code>yes</code>.",
      "Resume profiles — two options: (A) place PDFs in <code>raw_resumes/</code> and run <code>python scripts/process_resume.py</code>; or (B) write a compact plain-text summary yourself.",
      "Paste each profile's text into a GitHub Variable: <code>RESUME_DEFAULT</code>, <code>RESUME_BACKEND</code>, etc."
    ]
  },
  {
    title: "4. Run automation locally",
    tags: ["dotenv", "Main Entrypoint", "Logs"],
    summary: "Validate the full pipeline locally before relying on the scheduled automation.",
    steps: [
      "Copy <code>example.env</code> to <code>.env</code> and fill in required values.",
      "Run <code>python main.py</code>.",
      "Inspect generated files under <code>output/</code> and logs under <code>logs/</code>."
    ]
  },
  {
    title: "5. Ship daily automation",
    tags: ["GitHub Actions", "Secrets", "Artifacts"],
    summary: "Move a working local setup into GitHub Actions so jobs process on schedule.",
    steps: [
      "Push project to GitHub. If using a fork, keep <code>origin</code> on your fork and add <code>FahimFBA/applyforge</code> as <code>upstream</code>.",
      "Add required secrets: <code>OPENAI_API_KEY</code>, <code>GOOGLE_SERVICE_ACCOUNT</code>, and OAuth values.",
      "Add variables: <code>GOOGLE_SHEET_ID</code>, <code>GOOGLE_DRIVE_FOLDER_ID</code>, <code>OPENAI_MODEL</code>, <code>MAX_JOBS_PER_RUN</code>, and <code>RESUME_DEFAULT</code>.",
      "Add one repository variable per resume type as <code>RESUME_&lt;TYPE&gt;</code>. Workflow exports every <code>RESUME_*</code> variable automatically.",
      "Optionally override any built-in AI prompt by adding a <code>PROMPT_*</code> variable — see README for required placeholders.",
      "Trigger a manual run from the Actions UI before relying on cron."
    ]
  },
  {
    title: "6. Tune cost and reliability",
    tags: ["Rate Limits", "Retries", "Token Budget", "CI"],
    summary: "Use compact profiles, capped max jobs, and retry knobs to keep runs stable and cheap.",
    steps: [
      "Leave <code>gpt-4o-mini</code> as the default unless output quality proves insufficient.",
      "Resume profile is embedded in the system prompt — OpenAI's automatic caching kicks in from call 2 onward, saving ~50% on profile tokens per run.",
      "Increase <code>RATE_LIMIT_DELAY</code> or reduce <code>MAX_JOBS_PER_RUN</code> if rate limits appear.",
      "Pre-fill <code>description</code> in the spreadsheet for job boards that block scraping.",
      "CI runs <code>ruff check</code> + all unit tests on every push — zero configuration needed."
    ]
  }
];

const workflow = [
  {
    title: "Fetch pending jobs",
    body: "Rows with <code>status = not applied</code> loaded from Google Sheets.",
    icon: "📋"
  },
  {
    title: "Resolve job context",
    body: "Use sheet description when present; scrape from link when missing.",
    icon: "🔍"
  },
  {
    title: "Generate tailored drafts",
    body: "Load matching resume profile, embed in system prompt for cache hits, then generate only row-enabled documents with OpenAI.",
    icon: "✨"
  },
  {
    title: "Write output files",
    body: "Save only requested Markdown and/or DOCX variants for recruiter email and cover letter.",
    icon: "📄"
  },
  {
    title: "Upload and mark done",
    body: "Push files to Google Drive and update sheet status to <code>draft generated</code>.",
    icon: "☁️"
  }
];

const configItems = [
  {
    name: "OPENAI_API_KEY",
    detail: "Required. Auth for content generation."
  },
  {
    name: "GOOGLE_SERVICE_ACCOUNT",
    detail: "Required. Full service-account JSON string for Sheets access."
  },
  {
    name: "GOOGLE_OAUTH_REFRESH_TOKEN",
    detail: "Required for personal Drive uploads. Used alongside OAuth client ID and secret."
  },
  {
    name: "GOOGLE_SHEET_ID",
    detail: "Required. Spreadsheet ID from the URL: <code>docs.google.com/spreadsheets/d/&lt;ID&gt;/edit</code>"
  },
  {
    name: "GOOGLE_DRIVE_FOLDER_ID",
    detail: "Recommended. Target Drive folder ID from the URL."
  },
  {
    name: "OPENAI_MODEL",
    detail: "Default <code>gpt-4o-mini</code>. Change only if quality or policy needs differ."
  },
  {
    name: "MAX_JOBS_PER_RUN",
    detail: "Default <code>10</code>. Caps API usage and run duration per schedule trigger."
  },
  {
    name: "RESUME_DEFAULT",
    detail: "Required. Processed resume profile text — fallback for all resume types."
  },
  {
    name: "RESUME_BACKEND / RESUME_AI / RESUME_&lt;TYPE&gt;",
    detail: "Optional. Add one per <code>resume_type</code> value in your sheet. Workflow exports every <code>RESUME_*</code> variable automatically — no YAML edits needed."
  },
  {
    name: "PROMPT_COVER_LETTER_SYSTEM / PROMPT_COVER_LETTER_USER",
    detail: "Optional. Override built-in cover letter prompts. <code>_SYSTEM</code> must contain <code>{resume_profile}</code> (cached by OpenAI); <code>_USER</code> must contain <code>{company}</code>, <code>{role}</code>, <code>{job_description}</code>."
  },
  {
    name: "PROMPT_RECRUITER_EMAIL_SYSTEM / PROMPT_RECRUITER_EMAIL_USER",
    detail: "Optional. Override built-in recruiter email prompts. Same placeholder rules as cover letter pair."
  },
  {
    name: "PROMPT_RESUME_OPTIMIZER_SYSTEM / PROMPT_RESUME_OPTIMIZER_USER",
    detail: "Optional. Override resume optimizer prompts used by <code>scripts/process_resume.py</code>. <code>_USER</code> must contain <code>{resume_text}</code>."
  }
];

const statuses = [
  {
    name: "not applied",
    detail: "Ready for automation pickup.",
    dotClass: "status-dot-active"
  },
  {
    name: "processing",
    detail: "Current run has claimed the row.",
    dotClass: "status-dot-processing"
  },
  {
    name: "draft generated",
    detail: "Outputs created and uploaded to Drive.",
    dotClass: "status-dot-done"
  },
  {
    name: "reviewed",
    detail: "Human reviewed and approved the draft.",
    dotClass: "status-dot-human"
  },
  {
    name: "applied",
    detail: "Application submitted manually.",
    dotClass: "status-dot-applied"
  },
  {
    name: "failed",
    detail: "Job processing broke — check logs and set back to not applied to retry.",
    dotClass: "status-dot-failed"
  }
];

const directories = [
  {
    name: ".github/workflows/",
    detail: "Scheduled automation (<code>automation.yml</code>), CI lint + test (<code>ci.yml</code>), docs deployment, and release workflow."
  },
  {
    name: "services/",
    detail: "Config, logging, Sheets, Drive, scraping, OpenAI, doc generation, prompts."
  },
  {
    name: "services/prompts.py",
    detail: "All AI prompt templates. Resume profile is embedded in system prompts for OpenAI cache hits. Override via <code>PROMPT_*</code> GitHub Variables."
  },
  {
    name: "utils/constants.py",
    detail: "Single source of truth for status strings, column names, flag values, and processing thresholds. Imported by <code>services/config.py</code>, <code>services/sheets.py</code>, and <code>main.py</code>."
  },
  {
    name: "scripts/",
    detail: "One-time helpers for resume PDF processing and OAuth2 refresh token generation."
  },
  {
    name: "resumes/",
    detail: "Local .txt profiles for dev fallback only (gitignored). Set as GitHub Variables at runtime."
  },
  {
    name: "output/ and logs/",
    detail: "Generated artifacts and automation logs (gitignored; also uploaded as Actions artifacts)."
  }
];

const tests = [
  {
    name: "test_config.py",
    detail: "Required env validation, auto-created directories, <code>get_config()</code> singleton behavior."
  },
  {
    name: "test_document_generator.py",
    detail: "Output path sanitizing, Markdown writes, DOCX generation behavior."
  },
  {
    name: "test_resume_optimizer.py",
    detail: "PDF text cleanup, fallback profile loading, empty-profile guards."
  },
  {
    name: "test_main.py",
    detail: "Per-job orchestration, <code>job_full_desc</code> bypass, scraping fallback, and output-toggle logic."
  },
  {
    name: "test_sheets.py",
    detail: "Spreadsheet row parsing and blank <code>yes</code>/<code>no</code> defaults."
  }
];

const commands = [
  {
    title: "Create env + install",
    body: "First local bootstrap — runtime deps only.",
    command: "python -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt"
  },
  {
    title: "Install dev dependencies",
    body: "Adds ruff linter and mypy type checker.",
    command: "pip install -r requirements-dev.txt"
  },
  {
    title: "Lint with ruff",
    body: "Run the full linter. CI runs this automatically.",
    command: "ruff check .\n# Auto-fix safe issues:\nruff check --fix ."
  },
  {
    title: "Generate OAuth refresh token",
    body: "One-time Google Drive auth setup.",
    command: "python scripts/generate_refresh_token.py"
  },
  {
    title: "Preprocess resume PDFs",
    body: "Turn raw PDFs into compact text profiles.",
    command: "python scripts/process_resume.py"
  },
  {
    title: "Run main automation",
    body: "Local end-to-end execution.",
    command: "python main.py"
  },
  {
    title: "Run tests",
    body: "Full unit test suite (17 tests).",
    command: "python -m unittest discover -s tests -v"
  },
  {
    title: "Preview docs locally",
    body: "Serve the docs site at localhost:8000.",
    command: "python -m http.server 8000 -d docs"
  },
  {
    title: "Run via Docker Compose",
    body: "Run automation in Docker with volume-mounted output.",
    command: "docker compose up"
  }
];

/* ============================================================
   Render functions
   ============================================================ */

function renderWhatsNew() {
  const banner = document.getElementById("whats-new-banner");
  if (!banner) return;
  banner.innerHTML = `
    <span class="whats-new-badge">v1.14.0</span>
    <p class="whats-new-text">
      <strong>What's new:</strong>
      Global docs navbar in <code>navbar.js</code> ·
      Full guide page with search overlay in <code>readme.html</code> ·
      Mobile topbar overflow fix on docs pages ·
      README and docs content refreshed for v1.14.0
    </p>
  `;
}

function renderTutorials() {
  const root = document.getElementById("tutorial-grid");
  if (!root) return;

  tutorials.forEach((tutorial, index) => {
    const article = document.createElement("article");
    article.className = "tutorial-card reveal";
    article.style.transitionDelay = `${index * 0.07}s`;
    article.innerHTML = `
      <span class="tutorial-index">${String(index + 1).padStart(2, "0")}</span>
      <div>
        <h3>${tutorial.title}</h3>
        <p>${tutorial.summary}</p>
      </div>
      <div class="pill-row">
        ${tutorial.tags.map((tag) => `<span class="pill">${tag}</span>`).join("")}
      </div>
      <ol class="step-list">
        ${tutorial.steps.map((step) => `<li>${step}</li>`).join("")}
      </ol>
    `;
    root.appendChild(article);
  });
}

function renderWorkflow() {
  const root = document.getElementById("workflow-board");
  if (!root) return;

  workflow.forEach((step, index) => {
    const article = document.createElement("article");
    article.className = "workflow-step reveal";
    article.style.transitionDelay = `${index * 0.1}s`;
    article.innerHTML = `
      <span class="workflow-step-number">Step ${index + 1}</span>
      <div style="font-size:1.6rem;margin:2px 0">${step.icon}</div>
      <h3>${step.title}</h3>
      <p>${step.body}</p>
    `;
    root.appendChild(article);

    // Connector arrow between steps (hidden on small viewports via CSS)
    if (index < workflow.length - 1) {
      const connector = document.createElement("div");
      connector.className = "workflow-connector";
      connector.setAttribute("aria-hidden", "true");
      connector.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="5" y1="12" x2="19" y2="12"></line>
          <polyline points="12 5 19 12 12 19"></polyline>
        </svg>
      `;
      root.appendChild(connector);
    }
  });
}

function renderList(targetId, items) {
  const root = document.getElementById(targetId);
  if (!root) return;

  items.forEach((item, index) => {
    const block = document.createElement("div");
    block.className = "list-item reveal";
    block.style.transitionDelay = `${index * 0.06}s`;

    const dotHtml = item.dotClass
      ? `<span class="status-dot ${item.dotClass}" aria-hidden="true"></span>`
      : "";

    block.innerHTML = `
      <strong>${dotHtml}<code>${item.name}</code></strong>
      <p>${item.detail}</p>
    `;
    root.appendChild(block);
  });
}

function renderCommands() {
  const root = document.getElementById("command-grid");
  if (!root) return;

  commands.forEach((item, index) => {
    const article = document.createElement("article");
    article.className = "command-card reveal";
    article.style.transitionDelay = `${index * 0.06}s`;
    article.innerHTML = `
      <strong>${item.title}</strong>
      <p>${item.body}</p>
      <div class="code-block">
        <code class="command-code"></code>
        <button class="copy-btn" aria-label="Copy command">Copy</button>
      </div>
    `;

    article.querySelector(".command-code").textContent = item.command;

    article.querySelector(".copy-btn").addEventListener("click", function () {
      navigator.clipboard.writeText(item.command).then(() => {
        this.textContent = "Copied!";
        this.classList.add("copied");
        setTimeout(() => {
          this.textContent = "Copy";
          this.classList.remove("copied");
        }, 2000);
      });
    });

    root.appendChild(article);
  });
}

function renderSavingsChart() {
  const root = document.getElementById("savings-chart");
  if (!root) return;

  const rows = [
    { label: "Without cache", percent: 100, value: "~14 000 tokens", colorClass: "amber" },
    { label: "With caching",  percent: 57,  value: "~8 000 tokens",  colorClass: "green" }
  ];

  rows.forEach((row) => {
    const div = document.createElement("div");
    div.className = "savings-row";
    div.innerHTML = `
      <span class="savings-label">${row.label}</span>
      <div class="savings-bar-track">
        <div class="savings-bar-fill ${row.colorClass}" data-width="${row.percent}"></div>
      </div>
      <span class="savings-value">${row.value}</span>
    `;
    root.appendChild(div);
  });
}

/* ============================================================
   Scroll reveal via IntersectionObserver
   ============================================================ */
function initReveal() {
  if (!("IntersectionObserver" in window)) {
    // Fallback: show everything immediately
    document.querySelectorAll(".reveal, .reveal-left").forEach((el) => {
      el.classList.add("visible");
    });
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
  );

  document.querySelectorAll(".reveal, .reveal-left").forEach((el) => {
    observer.observe(el);
  });
}

/* Animate savings chart bars when they scroll into view */
function initSavingsBars() {
  if (!("IntersectionObserver" in window)) {
    document.querySelectorAll(".savings-bar-fill").forEach((bar) => {
      bar.style.width = bar.dataset.width + "%";
    });
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.style.width = entry.target.dataset.width + "%";
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.5 }
  );

  document.querySelectorAll(".savings-bar-fill").forEach((bar) => {
    observer.observe(bar);
  });
}

/* ============================================================
   Boot
   ============================================================ */
renderWhatsNew();
renderTutorials();
renderWorkflow();
renderList("config-list", configItems);
renderList("status-list", statuses);
renderList("directory-list", directories);
renderList("test-list", tests);
renderCommands();
renderSavingsChart();

// Init animations after DOM is populated
requestAnimationFrame(() => {
  initReveal();
  initSavingsBars();
});

