# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.13.0] — 2026-05-16

### Added

- **`utils/constants.py`** — single source of truth for all domain constants:
  - Spreadsheet status values (`STATUS_NOT_APPLIED`, `STATUS_PROCESSING`,
    `STATUS_DRAFT_GENERATED`, `STATUS_FAILED`, `STATUS_REVIEWED`, `STATUS_APPLIED`).
  - Spreadsheet column names (`COL_STATUS`, `COL_COMPANY`, `COL_ROLE`, `COL_JOB_ID`,
    `COL_LINK`, `COL_DESCRIPTION`, `COL_JOB_FULL_DESC`, `COL_RESUME_TYPE`, and the
    four `will_ai_generate_*` columns).
  - Flag values (`FLAG_YES`, `FLAG_NO`) and `RESUME_TYPE_DEFAULT`.
  - Processing thresholds: `JOB_FULL_DESC_MIN_WORDS`, `JD_CHAR_LIMIT_COVER_LETTER`,
    `JD_CHAR_LIMIT_EMAIL`.
- **`requirements-dev.txt`** — development dependencies: `ruff`, `mypy`.
- **`pyproject.toml`** — ruff and mypy configuration (line length 120, rules E/F/W/I/B/UP,
  per-file ignores for intentional patterns).
- **`.github/workflows/ci.yml`** — CI pipeline that runs on every push and PR to main:
  installs dev dependencies, runs `ruff check`, then runs the full unit test suite.

### Changed

- `services/config.py` — status fields now reference `utils.constants` instead of bare strings.
- `services/sheets.py` — all column name and flag literals replaced with `COL_*` /
  `FLAG_*` / `RESUME_TYPE_DEFAULT` constants.
- `main.py` — `4_000`, `3_000`, and `20` magic numbers replaced with
  `JD_CHAR_LIMIT_COVER_LETTER`, `JD_CHAR_LIMIT_EMAIL`, `JOB_FULL_DESC_MIN_WORDS`.
- Codebase-wide import ordering, unused import removal, and minor style fixes applied
  by `ruff --fix` (isort order, one unused mock import removed from tests).

---

## [1.12.0] — 2026-05-16

### Changed

- **`{resume_profile}` moved from user prompt to system prompt** for cover letter and
  recruiter email generation.  The system message now embeds the candidate profile,
  so OpenAI's automatic prompt caching covers it — the ~600-token profile is cached
  after the first API call and re-used at 50 % cost for every subsequent job in the
  same run.  With 10 jobs × 2 calls this saves roughly 6 000 cached tokens per run,
  regardless of whether default or custom `PROMPT_*` prompts are used.
- `main.py` — cover letter and recruiter email calls now format `resume_profile`
  into the system prompt; user prompt receives only job-specific variables
  (`{company}`, `{role}`, `{job_description}`).
- `services/prompts.py` — `_COVER_LETTER_SYSTEM_DEFAULT` and
  `_RECRUITER_EMAIL_SYSTEM_DEFAULT` gain a `CANDIDATE PROFILE: {resume_profile}`
  section at the bottom; corresponding `_USER` defaults no longer contain
  `{resume_profile}`.
- Placeholder contract updated across `example.env`, `README.md`, and `docs/app.js`:
  `_SYSTEM` templates require `{resume_profile}`; `_USER` templates require
  `{company}`, `{role}`, `{job_description}` only.

### Notes

- Custom `PROMPT_COVER_LETTER_SYSTEM` / `PROMPT_RECRUITER_EMAIL_SYSTEM` variables
  **must now include `{resume_profile}`** — missing it raises `KeyError` at generation
  time.  Update any existing custom system prompts before upgrading.
- Custom `PROMPT_*_USER` variables should **remove** `{resume_profile}` if present —
  it is no longer injected at the user-message level.

---

## [1.11.0] — 2026-05-16

### Added

