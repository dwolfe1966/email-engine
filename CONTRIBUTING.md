# Contributing

1. Create a feature branch from `main`.
2. Run `ruff check .`, `mypy src`, and `pytest` before opening a PR.
3. Keep provider-specific integrations behind `email_platform.providers`.
4. Never commit `.env` or API keys.
