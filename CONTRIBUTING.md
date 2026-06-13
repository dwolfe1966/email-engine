# Contributing

1. Create a feature branch from `main`.
2. Run `ruff check .`, `mypy src`, and `pytest` before opening a PR.
3. Keep provider-specific integrations behind `email_platform.providers`.
4. Never commit `.env`, API keys, recovery codes, private keys, or PII exports.
5. Follow `docs/SECRET_AND_PII_POLICY.md` before staging provider docs, SMTP artifacts, or contact
   data.
6. Run `python scripts/secret_pii_guard.py` before committing sensitive-adjacent docs or fixtures.