- **Custom prompt overrides via GitHub Actions Repository Variables.**
  Any of the six built-in AI prompts can now be replaced without touching code.
  Set a `PROMPT_*` Repository Variable and the workflow uses it instead of the
  default; delete or leave it empty to revert to the default.

  | Variable | Overrides |
  |----------|-----------|
  | `PROMPT_RESUME_OPTIMIZER_SYSTEM` | Resume optimizer system prompt |
  | `PROMPT_RESUME_OPTIMIZER_USER` | Resume optimizer user prompt |
  | `PROMPT_COVER_LETTER_SYSTEM` | Cover letter system prompt |
  | `PROMPT_COVER_LETTER_USER` | Cover letter user prompt |
  | `PROMPT_RECRUITER_EMAIL_SYSTEM` | Recruiter email system prompt |
  | `PROMPT_RECRUITER_EMAIL_USER` | Recruiter email user prompt |

- `services/prompts.py` — each constant now reads its `PROMPT_*` env var at
  module load time and falls back to the hardcoded default when absent or empty.
  Public constant names (`COVER_LETTER_SYSTEM`, etc.) are unchanged — no caller
  changes needed.
- `.github/workflows/automation.yml` — export step now exports `PROMPT_*`
  variables alongside `RESUME_*` using the same multiline heredoc mechanism.

### Notes

- User-facing prompt templates (`_USER` variants) must still contain the
  required `{placeholder}` variables: `{resume_profile}`, `{company}`, `{role}`,
  `{job_description}` for cover letter / recruiter email; `{resume_text}` for
  resume optimizer. Missing placeholders raise a `KeyError` at generation time.
- Prompts are Repository **Variables** (not Secrets) — they are not sensitive.

---

## [1.10.0] — 2026-05-16

### Added

- **Docker support.** `Dockerfile`, `docker-compose.yml`, and `.dockerignore`
  added so the automation can run without a local Python install.
  `docker compose up` mounts `output/`, `logs/`, `resumes/`, and
  `raw_resumes/` as volumes so generated files persist on the host.
- **Resume manual text option documented.** README and docs tutorial now
  explicitly describe both resume intake paths: (A) PDF → `process_resume.py`
  → GitHub Variable, and (B) write a compact plain-text profile by hand and
  paste directly into the GitHub Variable — no PDF or script required.
- **Prompt customization guide.** README and docs now explain that all AI
  prompt templates live in `services/prompts.py` as module-level constants,
  list every constant pair and its purpose, and show how to edit them without
  touching business logic.
- **OpenAI client cleanup.** Removed dead code from `services/openai_client.py`.

### Changed

- `README.md` — Project Structure section updated with new Docker files;
  Running with Docker section added (item 10); TOC renumbered accordingly.
- `docs/app.js` — Command Deck now includes Docker build, Compose run, and
  in-container resume processing commands; Directories reference lists
  `services/prompts.py` as the single file to edit for prompt changes.

---

## [1.9.0] — 2026-05-15

### Changed

- **Breaking: Spreadsheet lookup now uses ID instead of name.**
  `GOOGLE_SHEET_NAME` is replaced by `GOOGLE_SHEET_ID` — set it to the
  alphanumeric ID from the spreadsheet URL
  (`docs.google.com/spreadsheets/d/<ID>/edit`).
  Using an ID is unambiguous, works regardless of spreadsheet renames, and
  avoids `SpreadsheetNotFound` errors caused by name case mismatches.
- `services/config.py` — `google_sheet_name` field renamed to `google_sheet_id`;
  reads from `GOOGLE_SHEET_ID` env var with no default (required).
- `services/sheets.py` — `connect()` uses `open_by_key()` instead of `open()`.
- `automation.yml` — `GOOGLE_SHEET_NAME` variable replaced with `GOOGLE_SHEET_ID`.
- `example.env` — documents `GOOGLE_SHEET_ID` with instructions for finding it.

### Migration from v1.8.x

1. Find your spreadsheet ID in the URL:
   `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`
