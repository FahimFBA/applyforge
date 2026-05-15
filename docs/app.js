const tutorials = [
  {
    title: "1. Clone and install",
    tags: ["Python 3.11+", "Virtualenv", "Requirements"],
    summary: "Prepare local environment and install runtime dependencies before touching credentials.",
    steps: [
      "Clone repo and enter project directory.",
      "Create virtual environment with `python -m venv .venv`.",
      "Install packages with `pip install -r requirements.txt`."
    ]
  },
  {
    title: "2. Connect Google services",
    tags: ["Sheets API", "Drive API", "OAuth2"],
    summary: "Create service-account access for Sheets and OAuth2 user credentials for Drive uploads.",
    steps: [
      "Enable Google Sheets API and Google Drive API in one Google Cloud project.",
      "Create service account, download JSON key, copy full JSON into `GOOGLE_SERVICE_ACCOUNT`.",
      "Create desktop OAuth client, run refresh-token script, save printed `GOOGLE_OAUTH_*` values."
    ]
  },
  {
    title: "3. Prepare spreadsheet and resumes",
    tags: ["Sheet Schema", "PDF Intake", "Resume Types"],
    summary: "Make input sheet match expected columns and supply compact text profiles — from a PDF or written by hand.",
    steps: [
      "Create spreadsheet headers: `status`, `company`, `role`, `job_id`, `link`, `description`, `job_full_desc`, `resume_type`, `will_ai_generate_email_draft_md`, `will_ai_generate_email_draft_docs`, `will_ai_generate_coverletter_md`, `will_ai_generate_coverletter_docs`.",
      "If `job_full_desc` has 20+ words, automation uses it directly and skips scraping job link.",
      "Use `yes` or `no` in AI output columns. Leave blank to default to `yes`.",
      "Resume profiles — two options: (A) place PDFs in `raw_resumes/` and run `python scripts/process_resume.py` to auto-generate compact `.txt` profiles; or (B) skip the script and write a compact plain-text summary of your resume yourself, then paste it directly into the GitHub Variable.",
      "Paste each profile's text into a GitHub Variable: `RESUME_DEFAULT`, `RESUME_BACKEND`, etc. The runtime only ever sees this text — it does not matter whether it came from a PDF or was written manually."
    ]
  },
  {
    title: "4. Run automation locally",
    tags: ["dotenv", "Main Entrypoint", "Logs"],
    summary: "Validate full pipeline with local execution before trusting schedule automation.",
    steps: [
      "Copy `example.env` to `.env` and fill required values.",
      "Run `python main.py`.",
      "Inspect generated files under `output/` and logs under `logs/`."
    ]
  },
  {
    title: "5. Ship daily automation",
    tags: ["GitHub Actions", "Secrets", "Artifacts"],
    summary: "Move working local setup into GitHub Actions so jobs process on schedule.",
    steps: [
      "Push project to GitHub first. If you use a fork, keep `origin` on your fork and add `FahimFBA/applyforge` as `upstream`; only maintainers should point `origin` directly at `FahimFBA/applyforge`.",
      "Add required secrets: `OPENAI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT`, and OAuth values.",
      "Add variables: `GOOGLE_SHEET_ID` (spreadsheet ID from URL), `GOOGLE_DRIVE_FOLDER_ID`, `OPENAI_MODEL`, `MAX_JOBS_PER_RUN`, and `RESUME_DEFAULT`.",
      "Add one repository variable per resume type as `RESUME_<TYPE>`. Workflow exports every `RESUME_*` variable automatically.",
      "Trigger manual run from Actions UI before relying on cron."
    ]
  },
  {
    title: "6. Tune cost and reliability",
    tags: ["Rate Limits", "Retries", "Token Budget"],
    summary: "Use compact resume profiles, capped max jobs, and retry knobs to keep runs stable.",
    steps: [
      "Leave `gpt-4o-mini` as default unless output quality proves weak.",
      "Increase `RATE_LIMIT_DELAY` or reduce `MAX_JOBS_PER_RUN` if limits appear.",
      "Prefill `description` in spreadsheet for job boards that block scraping."
    ]
  }
];

const workflow = [
  {
    title: "Fetch pending jobs",
    body: "Rows with `status = not applied` loaded from Google Sheets."
  },
  {
    title: "Resolve job context",
    body: "Use sheet description when present; scrape from link when missing."
  },
  {
    title: "Generate tailored drafts",
    body: "Load matching resume profile, then create only row-enabled cover letter and recruiter email drafts with OpenAI."
  },
  {
    title: "Write output files",
    body: "Save only requested Markdown and/or DOCX variants for recruiter email and cover letter."
  },
  {
    title: "Upload and mark done",
    body: "Push files to Google Drive and update sheet status to `draft generated`."
  }
];

