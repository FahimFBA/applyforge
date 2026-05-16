# Contributing to ApplyForge

Thanks for contributing. Keep changes focused, tested, and aligned with the
automation workflow documented in [README.md](README.md).

## Before You Start

- Read the relevant section in [README.md](README.md) to understand the current
  architecture and configuration model.
- Search existing issues and pull requests before opening a new one.
- Use discussions in issues for bugs, regressions, and concrete feature work.

## Development Setup

1. Fork the repository and create a topic branch from `main`.
2. Set up Python 3.11 or newer.
3. Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

4. Copy `example.env` to `.env` and provide local values as needed.
5. If your change depends on Google APIs or OpenAI, prefer mocks or fixtures in
   tests so CI remains deterministic.

## Project Conventions

- Keep configuration driven by environment variables when possible.
- Avoid committing secrets, OAuth client files, generated tokens, resumes, or
  generated outputs.
- Preserve the existing module split in `services/`, `utils/`, `scripts/`, and
  `tests/`.
- Update documentation when behavior, setup, configuration, or workflows change.
- Add or update tests for behavior changes.

## Local Checks

Run the same checks used in CI before opening a pull request:

```bash
ruff check .
python -m unittest discover -s tests -v
```

If you touched dependency management, Docker setup, or GitHub Actions, validate
those paths locally as far as practical and describe any limits in the pull
request.

## Commit and Pull Request Guidance

- Use small, reviewable commits with clear messages.
- Keep pull requests scoped to one logical change.
- Link related issues using `Fixes #<number>` or `Refs #<number>` when
  applicable.
- Fill out the pull request template completely, especially rollout or
  configuration impacts.

## Documentation Expectations

Update the following when relevant:

- [README.md](README.md) for setup, workflow, or usage changes
- [`docs/`](docs/) for documentation site content
- [CHANGELOG.md](CHANGELOG.md) for notable user-facing changes, if the project
  maintainers are tracking the change there

## Reporting Security Issues

Do not open public issues for security vulnerabilities, exposed credentials, or
token-handling flaws. Follow [SECURITY.md](SECURITY.md) instead.

## Review Criteria

Maintainers will generally look for:

- Correctness and test coverage
- Clear operational impact
- Backward compatibility for existing config and automation flows
- Reasonable failure handling for external API calls
- Documentation updates where needed
