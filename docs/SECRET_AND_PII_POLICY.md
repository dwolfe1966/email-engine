# Secret And PII Handling Policy

This repository must not contain live credentials, recovery codes, private keys, customer contact
exports, or other sensitive operational data.

## Do Not Commit

Never commit:

- API keys or provider tokens, including OpenAI, SendGrid, Twilio, Vercel, Neon, SMTP, webhook, or
  cloud provider credentials.
- Recovery codes, one-time backup codes, seed phrases, private keys, certificates with private key
  material, or password exports.
- `.env`, `.env.local`, provider dashboards exports, screenshots that expose credentials, or local
  deployment notes containing secrets.
- subscriber lists, contact exports, audience imports, suppression exports, or other PII-bearing
  CSV/XLSX files.
- Production DKIM private keys or TLS private keys.
- Raw mailbox dumps, DSN archives, quarantine Maildir contents, or Postfix logs that contain real
  recipient addresses unless they have been explicitly sanitized.

## Safe To Commit

It is acceptable to commit:

- Redacted examples using placeholder values such as `<secret>`, `<token>`, `example.com`, and
  `person@example.com`.
- `.env.example` or production env examples that contain only variable names and fake values.
- Provider research, architecture documents, and runbooks that do not include live credentials or
  customer data.
- Small synthetic test fixtures with fake names and example-domain email addresses.
- Public DNS record examples when they do not expose private key material.

## Local Files

The repo intentionally ignores local reference files that are useful during development but unsafe
to publish:

- `docs/OpenAI API Key.rtf`
- `docs/SendGrid.rtf`
- `docs/twilio_2FA_recovery_code.txt`
- `tests/Milkbar_Email_List_6_4_.xlsx - subs*.csv`
- `tests/random_people_100.csv`

If a similar file is created, add it to `.gitignore` before it becomes a commit candidate.

## Managed SMTP Notes

Managed SMTP work has extra sensitive material:

- DKIM private keys belong on the MTA host or in a secrets manager, not in git.
- Postfix TLS private keys belong on the MTA host or in a secrets manager, not in git.
- SMTP submission credentials must be managed as deployment secrets.
- MTA logs, DSN messages, and Maildir archives can contain recipient PII and should be sanitized
  before being used as test fixtures.
- Readiness and smoke-test examples should use placeholders or synthetic seed addresses.

## If A Secret Is Found

1. Do not commit it.
2. Add an ignore rule if the file is local-only.
3. Move the secret into the intended secret manager or deployment environment.
4. Rotate the secret if it may have been exposed.
5. If the secret was already pushed, treat it as compromised and rotate it immediately.