2. Replace `GOOGLE_SHEET_NAME` with `GOOGLE_SHEET_ID=<your-id>` in your `.env`.
3. In GitHub Actions Variables: delete `GOOGLE_SHEET_NAME`, add `GOOGLE_SHEET_ID`.

---

## [1.8.2] — 2026-05-15

### Fixed

- GitHub Release workflow changelog extraction now stops at the next version
  heading instead of relying on brittle awk escaping.
- Release process docs now stay aligned with tagged releases by documenting the
  versioned release fix separately from the earlier `1.8.0` workflow/docs
  changes.

---

## [1.8.0] — 2026-05-15

### Added

- GitHub Actions workflow now exports every repository variable whose name
  starts with `RESUME_`, so new `resume_type` values work without editing
  `.github/workflows/automation.yml`.
- Release workflow documentation now includes `release.yml` in the project
  structure and explains fork-vs-maintainer Git remote setup more clearly.
- Windows PowerShell copy command examples in `README.md` and `example.env`
  alongside the existing macOS / Linux examples.

### Changed

- `.github/workflows/automation.yml` now loads resume profile variables
  dynamically from repository variables instead of hardcoding a small fixed
  list in the workflow environment block.
- Docs site tutorial/reference text now explains that all `RESUME_*`
  repository variables are exported automatically.
- Service-account JSON flattening examples now use portable `python -c ...`
  commands instead of shell-specific pipelines.

---

## [1.7.0] — 2026-05-13

### Added

- Per-job spreadsheet output toggles:
  `will_ai_generate_email_draft_md`,
  `will_ai_generate_email_draft_docs`,
  `will_ai_generate_coverletter_md`, and
  `will_ai_generate_coverletter_docs`. Values accept `yes` / `no`, and blank
  values default to `yes`.
- `job_full_desc` spreadsheet column. When the cell contains at least 20 words,
  ApplyForge uses that text directly and skips visiting the job link.
- Unit test coverage for spreadsheet parsing and main per-job generation flow.

### Changed

- `main.py` now generates and uploads only the email / cover letter formats
  requested for each row instead of always producing both `.md` and `.docx`
  outputs.
- Docs site spreadsheet tables now wrap safely inside a horizontal scroll
  container instead of stretching past the page width.

---

## [1.6.2] — 2026-05-11

### Fixed

- **Full Guide page markdown rendering crash** — removed brittle custom `marked`
  heading renderer from `docs/readme.html` and now generate heading anchor IDs
  from rendered DOM text after `marked.parse(md)`, avoiding browser/runtime
  differences around parser internals.
- **Broken repository file links inside Full Guide** — relative markdown links
  like `CHANGELOG.md` now rewrite to GitHub blob URLs in the docs site, so the
  changelog link at the end of the README opens correctly on GitHub Pages.

---

## [1.6.1] — 2026-05-11

### Fixed

- **Full Guide page stuck on "Loading README…"** — two bugs in `docs/readme.html`:
  1. Heading renderer destructured `{ text, depth }` but in marked v9 the token
     carries `{ tokens, depth }` — `text` is always `undefined`, causing
     `text.replace(...)` to throw inside `marked.parse()`. Fixed by using
     `{ tokens, depth }` and rendering via `this.parser.parseInline(tokens)`.
  2. All post-fetch DOM manipulation was outside the `try/catch`, so any exception
     produced a silent failure with no error shown. Entire `loadReadme` body is
     now inside a single `try/catch`.
- Heading slug generation strips HTML tags from the rendered text before slugifying,
  so headings with inline markup (`**bold**`, `` `code` ``) produce clean anchor IDs.

---

## [1.6.0] — 2026-05-11

### Added

- **Full Guide page** (`docs/readme.html`) — renders the repository README inside
  the docs site with syntax-highlighted code blocks, copy buttons on every snippet,
  and working table-of-contents anchor links.
- Copy buttons on all Command Deck snippets in the docs homepage.
- `docs-site.yml` CI step to copy `README.md` into `docs/` before artifact upload,
  making the file accessible to the Full Guide page on GitHub Pages.
