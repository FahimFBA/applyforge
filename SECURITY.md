# Security Policy

## Supported Versions

ApplyForge is currently maintained on the default branch and the latest tagged
release. Older versions may not receive security fixes.

## Reporting a Vulnerability

Please do not report security issues in public GitHub issues.

Report vulnerabilities privately using one of these paths:

1. GitHub Security Advisories for this repository, if enabled
2. The maintainer contact listed on the repository profile

Include as much detail as possible:

- A clear description of the issue
- Steps to reproduce
- Impact assessment
- Any proof-of-concept details
- Whether credentials, OAuth tokens, Google service-account JSON, or OpenAI API
  keys may be exposed

## Response Expectations

- We will acknowledge receipt as soon as practical.
- We will investigate the report and determine severity and scope.
- We will aim to coordinate a fix before public disclosure.

## Secrets Handling

Because this project integrates with Google APIs and OpenAI, treat the
following as sensitive:

- `.env` contents
- OAuth client credentials and refresh tokens
- Google service-account JSON
- OpenAI API keys
- Generated documents containing personal data

If you accidentally expose any of the above in a commit, issue, pull request,
log, or workflow output, report it immediately through the private channels
above and rotate the affected credentials.