const configItems = [
  {
    name: "OPENAI_API_KEY",
    detail: "Required. Auth for content generation."
  },
  {
    name: "GOOGLE_SERVICE_ACCOUNT",
    detail: "Required. Service-account JSON string for Sheets access."
  },
  {
    name: "GOOGLE_OAUTH_REFRESH_TOKEN",
    detail: "Required for personal Drive uploads. Works with OAuth client ID and secret."
  },
  {
    name: "GOOGLE_SHEET_ID",
    detail: "Required. Spreadsheet ID from the URL: docs.google.com/spreadsheets/d/<ID>/edit"
  },
  {
    name: "GOOGLE_DRIVE_FOLDER_ID",
    detail: "Recommended. Target Drive folder ID from URL."
  },
  {
    name: "OPENAI_MODEL",
    detail: "Default `gpt-4o-mini`. Change only if quality or policy needs differ."
  },
  {
    name: "MAX_JOBS_PER_RUN",
    detail: "Default `10`. Caps API usage and run duration."
  },
  {
    name: "RESUME_DEFAULT",
    detail: "Required. Processed resume profile text (fallback for all resume types)."
  },
  {
    name: "RESUME_BACKEND / RESUME_AI",
    detail: "Optional examples. Add RESUME_<TYPE> for each resume_type in your sheet. Workflow exports every `RESUME_*` repository variable."
  }
];

const statuses = [
  {
    name: "not applied",
    detail: "Ready for automation pickup."
  },
  {
    name: "processing",
    detail: "Current run claimed row."
  },
  {
    name: "draft generated",
    detail: "Outputs created and uploaded."
  },
  {
    name: "reviewed",
    detail: "Human reviewed draft."
  },
  {
    name: "applied",
    detail: "Application submitted manually."
  },
  {
    name: "failed",
    detail: "Job processing broke. Check logs and retry."
  }
];

const directories = [
  {
    name: ".github/workflows/",
    detail: "Scheduled automation, docs deployment, and release workflow."
  },
  {
    name: "services/",
    detail: "Config, logging, Sheets, Drive, scraping, OpenAI, doc generation."
  },
  {
    name: "services/prompts.py",
    detail: "All AI prompt templates. Edit constants here to change cover letter tone, recruiter email style, or resume optimizer behavior — no other file needs changing."
  },
  {
    name: "scripts/",
    detail: "One-time helper scripts for resume processing and OAuth refresh token generation."
  },
  {
    name: "resumes/",
    detail: "Local .txt profiles for dev fallback only (gitignored). Profiles are set as GitHub Variables at runtime."
  },
  {
    name: "raw_resumes/",
    detail: "Local PDF source resumes. Sensitive, not committed."
  },
  {
    name: "output/ and logs/",
    detail: "Generated artifacts and automation logs."
  }
];

const tests = [
  {
    name: "test_config.py",
    detail: "Validation, directory creation, singleton config behavior."
  },
  {
    name: "test_document_generator.py",
    detail: "Output path sanitizing and Markdown/DOCX generation."
  },
  {
    name: "test_resume_optimizer.py",
    detail: "PDF text cleanup, fallback profile loading, empty-profile guards."
  },
  {
    name: "test_main.py",
    detail: "Per-job orchestration, full-description bypass, and output-toggle behavior."
  },
  {
    name: "test_sheets.py",
    detail: "Spreadsheet row parsing and blank `yes`/`no` defaults."
  }
];

const commands = [
  {
    title: "Create env + install",
    body: "First local bootstrap.",
    command: "python -m venv .venv\n.\\.venv\\Scripts\\activate\npip install -r requirements.txt"
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
    body: "Current unit test suite.",
    command: "python -m unittest discover -s tests -v"
  },
  {
    title: "Preview docs locally",
    body: "Open docs site in browser with static serving.",
    command: "python -m http.server 8000 -d docs"
  },
  {
    title: "Build Docker image",
    body: "Build ApplyForge container image locally.",
    command: "docker build -t applyforge ."
  },
  {
    title: "Run via Docker Compose",
    body: "Run automation in Docker with volume-mounted output.",
    command: "docker compose up"
  },
  {
    title: "Process resumes in Docker",
    body: "Run resume preprocessor inside the container.",
    command: "docker compose run --rm applyforge python scripts/process_resume.py"
  }
];

function renderTutorials() {
  const root = document.getElementById("tutorial-grid");

  tutorials.forEach((tutorial, index) => {
    const article = document.createElement("article");
    article.className = "tutorial-card";
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

  workflow.forEach((step, index) => {
    const article = document.createElement("article");
    article.className = "workflow-step";
    article.innerHTML = `
      <span class="workflow-step-number">Step ${index + 1}</span>
      <h3>${step.title}</h3>
      <p>${step.body}</p>
    `;
    root.appendChild(article);
  });
}

function renderList(targetId, items) {
  const root = document.getElementById(targetId);

  items.forEach((item) => {
    const block = document.createElement("div");
    block.className = "list-item";
    block.innerHTML = `
      <strong><code>${item.name}</code></strong>
      <p>${item.detail}</p>
    `;
    root.appendChild(block);
  });
}

function renderCommands() {
  const root = document.getElementById("command-grid");

  commands.forEach((item) => {
    const article = document.createElement("article");
    article.className = "command-card";
    article.innerHTML = `
      <strong>${item.title}</strong>
      <p>${item.body}</p>
      <div class="code-block">
        <code class="command-code"></code>
        <button class="copy-btn">Copy</button>
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

renderTutorials();
renderWorkflow();
renderList("config-list", configItems);
renderList("status-list", statuses);
renderList("directory-list", directories);
renderList("test-list", tests);
renderCommands();