- `docs/README.md` added to `.gitignore` so the CI-generated copy is never committed.

### Changed

- Docs site nav link renamed from "README" to "Full Guide" and now points to
  `readme.html` instead of the raw `../README.md` file (which is unreachable on
  GitHub Pages).
- Command code blocks in the docs site now render with `white-space: pre` so
  multi-line commands display correctly.

---

## [1.5.0] — 2026-05-10

### Changed

- **Breaking: Resume profiles moved from repository files to GitHub Variables.**
  Profiles were previously committed to `resumes/` (safe only in a private repo).
  Now that the repository is public, profiles are stored as GitHub Actions
  Repository Variables (`RESUME_DEFAULT`, `RESUME_BACKEND`, `RESUME_AI`, etc.)
  and injected at runtime via environment variables — no resume content ever
  touches the repository.
- `services/resume_optimizer.py` — `load_resume_profile()` now resolves profiles
  in priority order: env var `RESUME_{TYPE}` → local file `resumes/{type}.txt` →
  env var `RESUME_DEFAULT` → local file `resumes/default.txt`. Local file fallback
  preserves existing local-dev workflows.
- `.gitignore` — added `resumes/*.txt`; profiles are no longer tracked.
- `resumes/default.txt` removed from version control.
- `automation.yml` — passes `RESUME_DEFAULT`, `RESUME_BACKEND`, and `RESUME_AI`
  from Repository Variables as environment variables to the Python runtime.
- `example.env` — documents the new `RESUME_*` variable section.

### Migration from v1.4.x

1. Run `python scripts/process_resume.py` to generate `.txt` profiles locally.
2. Copy each profile's content into a GitHub Actions Repository Variable:
   **Settings → Secrets and variables → Actions → Variables → New repository variable**
   - `RESUME_DEFAULT` — content of `resumes/default.txt`
   - `RESUME_BACKEND` — content of `resumes/backend.txt` (if you use this type)
   - `RESUME_AI` — content of `resumes/ai.txt` (if you use this type)
3. Local `.txt` files remain usable for local dev but are now gitignored.

---

## [1.4.1] — 2026-05-10

### Added

- Added the new ApplyForge overview graphic under `docs/assets/` and embedded
  it in both the docs homepage and the repository README.

### Changed

- Centralized the project hero image in a shared docs asset path so GitHub
  Pages and GitHub README rendering stay in sync.

---

## [1.4.0] — 2026-05-10

### Changed

- Rebranded project from `career-agent-email-cover` / "Career Agent" to
  `applyforge` / "ApplyForge" across README, docs site, workflows, config
  references, and runtime-facing labels.
- Updated clone examples, GitHub Actions workflow names, Google Cloud naming
  examples, and release metadata to use the new project name consistently.

---

## [1.3.0] — 2026-05-10

### Added

- Static documentation website under `docs/` with tutorial cards, workflow
  overview, configuration highlights, project layout, status values, and command
  reference.
- GitHub Pages deployment workflow at `.github/workflows/docs-site.yml` for
  publishing the `docs/` directory from GitHub Actions.

### Changed

- README now links and documents the new docs website, local preview command,
  GitHub Pages activation steps, and updated project structure.

---

## [1.2.1] — 2026-05-10

### Added

- Unit test suite under `tests/` covering config validation, document generation,
  and resume optimizer behavior.

### Changed

- README now documents unit test execution and includes `tests/` in project
  structure.

---

## [1.2.0] — 2026-05-09

### Fixed

- **Google Drive `403 storageQuotaExceeded`** — service accounts have zero
  personal Drive storage quota and cannot upload to regular "My Drive" folders.
  Switched Drive auth to OAuth2 user credentials so files are uploaded as the
  real Google account owner.

### Added

