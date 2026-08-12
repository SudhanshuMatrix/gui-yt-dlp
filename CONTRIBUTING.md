# Contributing to gui-yt-dlp

Thank you for your interest in contributing to **gui-yt-dlp**!

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/SudhanshuMatrix/gui-yt-dlp.git
   cd gui-yt-dlp
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install all dependencies (including dev tools)**:
   ```bash
   pip install -e .[dev]
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## Running Tests & Quality Checks

- **Run Unit Tests**:
  ```bash
  python -m pytest tests/
  ```
- **Code Formatting**:
  ```bash
  black src tests
  isort src tests
  ```
- **Linting**:
  ```bash
  ruff check src tests
  ```
- **Type Checking**:
  ```bash
  mypy src
  ```

## Submitting Pull Requests

1. Fork the repo and create your branch from `main`.
2. Ensure all tests and linting pass before submitting.
3. Write a clear PR description detailing your changes and motivation.
4. If your PR is a bug fix, reference the issue it closes.

## Code Review Policy

All contributions are reviewed before merge. Please:
- Keep PRs focused and small where possible.
- Add tests for new logic.
- Update documentation as needed.

## 🤖 AI Assistance Disclosure Policy

This project welcomes contributions that were assisted by AI tools (such as Gemini, Claude, ChatGPT, Copilot, etc.). However, to maintain transparency and accountability:

**In your PR description or commit message, you MUST disclose any AI assistance:**

```
Assisted By: <Model Name> (e.g., Claude Sonnet 4.5, Gemini 2.5 Pro)
```

**Review Responsibility**: Even when AI-assisted, you are responsible for reviewing all generated code **before** committing or submitting. Never blindly paste AI output — verify correctness, security, and style compliance yourself.

**Example PR description:**
```
## Changes
- Fixed yt-dlp update worker to use sys.executable -m pip

## AI Assistance
Assisted By: Claude Sonnet 4.6 (Thinking)
All code was manually reviewed and tested before submission.
```

Failure to disclose AI assistance or submitting unreviewed AI-generated code may result in the PR being closed.

## Community Standards

Please read and follow our [Code of Conduct](./CODE_OF_CONDUCT.md).
