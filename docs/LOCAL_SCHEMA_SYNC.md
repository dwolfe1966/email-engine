# Local Schema Sync

Use this when a local EE or SentientMail setup starts returning API errors after new backend work lands.

## Check Status

Open the EE admin home:

```text
http://localhost:8000/admin
```

The schema banner shows the database revision, expected code revision, and whether migrations are needed.

You can also call the API directly:

```bash
curl http://localhost:8000/api/v1/system/schema-status
```

For a fuller local/remote sanity check, use:

```bash
curl http://localhost:8000/api/v1/system/diagnostics
```

That response includes schema status, provider configuration booleans, AI configuration booleans, and core entity counts without exposing secrets.

## Fix A Stale Local Database

From the `email-engine` repository:

```bash
alembic upgrade head
```

If using the project virtual environment:

```bash
.venv/bin/alembic upgrade head
```

Then restart the EE API and refresh the SentientMail UI.