- `scripts/generate_refresh_token.py` — one-time local script that opens a
  browser for Google login and prints the three credential values to save as
  GitHub Secrets.
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`,
  `GOOGLE_OAUTH_REFRESH_TOKEN` config fields in `services/config.py`.
- `GOOGLE_DRIVE_FOLDER_ID` config field — set to the Drive folder ID from the
  folder URL for reliable targeting without name-based search.
- `supportsAllDrives=True` and `includeItemsFromAllDrives=True` on all Drive
  API calls for forward compatibility with Shared Drives.
- `google-auth-oauthlib>=1.2.0` dependency.

### Changed

- `services/drive.py` now prefers OAuth2 user credentials over service-account
  credentials when `GOOGLE_OAUTH_REFRESH_TOKEN` is present. Service-account
  auth remains as a fallback for Shared Drive setups.
- GitHub Actions workflow exposes three new OAuth2 secrets.
- `oauth_client.json` added to `.gitignore`.

---

## [1.1.0] — 2026-05-09

### Fixed

- **Blank directories missing after `git clone`** — `.gitignore` patterns used
  `dir/` which prevents negation rules from working inside the directory. Changed
  to `dir/*` so `.gitkeep` files are correctly unignored.
- **GitHub Actions Node.js 20 deprecation warning** — added
  `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` at workflow level to opt into
  Node.js 24 ahead of the September 2026 forced migration.

### Added

- `.gitkeep` files in `raw_resumes/`, `output/`, and `logs/` so all expected
  directories exist immediately after cloning.

### Changed

- Removed `resumes/*.txt` from `.gitignore` — profiles are committed directly
  since this is a private repository, eliminating the need for GitHub Secrets
  to hold resume content at runtime.

---

## [1.0.0] — 2026-05-08

### Added

- Initial release.
- Daily automation via GitHub Actions (`0 19 * * *` UTC = 1:00 AM BST).
- Google Sheets integration: reads `not applied` rows, writes status updates
  throughout processing.
- Job-page scraping with `requests` + `BeautifulSoup` — no headless browser.
- OpenAI cover letter and recruiter email generation with exponential backoff
  and separate rate-limit handling.
- Google Drive upload organized into `Applications/<Company>/` sub-folders.
- Two-phase resume pipeline: preprocess PDFs once with
  `scripts/process_resume.py`, use compact `.txt` profiles at runtime
  (~55% token reduction per job).
- Output formats: `.md` (plain text) and `.docx` (formatted Word document).
- All credentials stored as GitHub Secrets — no JSON files on disk.
- Manual workflow trigger with `max_jobs` and `log_level` overrides.
- Artifact upload of generated documents (30-day retention in Actions UI).
- Per-job failure isolation — one failure does not stop the rest of the run.

[1.13.0]: https://github.com/FahimFBA/applyforge/compare/v1.12.0...v1.13.0
[1.12.0]: https://github.com/FahimFBA/applyforge/compare/v1.11.0...v1.12.0
[1.11.0]: https://github.com/FahimFBA/applyforge/compare/v1.9.0...v1.11.0
[1.10.0]: https://github.com/FahimFBA/applyforge/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/FahimFBA/applyforge/compare/v1.8.2...v1.9.0
[1.8.2]: https://github.com/FahimFBA/applyforge/compare/v1.8.0...v1.8.2
[1.8.0]: https://github.com/FahimFBA/applyforge/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/FahimFBA/applyforge/compare/v1.6.2...v1.7.0
[1.6.1]: https://github.com/FahimFBA/applyforge/compare/v1.6.0...v1.6.1
[1.6.2]: https://github.com/FahimFBA/applyforge/compare/v1.6.1...v1.6.2
[1.6.0]: https://github.com/FahimFBA/applyforge/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/FahimFBA/applyforge/compare/v1.4.1...v1.5.0
[1.4.1]: https://github.com/FahimFBA/applyforge/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/FahimFBA/applyforge/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/FahimFBA/applyforge/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/FahimFBA/applyforge/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/FahimFBA/applyforge/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/FahimFBA/applyforge/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/FahimFBA/applyforge/releases/tag/v1.0.0
