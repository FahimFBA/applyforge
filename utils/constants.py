"""
utils/constants.py
==================
Project-wide constants — values that are fixed by the domain schema and
never driven by environment variables or runtime configuration.

Guidelines
----------
* Status strings and column names must match the Google Spreadsheet schema
  exactly (case-sensitive).
* Processing thresholds (word counts, character caps) are documented here so
  they can be updated in one place.
* Do NOT put environment-variable defaults here — those belong in
  services/config.py.
* Do NOT put prompt templates here — those belong in services/prompts.py.
"""
from __future__ import annotations

# ======================================================================== #
# Spreadsheet status vocabulary                                              #
# Must match the values users type into the "status" column exactly.        #
# ======================================================================== #

STATUS_NOT_APPLIED: str = "not applied"
STATUS_PROCESSING: str = "processing"
STATUS_DRAFT_GENERATED: str = "draft generated"
STATUS_FAILED: str = "failed"
STATUS_REVIEWED: str = "reviewed"
STATUS_APPLIED: str = "applied"

# ======================================================================== #
# Spreadsheet column names                                                   #
# Must match the header row of the Google Spreadsheet exactly.              #
# ======================================================================== #

COL_STATUS: str = "status"
COL_COMPANY: str = "company"
COL_ROLE: str = "role"
COL_JOB_ID: str = "job_id"
COL_LINK: str = "link"
COL_DESCRIPTION: str = "description"
COL_JOB_FULL_DESC: str = "job_full_desc"
COL_RESUME_TYPE: str = "resume_type"
COL_EMAIL_DRAFT_MD: str = "will_ai_generate_email_draft_md"
COL_EMAIL_DRAFT_DOCS: str = "will_ai_generate_email_draft_docs"
COL_COVERLETTER_MD: str = "will_ai_generate_coverletter_md"
COL_COVERLETTER_DOCS: str = "will_ai_generate_coverletter_docs"

# ======================================================================== #
# Spreadsheet yes/no flag values                                             #
# ======================================================================== #

FLAG_YES: str = "yes"
FLAG_NO: str = "no"

# ======================================================================== #
# Resume type                                                                #
# ======================================================================== #

RESUME_TYPE_DEFAULT: str = "default"

# ======================================================================== #
# Job description processing thresholds                                      #
# ======================================================================== #

# Rows with job_full_desc containing at least this many words skip scraping
JOB_FULL_DESC_MIN_WORDS: int = 20

# Character cap on job description passed to each generation call.
# Keeps context within a sensible budget; JD text beyond this is truncated.
JD_CHAR_LIMIT_COVER_LETTER: int = 4_000
JD_CHAR_LIMIT_EMAIL: int = 3_000
