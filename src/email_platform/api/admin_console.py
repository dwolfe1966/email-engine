from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from email_platform.api.operation_feedback import with_operation_feedback

router = APIRouter()


@router.get('/admin', response_class=HTMLResponse, include_in_schema=False)
def admin_home() -> str:
    return with_operation_feedback(ADMIN_HOME_HTML)


@router.get('/admin/entities', response_class=HTMLResponse, include_in_schema=False)
def admin_entities() -> str:
    return with_operation_feedback(ADMIN_ENTITIES_HTML)


@router.get('/admin/audience-import', response_class=HTMLResponse, include_in_schema=False)
def admin_audience_import() -> str:
    return with_operation_feedback(ADMIN_AUDIENCE_IMPORT_HTML)


@router.get('/admin/audiences', response_class=HTMLResponse, include_in_schema=False)
def admin_audiences() -> str:
    return with_operation_feedback(ADMIN_AUDIENCES_HTML)


@router.get('/admin/campaigns', response_class=HTMLResponse, include_in_schema=False)
def admin_campaigns() -> str:
    return with_operation_feedback(ADMIN_CAMPAIGNS_HTML)


@router.get('/admin/journeys', response_class=HTMLResponse, include_in_schema=False)
def admin_journeys() -> str:
    return with_operation_feedback(ADMIN_JOURNEYS_HTML)


@router.get('/admin/delivery', response_class=HTMLResponse, include_in_schema=False)
def admin_delivery() -> str:
    return with_operation_feedback(ADMIN_DELIVERY_HTML)


@router.get('/admin/analytics', response_class=HTMLResponse, include_in_schema=False)
def admin_analytics() -> str:
    return with_operation_feedback(ADMIN_ANALYTICS_HTML)


@router.get('/admin/data-sources', response_class=HTMLResponse, include_in_schema=False)
def admin_data_sources() -> str:
    return with_operation_feedback(ADMIN_DATA_SOURCES_HTML)


@router.get('/admin/suppressions', response_class=HTMLResponse, include_in_schema=False)
def admin_suppressions() -> str:
    return with_operation_feedback(ADMIN_SUPPRESSIONS_HTML)


@router.get('/admin/system', response_class=HTMLResponse, include_in_schema=False)
def admin_system() -> str:
    return with_operation_feedback(ADMIN_SYSTEM_HTML)


ADMIN_HOME_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Admin</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 18px 22px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    nav { display: flex; flex-wrap: wrap; gap: 8px; }
    nav a {
      min-height: auto;
      padding: 8px 10px;
      border-color: var(--blue);
      color: var(--blue);
      font-weight: 650;
    }
    main {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      padding: 14px;
      max-width: 1120px;
    }
    .system-status {
      grid-column: 1 / -1;
      min-height: auto;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 12px 14px;
    }
    .system-status.ok { border-color: #067647; }
    .system-status.warn { border-color: #b54708; background: #fffbeb; }
    .system-status.error { border-color: #b42318; background: #fef3f2; }
    .system-status strong { display: block; margin-bottom: 4px; }
    .system-status code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
    }
    .system-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }
    .system-meta span {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 8px;
      background: #fff;
      color: var(--muted);
      font-size: 12px;
    }
    a {
      display: grid;
      gap: 8px;
      min-height: 112px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--text);
      text-decoration: none;
    }
    strong { font-size: 15px; }
    span { color: var(--muted); line-height: 1.45; }
    a:hover { border-color: var(--blue); }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Admin</h1>
    <nav>
      <a href="/admin">Admin</a>
      <a href="/tester">Tester</a>
      <a href="/template-editor">Template Editor</a>
      <a href="/admin/entities">Entity Workbench</a>
      <a href="/admin/audience-import">Audience Import</a>
      <a href="/admin/audiences">Audience Builder</a>
      <a href="/admin/campaigns">Campaign Manager</a>
      <a href="/admin/journeys">Journey Manager</a>
      <a href="/admin/delivery">Delivery Manager</a>
      <a href="/admin/suppressions">Suppressions</a>
      <a href="/admin/analytics">Analytics</a>
      <a href="/admin/data-sources">Data Sources</a>
      <a href="/admin/system">System</a>
      <a href="/docs">Docs</a>
    </nav>
  </header>
  <main>
    <section class="system-status" id="schemaStatus">
      <strong>Schema status</strong>
      <span>Checking database migration status...</span>
    </section>
    <a href="/admin/entities">
      <strong>Entity Workbench</strong>
      <span>List, create, update, and delete core API entities from one page.</span>
    </a>
    <a href="/template-editor">
      <strong>Template Editor</strong>
      <span>Edit subject, HTML, CSS, text, variables, validation, and preview.</span>
    </a>
    <a href="/admin/audience-import">
      <strong>Audience Import</strong>
      <span>Upload a CSV file, upsert contacts, and create an audience.</span>
    </a>
    <a href="/admin/audiences">
      <strong>Audience Builder</strong>
      <span>Create, preview, update, and delete rule-based audiences.</span>
    </a>
    <a href="/admin/campaigns">
      <strong>Campaign Manager</strong>
      <span>Create campaigns, launch dry runs or queues, and inspect delivery state.</span>
    </a>
    <a href="/admin/journeys">
      <strong>Journey Manager</strong>
      <span>Create multi-step journeys with entry rules, exits, waits, and actions.</span>
    </a>
    <a href="/admin/delivery">
      <strong>Delivery Manager</strong>
      <span>Process queued delivery and inspect jobs, records, suppressions, and tracking.</span>
    </a>
    <a href="/admin/suppressions">
      <strong>Suppressions</strong>
      <span>Review bounced, complained, unsubscribed, and manually suppressed contacts.</span>
    </a>
    <a href="/admin/analytics">
      <strong>Analytics</strong>
      <span>Review campaign metrics, events, send jobs, send records, and tracking links.</span>
    </a>
    <a href="/admin/data-sources">
      <strong>Data Sources</strong>
      <span>Manage source definitions, credentials references, mappings, and plans.</span>
    </a>
    <a href="/admin/system">
      <strong>System Diagnostics</strong>
      <span>Check schema status, provider configuration, AI configuration, and entity counts.</span>
    </a>
    <a href="/tester">
      <strong>Workflow Tester</strong>
      <span>Run manual send, campaign, delivery, suppression, and tracking workflows.</span>
    </a>
    <a href="/docs">
      <strong>API Docs</strong>
      <span>Inspect the generated OpenAPI schema and execute raw endpoints.</span>
    </a>
  </main>
  <script>
    async function loadSchemaStatus() {
      const el = document.getElementById("schemaStatus");
      try {
        const response = await fetch("/api/v1/system/diagnostics");
        const data = await response.json();
        const schema = data.schema || {};
        const counts = data.entity_counts || {};
        const countText = Object.entries(counts)
          .map(([key, value]) => `<span>${key}: ${value}</span>`)
          .join("");
        el.classList.toggle("ok", Boolean(schema.ok));
        el.classList.toggle("warn", !schema.ok);
        el.innerHTML = schema.ok
          ? `<strong>System status</strong><span>Database schema is current at revision <code>${schema.current_revision || "none"}</code>.</span><div class="system-meta">${countText}</div>`
          : `<strong>Schema migration needed</strong><span>Current revision <code>${schema.current_revision || "none"}</code>, expected <code>${schema.expected_revision || "unknown"}</code>. Run <code>${schema.migration_command}</code>.</span>`;
      } catch (error) {
        el.classList.add("error");
        el.innerHTML = `<strong>Schema status unavailable</strong><span>${error.message}</span>`;
      }
    }
    loadSchemaStatus();
  </script>
</body>
</html>"""


ADMIN_SYSTEM_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine System Diagnostics</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --green: #067647;
      --red: #b42318;
      --amber: #b54708;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 18px 22px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    h2 { margin: 0 0 12px; font-size: 16px; }
    nav { display: flex; flex-wrap: wrap; gap: 8px; }
    nav a, button {
      border: 1px solid var(--blue);
      border-radius: 8px;
      background: #fff;
      color: var(--blue);
      cursor: pointer;
      font-weight: 650;
      padding: 8px 10px;
      text-decoration: none;
    }
    button.primary { background: var(--blue); color: #fff; }
    main {
      display: grid;
      grid-template-columns: minmax(280px, 0.8fr) minmax(360px, 1.2fr);
      gap: 14px;
      max-width: 1280px;
      padding: 14px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
    }
    .span-2 { grid-column: 1 / -1; }
    .status {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border-left: 5px solid var(--line);
    }
    .status.ok { border-left-color: var(--green); }
    .status.warn { border-left-color: var(--amber); }
    .status.error { border-left-color: var(--red); }
    .status strong { display: block; font-size: 18px; margin-bottom: 4px; }
    .muted { color: var(--muted); line-height: 1.45; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfe;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
      text-transform: uppercase;
    }
    .metric strong { font-size: 22px; }
    details.table-detail {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      overflow: hidden;
    }
    details.table-detail summary {
      cursor: pointer;
      font-weight: 700;
      padding: 10px 12px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }
    th, td {
      border-top: 1px solid var(--line);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
    }
    .kv {
      display: grid;
      grid-template-columns: minmax(140px, 0.45fr) minmax(180px, 1fr);
      gap: 8px 12px;
      align-items: center;
    }
    .kv div {
      border-bottom: 1px solid var(--line);
      padding: 8px 0;
      min-width: 0;
      overflow-wrap: anywhere;
    }
    .kv div:nth-child(odd) { color: var(--muted); }
    .pill {
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 650;
    }
    .pill.ok { border-color: var(--green); color: var(--green); }
    .pill.warn { border-color: var(--amber); color: var(--amber); }
    .pill.error { border-color: var(--red); color: var(--red); }
    code, pre { font-family: var(--mono); }
    pre {
      margin: 0;
      max-height: 420px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      background: #111827;
      color: #f9fafb;
      border-radius: 8px;
      padding: 12px;
      font-size: 12px;
      line-height: 1.5;
    }
    @media (max-width: 860px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      .span-2 { grid-column: auto; }
      .kv { grid-template-columns: 1fr; }
      .kv div:nth-child(odd) { border-bottom: 0; padding-bottom: 0; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine System Diagnostics</h1>
    <nav>
      <a href="/admin">Admin</a>
      <a href="/tester">Tester</a>
      <a href="/template-editor">Template Editor</a>
      <a href="/admin/entities">Entity Workbench</a>
      <a href="/admin/audience-import">Audience Import</a>
      <a href="/admin/audiences">Audience Builder</a>
      <a href="/admin/campaigns">Campaign Manager</a>
      <a href="/admin/journeys">Journey Manager</a>
      <a href="/admin/delivery">Delivery Manager</a>
      <a href="/admin/suppressions">Suppressions</a>
      <a href="/admin/analytics">Analytics</a>
      <a href="/admin/data-sources">Data Sources</a>
      <a href="/admin/system">System</a>
      <a href="/docs">Docs</a>
    </nav>
  </header>
  <main>
    <section class="panel status span-2" id="statusPanel">
      <div>
        <strong>Loading diagnostics</strong>
        <div class="muted">Checking schema, providers, AI configuration, and entity counts.</div>
      </div>
      <button class="primary" onclick="loadDiagnostics()">Refresh</button>
    </section>

    <section class="panel">
      <h2>Schema</h2>
      <div class="kv" id="schemaDetails"></div>
    </section>

    <section class="panel">
      <h2>Configuration</h2>
      <div class="kv" id="configDetails"></div>
    </section>

    <section class="panel span-2">
      <h2>Entity Counts</h2>
      <div class="grid" id="entityCounts"></div>
    </section>

    <section class="panel span-2">
      <h2>Database Tables</h2>
      <div class="grid" id="databaseTables"></div>
    </section>

    <section class="panel span-2">
      <h2>Table Columns</h2>
      <div class="grid" id="tableColumns"></div>
    </section>

    <section class="panel span-2">
      <h2>Raw Diagnostics</h2>
      <pre id="rawJson">{}</pre>
    </section>
  </main>

  <script>
    function pill(ok, text) {
      const cls = ok ? "ok" : "warn";
      return `<span class="pill ${cls}">${text}</span>`;
    }

    function row(label, value) {
      return `<div>${label}</div><div>${value ?? ""}</div>`;
    }

    function renderStatus(data) {
      const panel = document.getElementById("statusPanel");
      const schema = data.schema || {};
      panel.classList.toggle("ok", Boolean(data.ok));
      panel.classList.toggle("warn", !data.ok);
      panel.classList.remove("error");
      panel.innerHTML = `
        <div>
          <strong>${data.ok ? "System diagnostics healthy" : "System attention needed"}</strong>
          <div class="muted">
            Schema ${schema.current_revision || "none"} / ${schema.expected_revision || "unknown"}.
            DB ${schema.db_reachable ? "reachable" : "not reachable"}.
          </div>
        </div>
        <button class="primary" onclick="loadDiagnostics()">Refresh</button>
      `;
    }

    function renderSchema(schema) {
      document.getElementById("schemaDetails").innerHTML = [
        row("Status", pill(schema.ok, schema.ok ? "Current" : "Needs migration")),
        row("DB Reachable", pill(schema.db_reachable, schema.db_reachable ? "Yes" : "No")),
        row("Current Revision", `<code>${schema.current_revision || "none"}</code>`),
        row("Expected Revision", `<code>${schema.expected_revision || "unknown"}</code>`),
        row("Migration Command", `<code>${schema.migration_command || "alembic upgrade head"}</code>`),
      ].join("");
    }

    function renderConfig(data) {
      const email = data.email_provider || {};
      const ai = data.ai || {};
      document.getElementById("configDetails").innerHTML = [
        row("Environment", data.environment || ""),
        row("Public Base URL", `<code>${data.public_base_url || ""}</code>`),
        row("Email Provider", email.provider || ""),
        row("Default From", email.default_from_email || ""),
        row("SG Configured", pill(email.sendgrid_configured, email.sendgrid_configured ? "Yes" : "No")),
        row("SMTP Configured", pill(email.smtp_configured, email.smtp_configured ? "Yes" : "No")),
        row("AI Provider", ai.provider || ""),
        row("AI Model", ai.model || ""),
        row("OpenAI Configured", pill(ai.openai_configured, ai.openai_configured ? "Yes" : "No")),
      ].join("");
    }

    function renderCounts(counts) {
      const entries = Object.entries(counts || {});
      document.getElementById("entityCounts").innerHTML = entries.length
        ? entries.map(([key, value]) => `
            <div class="metric">
              <span>${key.replaceAll("_", " ")}</span>
              <strong>${value}</strong>
            </div>
          `).join("")
        : `<div class="muted">No entity counts available.</div>`;
    }

    function renderTables(tables) {
      document.getElementById("databaseTables").innerHTML = (tables || []).length
        ? tables.map((table) => `
            <div class="metric">
              <span>table</span>
              <strong style="font-size:14px;">${table}</strong>
            </div>
          `).join("")
        : `<div class="muted">No database tables available.</div>`;
    }

    function renderTableColumns(columnsByTable) {
      const entries = Object.entries(columnsByTable || {});
      document.getElementById("tableColumns").innerHTML = entries.length
        ? entries.map(([tableName, columns]) => `
            <details class="table-detail">
              <summary>${tableName} (${columns.length})</summary>
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Nullable</th>
                    <th>PK</th>
                  </tr>
                </thead>
                <tbody>
                  ${columns.map((column) => `
                    <tr>
                      <td><code>${column.name}</code></td>
                      <td><code>${column.type}</code></td>
                      <td>${column.nullable ? "Yes" : "No"}</td>
                      <td>${column.primary_key ? "Yes" : "No"}</td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </details>
          `).join("")
        : `<div class="muted">No table columns available.</div>`;
    }

    async function loadDiagnostics() {
      const statusPanel = document.getElementById("statusPanel");
      statusPanel.classList.remove("ok", "warn", "error");
      statusPanel.innerHTML = `
        <div>
          <strong>Loading diagnostics</strong>
          <div class="muted">Checking current system status...</div>
        </div>
        <button class="primary" onclick="loadDiagnostics()">Refresh</button>
      `;
      try {
        const response = await fetch("/api/v1/system/diagnostics");
        const data = await response.json();
        if (!response.ok) throw new Error(JSON.stringify(data));
        renderStatus(data);
        renderSchema(data.schema || {});
        renderConfig(data);
        renderCounts(data.entity_counts || {});
        renderTables(data.database_tables || []);
        renderTableColumns(data.database_table_columns || {});
        document.getElementById("rawJson").textContent = JSON.stringify(data, null, 2);
      } catch (error) {
        statusPanel.classList.add("error");
        statusPanel.innerHTML = `
          <div>
            <strong>Diagnostics unavailable</strong>
            <div class="muted">${error.message}</div>
          </div>
          <button class="primary" onclick="loadDiagnostics()">Retry</button>
        `;
      }
    }

    loadDiagnostics();
  </script>
</body>
</html>"""


ADMIN_AUDIENCE_IMPORT_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Audience Import</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --green: #067647;
      --red: #b42318;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: minmax(340px, 440px) minmax(420px, 1fr);
      gap: 14px;
      padding: 14px;
      max-width: 1180px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { padding: 12px; display: grid; gap: 12px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    textarea {
      min-height: 130px;
      resize: vertical;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--blue); }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .status {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      color: var(--muted);
      background: #fbfcfe;
      line-height: 1.45;
    }
    .status.ok { border-color: #8ed6b0; color: var(--green); background: #f0fdf4; }
    .status.error { border-color: #f2a6a0; color: var(--red); background: #fff4f2; }
    pre {
      margin: 0;
      min-height: 360px;
      max-height: calc(100vh - 210px);
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    .sample {
      margin: 0;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfe;
      color: var(--muted);
      font-family: var(--mono);
      font-size: 12px;
      overflow: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 7px 6px;
      text-align: left;
      vertical-align: top;
    }
    th { color: var(--muted); font-weight: 650; background: #fbfcfe; }
    .preview {
      max-height: 310px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    @media (max-width: 900px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Audience Import</h1>
    <div class="actions">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/admin/journeys'">Journey Manager</button>
      <button class="secondary" onclick="location.href='/admin/delivery'">Delivery Manager</button>
      <button class="secondary" onclick="location.href='/admin/suppressions'">Suppressions</button>
      <button class="secondary" onclick="location.href='/admin/analytics'">Analytics</button>
      <button class="secondary" onclick="location.href='/admin/data-sources'">Data Sources</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <section>
      <div class="head"><h2>CSV Import</h2></div>
      <div class="body">
        <label>Audience name
          <input id="audienceName" />
        </label>
        <label>Description
          <textarea id="description"></textarea>
        </label>
        <label>Source
          <input id="source" value="csv_import" />
        </label>
        <label>CSV file
          <input id="file" type="file" accept=".csv,text/csv" />
        </label>
        <div class="actions">
          <button class="secondary" id="preview">Preview Mapping</button>
          <button id="import">Import CSV</button>
          <button class="secondary" id="loadAudiences">Load Audiences</button>
          <button class="secondary" id="loadContacts">Load Contacts</button>
        </div>
        <div class="status" id="status">
          Required column: email. Optional: first_name, last_name, source.
          Other columns become contact attributes.
        </div>
        <pre class="sample">email,first_name,last_name,plan,company
alex@example.com,Alex,Taylor,trial,Example Co
sam@example.com,Sam,Rivera,active,Acme Inc</pre>
        <div class="preview" id="mapping"></div>
        <div class="preview" id="sampleRows"></div>
      </div>
    </section>
    <section>
      <div class="head"><h2>Response</h2><button class="secondary" id="clear">Clear</button></div>
      <div class="body">
        <pre id="result"></pre>
      </div>
    </section>
  </main>
  <script>
    const status = document.getElementById("status");
    const result = document.getElementById("result");
    const audienceName = document.getElementById("audienceName");
    const targetOptions = ["email", "first_name", "last_name", "source", "attribute", "ignore"];
    audienceName.value = `csv-audience-${Date.now()}`;

    function setStatus(message, type = "") {
      status.className = `status ${type}`.trim();
      status.textContent = message;
    }

    function writeResult(data, ok = true) {
      result.textContent = JSON.stringify({ ok, data }, null, 2);
    }

    async function readResponse(response) {
      const text = await response.text();
      try { return text ? JSON.parse(text) : null; } catch { return text; }
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function selectedMapping() {
      const mapping = {};
      document.querySelectorAll("[data-column]").forEach((select) => {
        mapping[select.dataset.column] = select.value;
      });
      return mapping;
    }

    function renderMapping(preview) {
      const mapping = document.getElementById("mapping");
      const rows = preview.headers.map((header) => {
        const safeHeader = escapeHtml(header);
        const inferred = preview.inferred_mapping[header] || "attribute";
        const options = targetOptions.map((target) => {
          const selected = target === inferred ? " selected" : "";
          return `<option value="${target}"${selected}>${target}</option>`;
        }).join("");
        return `
          <tr>
            <td>${safeHeader}</td>
            <td><select data-column="${safeHeader}">${options}</select></td>
          </tr>
        `;
      }).join("");
      mapping.innerHTML = `
        <table>
          <thead><tr><th>CSV column</th><th>Import target</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      `;
      renderSampleRows(preview);
    }

    function renderSampleRows(preview) {
      const sampleRows = document.getElementById("sampleRows");
      if (!preview.sample_rows.length) {
        sampleRows.innerHTML = "";
        return;
      }
      const head = preview.headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("");
      const body = preview.sample_rows.map((row) => {
        const cells = preview.headers.map((header) => (
          `<td>${escapeHtml(row[header] || "")}</td>`
        )).join("");
        return `<tr>${cells}</tr>`;
      }).join("");
      sampleRows.innerHTML = `
        <table>
          <thead><tr>${head}</tr></thead>
          <tbody>${body}</tbody>
        </table>
      `;
    }

    async function previewCsv() {
      const file = document.getElementById("file").files[0];
      if (!file) {
        setStatus("Choose a CSV file first.", "error");
        return;
      }
      const form = new FormData();
      form.append("sample_limit", "8");
      form.append("file", file);
      setStatus("Reading CSV preview...");
      const response = await fetch("/api/v1/audiences/import-csv/preview", {
        method: "POST",
        body: form
      });
      const data = await readResponse(response);
      writeResult(data, response.ok);
      if (!response.ok) {
        setStatus(data.detail || "Preview failed.", "error");
        return;
      }
      renderMapping(data);
      setStatus(
        data.errors.length ? data.errors.join(" ") : `Previewed ${data.row_count} rows.`,
        data.errors.length ? "error" : "ok"
      );
    }

    async function importCsv() {
      const file = document.getElementById("file").files[0];
      if (!file) {
        setStatus("Choose a CSV file first.", "error");
        return;
      }
      const form = new FormData();
      form.append("audience_name", audienceName.value.trim());
      form.append("description", document.getElementById("description").value.trim());
      form.append("source", document.getElementById("source").value.trim() || "csv_import");
      form.append("column_mapping", JSON.stringify(selectedMapping()));
      form.append("file", file);
      setStatus("Importing CSV...");
      const response = await fetch("/api/v1/audiences/import-csv", {
        method: "POST",
        body: form
      });
      const data = await readResponse(response);
      writeResult(data, response.ok);
      if (!response.ok) {
        setStatus(data.detail || "Import failed.", "error");
        return;
      }
      setStatus(
        `Imported ${data.imported_count} contacts into audience ${data.audience_id}.`,
        "ok"
      );
    }

    async function loadJson(path) {
      const response = await fetch(path);
      const data = await readResponse(response);
      writeResult(data, response.ok);
      setStatus(
        response.ok ? `Loaded ${path}.` : `Failed to load ${path}.`,
        response.ok ? "" : "error"
      );
    }

    document.getElementById("preview").addEventListener("click", () => {
      previewCsv().catch((error) => {
        writeResult(error.message, false);
        setStatus(error.message, "error");
      });
    });
    document.getElementById("import").addEventListener("click", () => {
      importCsv().catch((error) => {
        writeResult(error.message, false);
        setStatus(error.message, "error");
      });
    });
    document.getElementById("loadAudiences").addEventListener("click", () => {
      loadJson("/api/v1/audiences/list?limit=100&offset=0");
    });
    document.getElementById("loadContacts").addEventListener("click", () => {
      loadJson("/api/v1/audiences/contacts/list?limit=100&offset=0");
    });
    document.getElementById("clear").addEventListener("click", () => {
      result.textContent = "";
    });
  </script>
</body>
</html>"""


ADMIN_AUDIENCES_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Audience Builder</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --red: #b42318;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: 280px minmax(360px, 1fr) minmax(360px, 1fr);
      gap: 14px;
      padding: 14px;
    }
    section {
      min-width: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { min-width: 0; padding: 12px; display: grid; gap: 10px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, select, textarea {
      min-width: 0;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    textarea {
      min-height: 150px;
      resize: vertical;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--blue); }
    button.danger { border-color: var(--red); color: var(--red); background: #fff; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .items {
      display: grid;
      gap: 6px;
      max-height: calc(100vh - 180px);
      overflow: auto;
    }
    .item {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 8px;
      text-align: left;
      color: var(--text);
    }
    .item small { display: block; color: var(--muted); margin-top: 3px; }
    .item.selected { border-color: var(--blue); background: #eff6ff; box-shadow: inset 3px 0 0 var(--blue); }
    .rule-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 8px;
      align-items: end;
    }
    .rule-grid button { min-height: 37px; }
    .rule-list { display: grid; gap: 6px; }
    .rule {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      background: #fbfcfe;
    }
    .rule code { color: var(--muted); font-family: var(--mono); font-size: 12px; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; }
    .chip {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      border-radius: 6px;
      padding: 5px 7px;
      font-size: 12px;
      font-weight: 600;
    }
    .contact-table {
      max-height: 260px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    .ai-audience-panel {
      border: 1px solid #c7d7fe;
      border-radius: 8px;
      background: #f7f9ff;
      padding: 10px;
      display: grid;
      gap: 8px;
    }
    .ai-audience-panel[hidden] { display: none; }
    .ai-audience-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .ai-audience-head strong { font-size: 13px; }
    .ai-audience-head span {
      color: var(--muted);
      font-size: 11px;
    }
    .ai-audience-summary {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 12px;
    }
    .ai-audience-list {
      display: grid;
      gap: 7px;
    }
    .ai-audience-card {
      border: 1px solid #dbe4ff;
      border-radius: 7px;
      background: #fff;
      padding: 9px;
      display: grid;
      gap: 4px;
    }
    .ai-audience-card.high { border-color: #f3c8c5; background: #fff7f7; }
    .ai-audience-card.medium { border-color: #f1d09a; background: #fffaf0; }
    .ai-audience-card strong { font-size: 13px; }
    .ai-audience-card p {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 7px 6px;
      text-align: left;
      vertical-align: top;
    }
    th { color: var(--muted); font-weight: 650; background: #fbfcfe; }
    td code { font-family: var(--mono); font-size: 11px; color: var(--muted); }
    pre {
      margin: 0;
      min-height: 300px;
      max-height: calc(100vh - 220px);
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    @media (max-width: 1280px) {
      main { grid-template-columns: 1fr; }
      header { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Audience Builder</h1>
    <div class="actions">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/admin/journeys'">Journey Manager</button>
      <button class="secondary" onclick="location.href='/admin/delivery'">Delivery Manager</button>
      <button class="secondary" onclick="location.href='/admin/suppressions'">Suppressions</button>
      <button class="secondary" onclick="location.href='/admin/analytics'">Analytics</button>
      <button class="secondary" onclick="location.href='/admin/data-sources'">Data Sources</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <section>
      <div class="head">
        <h2>Audiences</h2>
        <button id="refresh">Refresh</button>
      </div>
      <div class="body">
        <div class="actions">
          <button class="secondary" id="new">New</button>
          <button class="secondary" onclick="location.href='/admin/audience-import'">Import</button>
        </div>
        <div class="items" id="items"></div>
      </div>
    </section>
    <section>
      <div class="head">
        <h2>Builder</h2>
        <div class="actions">
          <button class="secondary" id="preview">Preview</button>
          <button class="secondary" id="aiAudienceReview">AI Review</button>
          <button class="secondary" id="snapshot">Snapshot</button>
          <button class="secondary" id="snapshots">Snapshots</button>
          <button id="save">Save</button>
          <button class="danger" id="delete">Delete</button>
        </div>
      </div>
      <div class="body">
        <label>Name
          <input id="name" />
        </label>
        <label>Description
          <input id="description" />
        </label>
        <label>Operator
          <select id="operator">
            <option value="and">Match all rules</option>
            <option value="or">Match any rule</option>
          </select>
        </label>
        <div class="rule-grid">
          <label>Field
            <input id="field" value="attributes.plan" />
          </label>
          <label>Comparator
            <select id="comparator">
              <option value="eq">equals</option>
              <option value="ne">does not equal</option>
              <option value="contains">contains</option>
              <option value="exists">exists</option>
              <option value="not_exists">does not exist</option>
            </select>
          </label>
          <label>Value
            <input id="value" value="trial" />
          </label>
          <button class="secondary" id="addRule">Add</button>
        </div>
        <div class="rule-list" id="rules"></div>
        <label>Rule tree JSON
          <textarea id="ruleTree"></textarea>
        </label>
        <div class="ai-audience-panel" id="aiAudiencePanel" hidden>
          <div class="ai-audience-head">
            <strong>AI Audience Review</strong>
            <span id="aiAudienceMeta"></span>
          </div>
          <ul class="ai-audience-summary" id="aiAudienceSummary"></ul>
          <div class="ai-audience-list" id="aiAudienceList"></div>
        </div>
        <div class="actions">
          <button class="secondary" id="loadContactMeta">Load Contact Fields</button>
          <button class="secondary" id="loadContactSamples">Sample Contacts</button>
        </div>
        <div>
          <h2>Core Fields</h2>
          <div class="chips" id="coreFields"></div>
        </div>
        <div>
          <h2>Attribute Fields</h2>
          <div class="chips" id="attributeFields"></div>
        </div>
        <div>
          <h2>Contact Samples</h2>
          <div class="contact-table" id="contactSamples"></div>
        </div>
      </div>
    </section>
    <section>
      <div class="head"><h2>Response</h2><button class="secondary" id="clear">Clear</button></div>
      <div class="body">
        <pre id="result"></pre>
      </div>
    </section>
  </main>
  <script>
    let selectedId = "";
    let rules = [];
    let lastContactMeta = null;
    const result = document.getElementById("result");

    function writeResult(data, ok = true) {
      result.textContent = JSON.stringify({ ok, data }, null, 2);
    }

    async function readResponse(response) {
      const text = await response.text();
      try { return text ? JSON.parse(text) : null; } catch { return text; }
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      const data = await readResponse(response);
      writeResult(data, response.ok);
      if (!response.ok) throw new Error(data.detail || `${path} failed`);
      return data;
    }

    function insertField(field) {
      document.getElementById("field").value = field;
    }

    function renderChips(containerId, fields) {
      const container = document.getElementById(containerId);
      container.textContent = "";
      fields.forEach((field) => {
        const button = document.createElement("button");
        button.className = "chip";
        button.type = "button";
        button.textContent = field;
        button.addEventListener("click", () => insertField(field));
        container.appendChild(button);
      });
    }

    function renderContacts(containerId, contacts) {
      const container = document.getElementById(containerId);
      if (!contacts.length) {
        container.textContent = "No contacts to show.";
        return;
      }
      const rows = contacts.map((contact) => {
        const attrs = Object.entries(contact.attributes || {})
          .slice(0, 8)
          .map(([key, value]) => `${escapeHtml(key)}=${escapeHtml(value)}`)
          .join("<br>");
        return `
          <tr>
            <td>${escapeHtml(contact.email)}</td>
            <td>${escapeHtml(contact.first_name || "")}</td>
            <td>${escapeHtml(contact.last_name || "")}</td>
            <td>${escapeHtml(contact.source || "")}</td>
            <td><code>${attrs}</code></td>
          </tr>
        `;
      }).join("");
      container.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Email</th>
              <th>First</th>
              <th>Last</th>
              <th>Source</th>
              <th>Attributes</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    async function loadContactMeta() {
      const data = await request(
        "/api/v1/audiences/contacts/meta?sample_limit=50&scan_limit=500"
      );
      lastContactMeta = data;
      renderChips("coreFields", data.fields || []);
      renderChips(
        "attributeFields",
        (data.attribute_keys || []).map((key) => `attributes.${key}`)
      );
      renderContacts("contactSamples", data.sample_contacts || []);
      return data;
    }

    function currentRuleTree() {
      const raw = document.getElementById("ruleTree").value.trim();
      return raw ? JSON.parse(raw) : { operator: "and", rules: [] };
    }

    function syncRuleTree() {
      const tree = {
        operator: document.getElementById("operator").value,
        rules
      };
      document.getElementById("ruleTree").value = JSON.stringify(tree, null, 2);
    }

    function renderRules() {
      const container = document.getElementById("rules");
      container.textContent = "";
      rules.forEach((rule, index) => {
        const row = document.createElement("div");
        row.className = "rule";
        const code = document.createElement("code");
        code.textContent = `${rule.field} ${rule.comparator} ${rule.value ?? ""}`;
        const remove = document.createElement("button");
        remove.className = "danger";
        remove.type = "button";
        remove.textContent = "Remove";
        remove.addEventListener("click", () => {
          rules.splice(index, 1);
          syncRuleTree();
          renderRules();
        });
        row.append(code, remove);
        container.appendChild(row);
      });
    }

    function loadRuleTree(tree) {
      const nextTree = tree && typeof tree === "object" ? tree : {};
      document.getElementById("operator").value = nextTree.operator || "and";
      rules = Array.isArray(nextTree.rules)
        ? nextTree.rules.filter((rule) => rule && rule.field)
        : [];
      syncRuleTree();
      renderRules();
    }

    function markSelected(containerId, id) {
      document.querySelectorAll(`#${containerId} .item`).forEach((item) => {
        item.classList.toggle("selected", item.dataset.id === id);
      });
    }

    function resetForm() {
      selectedId = "";
      document.getElementById("name").value = `audience-${Date.now()}`;
      document.getElementById("description").value = "";
      document.getElementById("aiAudiencePanel").hidden = true;
      loadRuleTree({ operator: "and", rules: [] });
    }

    function selectAudience(item) {
      selectedId = item.id;
      markSelected("items", selectedId);
      document.getElementById("name").value = item.name || "";
      document.getElementById("description").value = item.description || "";
      document.getElementById("aiAudiencePanel").hidden = true;
      loadRuleTree(item.rule_tree || {});
      writeResult(item);
    }

    async function loadAudiences() {
      const data = await request("/api/v1/audiences/list?limit=100&offset=0");
      const container = document.getElementById("items");
      container.textContent = "";
      data.items.forEach((item) => {
        const button = document.createElement("button");
        button.className = `item${selectedId === item.id ? " selected" : ""}`;
        button.dataset.id = item.id;
        button.type = "button";
        button.textContent = item.name;
        const detail = document.createElement("small");
        detail.textContent = `${item.status} · ${item.estimated_count} contacts`;
        button.appendChild(detail);
        button.addEventListener("click", () => selectAudience(item));
        container.appendChild(button);
      });
    }

    function addRule() {
      const field = document.getElementById("field").value.trim();
      if (!field) {
        writeResult("Field is required.", false);
        return;
      }
      const comparator = document.getElementById("comparator").value;
      const value = document.getElementById("value").value.trim();
      const rule = { field, comparator };
      if (!["exists", "not_exists"].includes(comparator)) rule.value = value;
      rules.push(rule);
      syncRuleTree();
      renderRules();
    }

    async function previewAudience() {
      const ruleTree = currentRuleTree();
      const data = await request("/api/v1/audiences/preview", {
        method: "POST",
        body: JSON.stringify({ rule_tree: ruleTree, limit: 25 })
      });
      renderContacts("contactSamples", data.sample_contacts || []);
      return data;
    }

    function selectedAudienceContext() {
      return {
        id: selectedId || null,
        name: document.getElementById("name").value.trim(),
        description: document.getElementById("description").value.trim() || null,
        rule_tree: currentRuleTree(),
      };
    }

    function renderAudienceAiReview(data) {
      const panel = document.getElementById("aiAudiencePanel");
      const meta = document.getElementById("aiAudienceMeta");
      const summary = document.getElementById("aiAudienceSummary");
      const list = document.getElementById("aiAudienceList");
      panel.hidden = false;
      meta.textContent = `${data.provider || "email-engine"} - ${data.model || "audience-analysis"}`;
      summary.innerHTML = (data.summary || [])
        .map((item) => `<li>${escapeHtml(item)}</li>`)
        .join("");
      list.innerHTML = (data.recommendations || []).map((item) => `
        <div class="ai-audience-card ${escapeHtml(item.priority || "")}">
          <strong>${escapeHtml(item.title || item.code)}</strong>
          <p>${escapeHtml(item.detail || "")}</p>
          <p>${escapeHtml(item.suggested_action || "")}</p>
        </div>
      `).join("") || '<div class="empty-state">No recommendations returned.</div>';
    }

    async function reviewAudienceWithAi() {
      const button = document.getElementById("aiAudienceReview");
      button.disabled = true;
      button.textContent = "Reviewing...";
      try {
        const preview = await previewAudience();
        const meta = lastContactMeta || await loadContactMeta();
        const data = await request("/api/v1/ai/audiences/analyze", {
          method: "POST",
          body: JSON.stringify({
            audience_context: {
              audience: selectedAudienceContext(),
              rule_tree: currentRuleTree(),
              preview,
              contact_meta: meta,
            },
            goals: [
              "Assess audience readiness for campaign launch.",
              "Identify rule, data quality, and segmentation risks.",
              "Recommend concrete next steps for the Audience Builder.",
            ],
          })
        });
        renderAudienceAiReview(data);
      } finally {
        button.disabled = false;
        button.textContent = "AI Review";
      }
    }

    async function saveAudience() {
      const payload = {
        name: document.getElementById("name").value.trim(),
        description: document.getElementById("description").value.trim() || null,
        rule_tree: currentRuleTree()
      };
      const path = selectedId ? `/api/v1/audiences/${selectedId}` : "/api/v1/audiences";
      const method = selectedId ? "PATCH" : "POST";
      const saved = await request(path, { method, body: JSON.stringify(payload) });
      selectedId = saved.id;
      await loadAudiences();
    }

    async function deleteAudience() {
      if (!selectedId) {
        writeResult("Select an audience first.", false);
        return;
      }
      await request(`/api/v1/audiences/${selectedId}`, { method: "DELETE" });
      resetForm();
      await loadAudiences();
    }

    async function createSnapshot() {
      if (!selectedId) {
        writeResult("Select or save an audience first.", false);
        return;
      }
      await request(`/api/v1/audiences/${selectedId}/snapshots`, {
        method: "POST",
        body: JSON.stringify({ metadata_json: { source: "admin_audience_builder" } })
      });
    }

    async function loadSnapshots() {
      const query = selectedId
        ? `?audience_id=${selectedId}&limit=100&offset=0`
        : "?limit=100&offset=0";
      await request(`/api/v1/audience-snapshots/list${query}`);
    }

    document.getElementById("refresh").addEventListener("click", () => {
      loadAudiences().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("new").addEventListener("click", resetForm);
    document.getElementById("addRule").addEventListener("click", addRule);
    document.getElementById("operator").addEventListener("change", syncRuleTree);
    document.getElementById("loadContactMeta").addEventListener("click", () => {
      loadContactMeta().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("loadContactSamples").addEventListener("click", () => {
      loadContactMeta().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("preview").addEventListener("click", () => {
      previewAudience().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("aiAudienceReview").addEventListener("click", () => {
      reviewAudienceWithAi().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("snapshot").addEventListener("click", () => {
      createSnapshot().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("snapshots").addEventListener("click", () => {
      loadSnapshots().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("save").addEventListener("click", () => {
      saveAudience().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("delete").addEventListener("click", () => {
      deleteAudience().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("clear").addEventListener("click", () => {
      result.textContent = "";
    });

    resetForm();
    loadAudiences()
      .then(loadContactMeta)
      .catch((error) => writeResult(error.message, false));
  </script>
</body>
</html>"""


ADMIN_CAMPAIGNS_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Campaign Manager</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --red: #b42318;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: 280px minmax(420px, .9fr) minmax(420px, 1fr);
      gap: 14px;
      padding: 14px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { padding: 12px; display: grid; gap: 10px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    textarea {
      min-height: 130px;
      resize: vertical;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--blue); }
    button.danger { border-color: var(--red); color: var(--red); background: #fff; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .items {
      display: grid;
      gap: 6px;
      max-height: calc(100vh - 180px);
      overflow: auto;
    }
    .item {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 8px;
      text-align: left;
      color: var(--text);
    }
    .item small { display: block; color: var(--muted); margin-top: 3px; }
    .item.selected { border-color: var(--blue); background: #eff6ff; box-shadow: inset 3px 0 0 var(--blue); }
    .inline {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .preview-table {
      max-height: 260px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    .test-send-panel {
      display: grid;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfcfe;
    }
    .test-send-panel[hidden] { display: none; }
    .test-send-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 8px;
    }
    .test-send-field {
      display: grid;
      gap: 3px;
      min-width: 0;
    }
    .test-send-field span {
      color: var(--muted);
      font-size: 11px;
      font-weight: 650;
      text-transform: uppercase;
    }
    .test-send-field code {
      overflow-wrap: anywhere;
      font-family: var(--mono);
      font-size: 12px;
    }
    .test-send-metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
      gap: 8px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      background: #fff;
    }
    .metric strong { display: block; font-size: 18px; }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      margin-top: 2px;
    }
    .summary-strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
      gap: 8px;
    }
    .summary-stat {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      padding: 9px;
      min-width: 0;
    }
    .summary-stat span {
      display: block;
      color: var(--muted);
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .summary-stat strong {
      display: block;
      margin-top: 3px;
      font-size: 18px;
    }
    .launch-progress-banner {
      display: grid;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fbff;
      padding: 10px;
    }
    .launch-progress-banner[hidden] { display: none; }
    .launch-progress-banner.active { border-color: #f3d39a; background: #fffaf0; }
    .launch-progress-banner.success { border-color: #b8e0c6; background: #f2fbf5; }
    .launch-progress-banner.warning { border-color: #f3d39a; background: #fffaf0; }
    .launch-progress-head,
    .launch-progress-counts {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }
    .launch-progress-head strong { font-size: 13px; }
    .launch-progress-head span,
    .launch-progress-counts {
      color: var(--muted);
      font-size: 11px;
    }
    .launch-progress-track {
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: #e8eef5;
    }
    .launch-progress-track span {
      display: block;
      height: 100%;
      min-width: 4px;
      border-radius: inherit;
      background: #186b3f;
      transition: width 180ms ease;
    }
    .launch-progress-banner.active .launch-progress-track span { background: #cf8a26; }
    .launch-progress-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .launch-progress-actions button {
      padding: 6px 8px;
      font-size: 12px;
    }
    .launch-activity {
      display: grid;
      gap: 4px;
      max-height: 130px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 7px;
      font-size: 11px;
      color: var(--muted);
    }
    .launch-activity:empty { display: none; }
    .launch-activity div {
      display: grid;
      grid-template-columns: 72px minmax(0, 1fr);
      gap: 6px;
      align-items: start;
    }
    .launch-activity strong {
      color: var(--text);
      font-weight: 700;
    }
    .test-send-events {
      max-height: 180px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    .test-send-events:empty { display: none; }
    .readiness-panel {
      display: grid;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfcfe;
    }
    .readiness-panel[hidden] { display: none; }
    .readiness-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
    }
    .readiness-card {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px;
      background: #fff;
      display: grid;
      gap: 4px;
      min-width: 0;
    }
    .readiness-card strong { font-size: 13px; }
    .readiness-card span { color: var(--muted); font-size: 12px; }
    .readiness-card.ok { border-color: #16a34a; }
    .readiness-card.warn { border-color: #d97706; }
    .readiness-card.fail { border-color: var(--red); }
    .readiness-list {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 12px;
    }
    .ai-review-panel {
      display: grid;
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfcfe;
    }
    .ai-review-panel[hidden] { display: none; }
    .ai-review-meta {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .ai-review-summary {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 12px;
    }
    .ai-review-list {
      display: grid;
      gap: 7px;
    }
    .ai-review-card {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      background: #fff;
      display: grid;
      gap: 4px;
    }
    .ai-review-card-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
    }
    .ai-review-card-head strong {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .ai-priority {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 6px;
      color: var(--muted);
      font-size: 10px;
      text-transform: uppercase;
    }
    .ai-priority-high { border-color: var(--red); color: var(--red); }
    .ai-priority-medium { border-color: #d97706; color: #92400e; }
    .ai-priority-low { border-color: #16a34a; color: #166534; }
    .ai-review-card p { margin: 0; color: var(--text); font-size: 12px; line-height: 1.35; }
    .ai-review-card small { color: var(--muted); font-size: 11px; line-height: 1.35; }
    .ai-review-card-actions {
      display: flex;
      justify-content: flex-end;
      margin-top: 2px;
    }
    .workflow-steps {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fff;
    }
    .workflow-step {
      border-left: 4px solid var(--line);
      padding: 6px 8px;
      display: grid;
      gap: 3px;
      min-width: 0;
    }
    .workflow-step strong { font-size: 12px; }
    .workflow-step span { color: var(--muted); font-size: 11px; }
    .workflow-step.ok { border-color: #16a34a; }
    .workflow-step.current { border-color: var(--blue); background: #eff6ff; }
    .workflow-step.fail { border-color: var(--red); background: #fff7f7; }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 7px 6px;
      text-align: left;
      vertical-align: top;
    }
    th { color: var(--muted); font-weight: 650; background: #fbfcfe; }
    td code { font-family: var(--mono); font-size: 11px; color: var(--muted); }
    iframe {
      width: 100%;
      min-height: 220px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    pre {
      margin: 0;
      min-height: 320px;
      max-height: calc(100vh - 220px);
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    @media (max-width: 1100px) {
      main { grid-template-columns: 1fr; }
      header { align-items: flex-start; flex-direction: column; }
      .inline { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Campaign Manager</h1>
    <div class="actions">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/admin/journeys'">Journey Manager</button>
      <button class="secondary" onclick="location.href='/admin/delivery'">Delivery Manager</button>
      <button class="secondary" onclick="location.href='/admin/suppressions'">Suppressions</button>
      <button class="secondary" onclick="location.href='/admin/analytics'">Analytics</button>
      <button class="secondary" onclick="location.href='/admin/data-sources'">Data Sources</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <section>
      <div class="head"><h2>Campaigns</h2><button id="refresh">Refresh</button></div>
      <div class="body">
        <button class="secondary" id="new">New</button>
        <div class="summary-strip" id="campaignSummary"></div>
        <div class="items" id="items"></div>
      </div>
    </section>
    <section>
      <div class="head">
        <h2>Editor</h2>
        <div class="actions">
          <button id="save">Save</button>
          <button class="secondary" id="clone">Clone</button>
          <button class="danger" id="delete">Delete</button>
        </div>
      </div>
      <div class="body">
        <label>Name
          <input id="name" />
        </label>
        <div class="inline">
          <label>Template
            <select id="template"></select>
          </label>
          <label>Audience
            <select id="audience"></select>
          </label>
        </div>
        <label>Scheduled at
          <input id="scheduledAt" type="datetime-local" />
        </label>
        <label>Audience query JSON
          <textarea id="audienceQuery"></textarea>
        </label>
        <label>Launch variables JSON
          <textarea id="variables"></textarea>
        </label>
        <label>Test recipient email
          <input id="testEmail" type="email" placeholder="you@example.com" />
        </label>
        <div class="workflow-steps" id="workflowSteps"></div>
        <div class="launch-progress-banner" id="launchProgress" hidden>
          <div class="launch-progress-head">
            <strong>Launch progress</strong>
            <span id="launchProgressStatus">Waiting</span>
          </div>
          <div class="launch-progress-track"><span id="launchProgressBar" style="width:0%"></span></div>
          <div class="launch-progress-counts" id="launchProgressCounts"></div>
          <div class="launch-progress-actions">
            <button class="secondary" type="button" id="continueLaunchPolling">Continue Polling</button>
            <button class="secondary" type="button" id="processLaunchQueue">Process Queue Now</button>
            <button class="secondary" type="button" id="viewLaunchDelivery">Open Delivery</button>
          </div>
          <div class="launch-activity" id="launchActivity"></div>
        </div>
        <div class="readiness-panel" id="readinessPanel" hidden>
          <div class="head">
            <h2>Workflow Readiness</h2>
            <span id="readinessSummary"></span>
          </div>
          <div class="readiness-grid" id="readinessGrid"></div>
          <ul class="readiness-list" id="readinessIssues"></ul>
        </div>
        <div class="ai-review-panel" id="aiReviewPanel" hidden>
          <div class="head">
            <h2>AI Campaign Review</h2>
            <span id="aiReviewSummary"></span>
          </div>
          <div class="ai-review-meta" id="aiReviewMeta"></div>
          <ul class="ai-review-summary" id="aiReviewNotes"></ul>
          <div class="ai-review-list" id="aiReviewList"></div>
        </div>
        <div class="test-send-panel" id="testSendPanel" hidden>
          <div class="head">
            <h2>Last Test Send</h2>
            <div class="actions">
              <button class="secondary" id="viewDelivery" type="button">Delivery</button>
              <button class="secondary" id="viewAnalytics" type="button">Analytics</button>
              <button class="secondary" id="viewEvents" type="button">Events</button>
              <button class="secondary" id="viewTimeline" type="button">Timeline</button>
              <button class="secondary" id="recordTestOpen" type="button">Record Open</button>
              <button class="secondary" id="recordTestClick" type="button">Record Click</button>
              <button class="secondary" id="refreshTestSend" type="button">Refresh</button>
            </div>
          </div>
          <label>Click target URL
            <input id="testClickTargetUrl" placeholder="https://email-engine.app/" />
          </label>
          <div class="test-send-metrics" id="testSendMetrics"></div>
          <div class="test-send-events" id="testSendEvents"></div>
          <div class="test-send-grid" id="testSendDetails"></div>
        </div>
        <div class="actions">
          <button class="secondary" id="previewAudience">Preview Audience</button>
          <button class="secondary" id="previewTemplate">Preview Template</button>
          <button class="secondary" id="validateCampaign">Validate</button>
          <button class="secondary" id="workflowStatus">Workflow Status</button>
          <button class="secondary" id="aiReview">AI Review</button>
          <button class="secondary" id="testPreview">Test Preview</button>
          <button class="secondary" id="testSend">Test Send</button>
          <button class="secondary" id="loadLastTestSend">Load Last Send</button>
          <button class="secondary" id="approveCampaign">Approve</button>
          <button class="secondary" id="processDue">Process Due</button>
          <button class="secondary" id="dryRun">Dry Run</button>
          <button id="launch">Queue Launch</button>
          <button class="secondary" id="analytics">Analytics</button>
          <button class="secondary" id="jobs">Jobs</button>
          <button class="secondary" id="records">Records</button>
        </div>
        <div>
          <h2>Matched Contacts</h2>
          <div class="preview-table" id="matchedContacts"></div>
        </div>
        <label>Template Preview
          <iframe id="templatePreview"></iframe>
        </label>
      </div>
    </section>
    <section>
      <div class="head"><h2>Response</h2><button class="secondary" id="clear">Clear</button></div>
      <div class="body">
        <pre id="result"></pre>
      </div>
    </section>
  </main>
  <script>
    let selectedId = "";
    let lastTestSend = null;
    let templateItems = [];
    let audienceItems = [];
    let activeLaunchJobId = "";
    let launchPollStartedAt = 0;
    const result = document.getElementById("result");

    function writeResult(data, ok = true) {
      result.textContent = JSON.stringify({ ok, data }, null, 2);
    }

    async function readResponse(response) {
      const text = await response.text();
      try { return text ? JSON.parse(text) : null; } catch { return text; }
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      const data = await readResponse(response);
      writeResult(data, response.ok);
      if (!response.ok) throw new Error(data.detail || `${path} failed`);
      return data;
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function markSelected(containerId, id) {
      document.querySelectorAll(`#${containerId} .item`).forEach((item) => {
        item.classList.toggle("selected", item.dataset.id === id);
      });
    }

    function parseJson(id, fallback) {
      const raw = document.getElementById(id).value.trim();
      return raw ? JSON.parse(raw) : fallback;
    }

    function selectedAudienceId() {
      const value = document.getElementById("audience").value;
      return value || null;
    }

    function selectedTemplateId() {
      return document.getElementById("template").value;
    }

    function selectedAudience() {
      const audienceId = selectedAudienceId();
      return audienceItems.find((item) => item.id === audienceId) || null;
    }

    function selectedTemplate() {
      const templateId = selectedTemplateId();
      return templateItems.find((item) => item.id === templateId) || null;
    }

    function templateEditorAiUrl(instruction) {
      const params = new URLSearchParams();
      const templateId = selectedTemplateId();
      if (templateId) params.set("template_id", templateId);
      if (instruction) params.set("ai_prompt", instruction);
      return `/template-editor?${params.toString()}`;
    }

    async function sampleVariablesForTemplate(templateId) {
      const data = await request(`/api/v1/templates/${templateId}/variables`);
      return data.sample_variables || {};
    }

    function displayProvider(value) {
      return String(value || "").toLowerCase() === "sendgrid" ? "SG" : (value || "email-engine");
    }

    function renderContacts(contacts) {
      const container = document.getElementById("matchedContacts");
      if (!contacts.length) {
        container.textContent = "No matching contacts.";
        return;
      }
      const rows = contacts.map((contact) => {
        const attrs = Object.entries(contact.attributes || {})
          .slice(0, 6)
          .map(([key, value]) => `${escapeHtml(key)}=${escapeHtml(value)}`)
          .join("<br>");
        return `
          <tr>
            <td>${escapeHtml(contact.email)}</td>
            <td>${escapeHtml(contact.first_name || "")}</td>
            <td>${escapeHtml(contact.last_name || "")}</td>
            <td>${escapeHtml(contact.source || "")}</td>
            <td><code>${attrs}</code></td>
          </tr>
        `;
      }).join("");
      container.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Email</th>
              <th>First</th>
              <th>Last</th>
              <th>Source</th>
              <th>Attributes</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    function renderTemplatePreview(preview) {
      const frame = document.getElementById("templatePreview");
      const doc = frame.contentDocument || frame.contentWindow.document;
      doc.open();
      doc.write(preview.html_body || "");
      doc.close();
    }

    function renderTestSendDetails(data) {
      lastTestSend = data;
      const panel = document.getElementById("testSendPanel");
      const container = document.getElementById("testSendDetails");
      panel.hidden = false;
      const fields = [
        ["Recipient", data.to_email],
        ["Campaign ID", data.campaign_id],
        ["Send Job ID", data.send_job_id],
        ["Send Record ID", data.send_record_id],
        ["Contact ID", data.contact_id],
        ["Provider Message ID", data.provider_message_id || "(none)"],
        ["Open Tracking", data.tracking_open_url],
        ["Click Tracking Base", data.tracking_click_base],
        ["Unsubscribe URL", data.unsubscribe_url]
      ];
      container.innerHTML = fields
        .filter(([, value]) => value)
        .map(([label, value]) => `
          <div class="test-send-field">
            <span>${escapeHtml(label)}</span>
            <code>${escapeHtml(value)}</code>
          </div>
        `)
        .join("");
    }

    function renderTestSendMetrics(data) {
      const container = document.getElementById("testSendMetrics");
      if (!data) {
        container.textContent = "";
        return;
      }
      const fields = [
        ["Sent", data.sent_count],
        ["Opened", data.opened_count],
        ["Clicked", data.clicked_count],
        ["Open rate", `${Math.round((data.open_rate || 0) * 100)}%`],
        ["Click rate", `${Math.round((data.click_rate || 0) * 100)}%`]
      ];
      container.innerHTML = fields.map(([label, value]) => `
        <div class="metric">
          <strong>${escapeHtml(value)}</strong>
          <span>${escapeHtml(label)}</span>
        </div>
      `).join("");
    }

    function renderTestSendEvents(data) {
      const container = document.getElementById("testSendEvents");
      const events = data?.items || [];
      if (!events.length) {
        container.textContent = "";
        return;
      }
      const rows = events.map((event) => {
        const metadata = event.metadata_json || {};
        return `
          <tr>
            <td>${escapeHtml(event.event_type)}</td>
            <td>${escapeHtml(event.occurred_at || "")}</td>
            <td>${escapeHtml(metadata.target_url || "")}</td>
          </tr>
        `;
      }).join("");
      container.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Event</th>
              <th>Occurred</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    function renderReadiness(data) {
      const panel = document.getElementById("readinessPanel");
      const summary = document.getElementById("readinessSummary");
      const grid = document.getElementById("readinessGrid");
      const issues = document.getElementById("readinessIssues");
      const validation = data.validation || {};
      const audience = data.audience_preview || {};
      const analytics = data.analytics || {};
      const cards = [
        {
          label: "Template",
          state: data.template ? "ok" : "fail",
          detail: data.template ? data.template.name : "Missing template"
        },
        {
          label: "Variables",
          state: validation.missing_variables?.length ? "fail" : "ok",
          detail: validation.missing_variables?.length
            ? validation.missing_variables.join(", ")
            : `${data.template_variables?.variables?.length || 0} user variables`
        },
        {
          label: "Audience",
          state: audience.estimated_count > 0 ? "ok" : "fail",
          detail: `${audience.estimated_count || 0} matched contacts`
        },
        {
          label: "Validation",
          state: validation.ok ? "ok" : "fail",
          detail: validation.ok ? "Ready" : `${validation.errors?.length || 0} errors`
        },
        {
          label: "Latest Send",
          state: data.latest_send_record ? "ok" : "warn",
          detail: data.latest_send_record
            ? `${data.latest_send_record.status} to ${data.latest_send_record.to_email}`
            : "No send record yet"
        },
        {
          label: "Metrics",
          state: analytics.sent_count ? "ok" : "warn",
          detail: `${analytics.sent_count || 0} sent, ${analytics.opened_count || 0} opened, ${analytics.clicked_count || 0} clicked`
        }
      ];
      panel.hidden = false;
      summary.textContent = validation.ok ? "Ready for test send" : "Needs attention";
      grid.innerHTML = cards.map((card) => `
        <div class="readiness-card ${card.state}">
          <strong>${escapeHtml(card.label)}</strong>
          <span>${escapeHtml(card.detail)}</span>
        </div>
      `).join("");
      const issueItems = [
        ...(validation.errors || []),
        ...(validation.warnings || []).map((warning) => `Warning: ${warning}`)
      ];
      issues.innerHTML = issueItems
        .map((item) => `<li>${escapeHtml(item)}</li>`)
        .join("");
    }

    function renderAiReview(data) {
      const panel = document.getElementById("aiReviewPanel");
      const summary = document.getElementById("aiReviewSummary");
      const meta = document.getElementById("aiReviewMeta");
      const notes = document.getElementById("aiReviewNotes");
      const list = document.getElementById("aiReviewList");
      const recommendations = data.recommendations || [];
      panel.hidden = false;
      summary.textContent = `${recommendations.length} recommendation${recommendations.length === 1 ? "" : "s"}`;
      meta.innerHTML = `
        <span>${escapeHtml(displayProvider(data.provider))}${data.model ? ` - ${escapeHtml(data.model)}` : ""}</span>
        <span>${data.validation?.ok ? "validation ready" : "validation needs review"}</span>
      `;
      notes.innerHTML = (data.summary || [])
        .map((item) => `<li>${escapeHtml(item)}</li>`)
        .join("");
      list.innerHTML = recommendations.slice(0, 6).map((item) => `
        <div class="ai-review-card">
          <div class="ai-review-card-head">
            <strong>${escapeHtml(item.title)}</strong>
            <span class="ai-priority ai-priority-${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span>
          </div>
          <p>${escapeHtml(item.detail)}</p>
          <small>${escapeHtml(item.suggested_instruction)}</small>
          <div class="ai-review-card-actions">
            <button
              type="button"
              class="secondary"
              data-ai-instruction="${escapeHtml(item.suggested_instruction || item.detail || "")}"
            >
              Use in Template Editor
            </button>
          </div>
        </div>
      `).join("") || `<div class="empty-state">No recommendations returned.</div>`;
      list.querySelectorAll("[data-ai-instruction]").forEach((button) => {
        button.addEventListener("click", () => {
          location.href = templateEditorAiUrl(button.dataset.aiInstruction || "");
        });
      });
    }

    function renderWorkflowSteps(data = null) {
      const container = document.getElementById("workflowSteps");
      const validation = data?.validation || {};
      const audience = data?.audience_preview || {};
      const analytics = data?.analytics || {};
      const latestSend = data?.latest_send_record;
      const steps = [
        {
          label: "1. Audience",
          state: audience.estimated_count > 0 ? "ok" : data ? "fail" : "current",
          detail: data ? `${audience.estimated_count || 0} contacts matched` : "Select or create audience"
        },
        {
          label: "2. Template",
          state: data?.template ? "ok" : data ? "fail" : "",
          detail: data?.template ? data.template.name : "Select template"
        },
        {
          label: "3. Validate",
          state: validation.ok ? "ok" : data ? "fail" : "",
          detail: data ? (validation.ok ? "Ready" : "Review errors") : "Run Workflow Status"
        },
        {
          label: "4. Test Send",
          state: latestSend ? "ok" : validation.ok ? "current" : "",
          detail: latestSend ? latestSend.status : "Send to test recipient"
        },
        {
          label: "5. Metrics",
          state: analytics.opened_count || analytics.clicked_count ? "ok" : latestSend ? "current" : "",
          detail: `${analytics.sent_count || 0} sent / ${analytics.opened_count || 0} opened / ${analytics.clicked_count || 0} clicked`
        }
      ];
      container.innerHTML = steps.map((step) => `
        <div class="workflow-step ${step.state}">
          <strong>${escapeHtml(step.label)}</strong>
          <span>${escapeHtml(step.detail)}</span>
        </div>
      `).join("");
    }

    function renderCampaignSummary(items) {
      const counts = items.reduce((acc, item) => {
        acc.total += 1;
        acc[item.status || "unknown"] = (acc[item.status || "unknown"] || 0) + 1;
        return acc;
      }, { total: 0 });
      document.getElementById("campaignSummary").innerHTML = [
        ["Total", counts.total],
        ["Draft", counts.draft || 0],
        ["Scheduled", counts.scheduled || 0],
        ["Sending", counts.sending || 0],
        ["Sent", counts.sent || 0]
      ].map(([label, value]) => `
        <div class="summary-stat">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `).join("");
    }

    function setLaunchProgress(data, tone = "active", label = "Launch progress") {
      const panel = document.getElementById("launchProgress");
      const status = document.getElementById("launchProgressStatus");
      const bar = document.getElementById("launchProgressBar");
      const counts = document.getElementById("launchProgressCounts");
      const percent = Math.max(0, Math.min(100, Number(data.percent_complete || 0) * 100));
      const elapsed = launchPollStartedAt
        ? Math.floor((Date.now() - launchPollStartedAt) / 1000)
        : 0;
      panel.hidden = false;
      panel.className = `launch-progress-banner ${tone}`;
      status.textContent = `${label} - ${data.status || "queued"} - ${percent.toFixed(0)}%${elapsed ? ` - ${elapsed}s` : ""}`;
      bar.style.width = `${Math.max(2, percent)}%`;
      counts.innerHTML = [
        ["requested", data.requested_count],
        ["queued", data.queued_count],
        ["sending", data.sending_count],
        ["active", data.active_count],
        ["processed", data.processed_count],
        ["sent", data.sent_count],
        ["failed", data.failed_count],
        ["suppressed", data.suppressed_count],
        ["remaining", data.remaining_count]
      ].filter(([, value]) => value !== undefined).map(([name, value]) => (
        `<span><strong>${escapeHtml(value)}</strong> ${escapeHtml(name)}</span>`
      )).join("");
    }

    function appendLaunchActivity(message, data = null) {
      const container = document.getElementById("launchActivity");
      const row = document.createElement("div");
      const time = document.createElement("strong");
      const detail = document.createElement("span");
      time.textContent = new Date().toLocaleTimeString();
      detail.textContent = data ? `${message}: ${JSON.stringify(data)}` : message;
      row.append(time, detail);
      container.prepend(row);
      while (container.children.length > 12) container.removeChild(container.lastElementChild);
    }

    async function pollLaunchProgress(sendJobId, maxAttempts = 24) {
      activeLaunchJobId = sendJobId;
      if (!launchPollStartedAt) launchPollStartedAt = Date.now();
      appendLaunchActivity("Polling send job", { send_job_id: sendJobId, max_attempts: maxAttempts });
      for (let index = 0; index < maxAttempts; index += 1) {
        const data = await request(`/api/v1/campaign-send-jobs/${sendJobId}/progress`);
        const active = Number(data.active_count || 0) > 0 || Number(data.remaining_count || 0) > 0;
        setLaunchProgress(data, active ? "active" : "success", active ? "Processing" : "Complete");
        appendLaunchActivity(active ? "Progress update" : "Launch complete", {
          active: data.active_count,
          remaining: data.remaining_count,
          sent: data.sent_count,
          failed: data.failed_count,
          suppressed: data.suppressed_count,
        });
        if (!active) {
          launchPollStartedAt = 0;
          return data;
        }
        await new Promise((resolve) => setTimeout(resolve, 1200));
      }
      appendLaunchActivity("Polling paused. Use Continue Polling to keep watching this send job.");
      return null;
    }

    async function processLaunchQueue() {
      if (!activeLaunchJobId) {
        writeResult("Launch a campaign or continue a selected send job first.", false);
        return;
      }
      const params = new URLSearchParams({ limit: "50", send_job_id: activeLaunchJobId });
      const data = await request(`/api/v1/delivery/process-queued?${params.toString()}`, { method: "POST" });
      appendLaunchActivity("Processed queued delivery", data);
      await pollLaunchProgress(activeLaunchJobId, 8);
    }

    function openLaunchDelivery() {
      const params = new URLSearchParams();
      if (selectedId) params.set("campaign_id", selectedId);
      if (activeLaunchJobId) params.set("send_job_id", activeLaunchJobId);
      location.href = `/admin/delivery${params.toString() ? `?${params.toString()}` : ""}`;
    }

    function resetForm() {
      selectedId = "";
      lastTestSend = null;
      document.getElementById("name").value = `campaign-${Date.now()}`;
      document.getElementById("scheduledAt").value = "";
      document.getElementById("audienceQuery").value = "{}";
      document.getElementById("variables").value = "{}";
      document.getElementById("readinessPanel").hidden = true;
      document.getElementById("aiReviewPanel").hidden = true;
      document.getElementById("testSendPanel").hidden = true;
      document.getElementById("launchProgress").hidden = true;
      document.getElementById("launchActivity").textContent = "";
      activeLaunchJobId = "";
      launchPollStartedAt = 0;
      renderWorkflowSteps();
      renderTestSendMetrics(null);
      renderTestSendEvents(null);
    }

    function clearLastTestSend() {
      lastTestSend = null;
      document.getElementById("testSendPanel").hidden = true;
      renderTestSendMetrics(null);
      renderTestSendEvents(null);
    }

    function selectCampaign(item) {
      selectedId = item.id;
      markSelected("items", selectedId);
      clearLastTestSend();
      document.getElementById("readinessPanel").hidden = true;
      document.getElementById("aiReviewPanel").hidden = true;
      document.getElementById("launchProgress").hidden = true;
      document.getElementById("launchActivity").textContent = "";
      activeLaunchJobId = "";
      launchPollStartedAt = 0;
      renderWorkflowSteps();
      document.getElementById("name").value = item.name || "";
      document.getElementById("template").value = item.template_id || "";
      document.getElementById("scheduledAt").value = item.scheduled_at
        ? item.scheduled_at.slice(0, 16)
        : "";
      document.getElementById("audienceQuery").value = JSON.stringify(
        item.audience_query || {},
        null,
        2
      );
      writeResult(item);
    }

    async function loadCampaigns() {
      const data = await request("/api/v1/campaigns/list?limit=100&offset=0");
      const container = document.getElementById("items");
      container.textContent = "";
      renderCampaignSummary(data.items || []);
      data.items.forEach((item) => {
        const button = document.createElement("button");
        button.className = `item${selectedId === item.id ? " selected" : ""}`;
        button.dataset.id = item.id;
        button.type = "button";
        button.textContent = item.name;
        const detail = document.createElement("small");
        const schedule = item.scheduled_at ? ` - scheduled ${item.scheduled_at}` : "";
        detail.textContent = `${item.status}${schedule} - ${item.id}`;
        button.appendChild(detail);
        button.addEventListener("click", () => selectCampaign(item));
        container.appendChild(button);
      });
    }

    async function loadLookups() {
      const templates = await request("/api/v1/templates/list?limit=100&offset=0");
      const audiences = await request("/api/v1/audiences/list?limit=100&offset=0");
      templateItems = templates.items;
      audienceItems = audiences.items;
      const templateSelect = document.getElementById("template");
      const audienceSelect = document.getElementById("audience");
      templateSelect.textContent = "";
      audienceSelect.textContent = "";
      audiences.items.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = item.name;
        audienceSelect.appendChild(option);
      });
      templates.items.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = item.name;
        templateSelect.appendChild(option);
      });
    }

    async function previewSelectedAudience() {
      const audience = selectedAudience();
      const ruleTree = audience ? audience.rule_tree : parseJson("audienceQuery", {});
      const data = await request("/api/v1/audiences/preview", {
        method: "POST",
        body: JSON.stringify({ rule_tree: ruleTree || {}, limit: 25 })
      });
      renderContacts(data.sample_contacts || []);
    }

    async function previewSelectedTemplate() {
      const template = selectedTemplate();
      if (!template) {
        writeResult("Select a template first.", false);
        return;
      }
      const sampleVariables = await sampleVariablesForTemplate(template.id);
      const data = await request("/api/v1/templates/preview", {
        method: "POST",
        body: JSON.stringify({
          subject: template.subject,
          html_body: template.html_body,
          css_body: template.css_body,
          text_body: template.text_body,
          variables: { ...sampleVariables, ...parseJson("variables", {}) }
        })
      });
      renderTemplatePreview(data);
    }

    async function saveCampaign() {
      const scheduledAt = document.getElementById("scheduledAt").value;
      const payload = {
        name: document.getElementById("name").value.trim(),
        template_id: selectedTemplateId(),
        audience_query: parseJson("audienceQuery", {}),
        scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : null
      };
      const path = selectedId ? `/api/v1/campaigns/${selectedId}` : "/api/v1/campaigns";
      const method = selectedId ? "PATCH" : "POST";
      const saved = await request(path, { method, body: JSON.stringify(payload) });
      selectedId = saved.id;
      await loadCampaigns();
    }

    async function deleteCampaign() {
      if (!selectedId) {
        writeResult("Select a campaign first.", false);
        return;
      }
      await request(`/api/v1/campaigns/${selectedId}`, { method: "DELETE" });
      resetForm();
      await loadCampaigns();
    }

    async function cloneCampaign() {
      if (!selectedId) {
        writeResult("Select a campaign first.", false);
        return;
      }
      const name = `${document.getElementById("name").value.trim()} copy ${Date.now()}`;
      const cloned = await request(`/api/v1/campaigns/${selectedId}/clone`, {
        method: "POST",
        body: JSON.stringify({ name })
      });
      selectCampaign(cloned);
      await loadCampaigns();
    }

    async function launchCampaign(dryRun) {
      if (!selectedId) {
        writeResult("Save or select a campaign first.", false);
        return;
      }
      const payload = {
        audience_id: selectedAudienceId(),
        variables: parseJson("variables", {}),
        dry_run: dryRun
      };
      const launch = await request(`/api/v1/campaigns/${selectedId}/launch`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      activeLaunchJobId = launch.job_id || "";
      launchPollStartedAt = Date.now();
      appendLaunchActivity(launch.dry_run ? "Dry run complete" : "Campaign queued", launch);
      setLaunchProgress({
        ...launch,
        active_count: launch.queued_count,
        processed_count: launch.dry_run ? launch.requested_count : 0,
        remaining_count: launch.dry_run ? 0 : launch.queued_count,
        percent_complete: launch.dry_run ? 1 : 0
      }, launch.dry_run ? "success" : "active", launch.dry_run ? "Dry run complete" : "Queued");
      if (!launch.dry_run && launch.job_id) {
        await pollLaunchProgress(launch.job_id);
      }
      await loadCampaigns();
    }

    async function validateCampaign() {
      if (!selectedId) {
        writeResult("Save or select a campaign first.", false);
        return;
      }
      await request(`/api/v1/campaigns/${selectedId}/validate`, {
        method: "POST",
        body: JSON.stringify({
          audience_id: selectedAudienceId(),
          variables: parseJson("variables", {}),
          dry_run: false
        })
      });
    }

    async function workflowStatus() {
      if (!selectedId) {
        writeResult("Save or select a campaign first.", false);
        return;
      }
      const data = await request(`/api/v1/campaigns/${selectedId}/workflow-status`);
      writeResult(data);
      renderWorkflowSteps(data);
      renderReadiness(data);
      renderContacts(data.audience_preview?.sample_contacts || []);
      if (data.analytics) renderTestSendMetrics(data.analytics);
      if (data.latest_send_record) {
        const links = await request(
          `/api/v1/email-send-records/${data.latest_send_record.id}/tracking-links`
        );
        renderTestSendDetails({
          campaign_id: data.latest_send_record.campaign_id,
          template_id: data.latest_send_record.template_id,
          send_job_id: data.latest_send_record.send_job_id,
          send_record_id: data.latest_send_record.id,
          contact_id: data.latest_send_record.contact_id,
          to_email: data.latest_send_record.to_email,
          provider_message_id: data.latest_send_record.provider_message_id,
          tracking_open_url: links.open_url,
          tracking_click_base: links.click_url_template,
          unsubscribe_url: data.latest_send_record.variables?.unsubscribe_url
        });
        await refreshLastTestEvents();
      }
    }

    async function reviewCampaignWithAi() {
      if (!selectedId) {
        writeResult("Save or select a campaign first.", false);
        return;
      }
      const button = document.getElementById("aiReview");
      button.disabled = true;
      button.textContent = "Reviewing...";
      const goals = [
        "Assess campaign workflow readiness.",
        "Recommend next steps for test send, launch, delivery, and analytics.",
        "Identify audience, template, validation, and performance risks."
      ];
      try {
        const workflow = await request(`/api/v1/campaigns/${selectedId}/workflow-status`);
        renderWorkflowSteps(workflow);
        renderReadiness(workflow);
        const data = await request("/api/v1/ai/campaigns/analyze", {
          method: "POST",
          body: JSON.stringify({
            campaign_context: workflow,
            goals,
          })
        });
        renderAiReview(data);
      } finally {
        button.disabled = false;
        button.textContent = "AI Review";
      }
    }

    async function testSendCampaign() {
      if (!selectedId) {
        writeResult("Save or select a campaign first.", false);
        return;
      }
      const toEmail = document.getElementById("testEmail").value.trim();
      if (!toEmail) {
        writeResult("Enter a test recipient email first.", false);
        return;
      }
      const data = await request(`/api/v1/campaigns/${selectedId}/test-send`, {
        method: "POST",
        body: JSON.stringify({
          to_email: toEmail,
          variables: parseJson("variables", {})
        })
      });
      renderTestSendDetails(data);
      renderTemplatePreview(data);
      await refreshLastTestAnalytics();
      await refreshLastTestEvents();
    }

    async function loadLastTestSend() {
      if (!selectedId) {
        writeResult("Select a campaign first.", false);
        return;
      }
      const records = await request(
        `/api/v1/email-send-records/list?campaign_id=${selectedId}&limit=1&offset=0`
      );
      const record = records.items?.[0];
      if (!record) {
        writeResult("No send records found for this campaign.", false);
        return;
      }
      const links = await request(`/api/v1/email-send-records/${record.id}/tracking-links`);
      renderTestSendDetails({
        campaign_id: record.campaign_id,
        template_id: record.template_id,
        send_job_id: record.send_job_id,
        send_record_id: record.id,
        contact_id: record.contact_id,
        to_email: record.to_email,
        provider_message_id: record.provider_message_id,
        tracking_open_url: links.open_url,
        tracking_click_base: links.click_url_template,
        unsubscribe_url: record.variables?.unsubscribe_url
      });
      await refreshLastTestAnalytics();
      await refreshLastTestEvents();
    }

    async function testPreviewCampaign() {
      if (!selectedId) {
        writeResult("Save or select a campaign first.", false);
        return;
      }
      const data = await request(`/api/v1/campaigns/${selectedId}/test-preview`, {
        method: "POST",
        body: JSON.stringify({
          variables: parseJson("variables", {})
        })
      });
      renderTemplatePreview(data);
    }

    async function approveCampaign() {
      if (!selectedId) {
        writeResult("Save or select a campaign first.", false);
        return;
      }
      const scheduledAt = document.getElementById("scheduledAt").value;
      await request(`/api/v1/campaigns/${selectedId}/approve`, {
        method: "POST",
        body: JSON.stringify({
          audience_id: selectedAudienceId(),
          variables: parseJson("variables", {}),
          scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : null,
          dry_run: false
        })
      });
      await loadCampaigns();
    }

    async function processDueCampaigns() {
      await request("/api/v1/campaigns/process-due?limit=25", { method: "POST" });
      await loadCampaigns();
    }

    async function loadAnalytics() {
      if (!selectedId) {
        writeResult("Select a campaign first.", false);
        return;
      }
      await request(`/api/v1/campaigns/${selectedId}/analytics`);
    }

    async function loadJobs() {
      const query = selectedId ? `?campaign_id=${selectedId}` : "?limit=100&offset=0";
      await request(`/api/v1/campaign-send-jobs/list${query}`);
    }

    async function loadRecords() {
      const query = selectedId ? `?campaign_id=${selectedId}` : "?limit=100&offset=0";
      await request(`/api/v1/email-send-records/list${query}`);
    }

    function openDeliveryForLastTest() {
      const params = new URLSearchParams();
      if (lastTestSend?.campaign_id) params.set("campaign_id", lastTestSend.campaign_id);
      if (lastTestSend?.send_job_id) params.set("send_job_id", lastTestSend.send_job_id);
      if (lastTestSend?.send_record_id) params.set("send_record_id", lastTestSend.send_record_id);
      location.href = `/admin/delivery${params.toString() ? `?${params.toString()}` : ""}`;
    }

    function openAnalyticsForLastTest() {
      const params = new URLSearchParams();
      if (lastTestSend?.campaign_id) params.set("campaign_id", lastTestSend.campaign_id);
      if (lastTestSend?.send_job_id) params.set("send_job_id", lastTestSend.send_job_id);
      location.href = `/admin/analytics${params.toString() ? `?${params.toString()}` : ""}`;
    }

    function openAnalyticsEventsForLastTest(view) {
      const params = new URLSearchParams();
      if (lastTestSend?.campaign_id) params.set("campaign_id", lastTestSend.campaign_id);
      if (lastTestSend?.send_job_id) params.set("send_job_id", lastTestSend.send_job_id);
      if (lastTestSend?.send_record_id) params.set("send_record_id", lastTestSend.send_record_id);
      params.set("view", view);
      location.href = `/admin/analytics?${params.toString()}`;
    }

    async function refreshLastTestAnalytics() {
      if (!lastTestSend?.campaign_id) return null;
      const params = new URLSearchParams();
      if (lastTestSend.send_job_id) params.set("send_job_id", lastTestSend.send_job_id);
      const suffix = params.toString() ? `?${params.toString()}` : "";
      const data = await request(`/api/v1/campaigns/${lastTestSend.campaign_id}/analytics${suffix}`);
      renderTestSendMetrics(data);
      return data;
    }

    async function refreshLastTestEvents() {
      if (!lastTestSend?.send_record_id) return null;
      const params = new URLSearchParams();
      params.set("send_record_id", lastTestSend.send_record_id);
      params.set("limit", "10");
      params.set("offset", "0");
      const data = await request(`/api/v1/events/list?${params.toString()}`);
      renderTestSendEvents(data);
      return data;
    }

    async function refreshLastTestSend() {
      if (!lastTestSend?.send_record_id) {
        writeResult("Run a test send first.", false);
        return;
      }
      await refreshLastTestAnalytics();
      await refreshLastTestEvents();
    }

    async function recordTestOpen() {
      if (!lastTestSend?.send_record_id) {
        writeResult("Run a test send first.", false);
        return;
      }
      await request(`/api/v1/tests/email-send-records/${lastTestSend.send_record_id}/open`, {
        method: "POST"
      });
      await refreshLastTestAnalytics();
      await refreshLastTestEvents();
    }

    async function recordTestClick() {
      if (!lastTestSend?.send_record_id) {
        writeResult("Run a test send first.", false);
        return;
      }
      const params = new URLSearchParams();
      const targetUrl = document.getElementById("testClickTargetUrl").value.trim();
      if (targetUrl) params.set("target_url", targetUrl);
      const suffix = params.toString() ? `?${params.toString()}` : "";
      await request(`/api/v1/tests/email-send-records/${lastTestSend.send_record_id}/click${suffix}`, {
        method: "POST"
      });
      await refreshLastTestAnalytics();
      await refreshLastTestEvents();
    }

    document.getElementById("refresh").addEventListener("click", () => {
      loadCampaigns().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("new").addEventListener("click", resetForm);
    document.getElementById("save").addEventListener("click", () => {
      saveCampaign().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("previewAudience").addEventListener("click", () => {
      previewSelectedAudience().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("previewTemplate").addEventListener("click", () => {
      previewSelectedTemplate().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("audience").addEventListener("change", () => {
      previewSelectedAudience().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("template").addEventListener("change", () => {
      previewSelectedTemplate().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("delete").addEventListener("click", () => {
      deleteCampaign().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("clone").addEventListener("click", () => {
      cloneCampaign().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("dryRun").addEventListener("click", () => {
      launchCampaign(true).catch((error) => writeResult(error.message, false));
    });
    document.getElementById("validateCampaign").addEventListener("click", () => {
      validateCampaign().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("workflowStatus").addEventListener("click", () => {
      workflowStatus().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("aiReview").addEventListener("click", () => {
      reviewCampaignWithAi().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("testPreview").addEventListener("click", () => {
      testPreviewCampaign().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("testSend").addEventListener("click", () => {
      testSendCampaign().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("loadLastTestSend").addEventListener("click", () => {
      loadLastTestSend().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("viewDelivery").addEventListener("click", openDeliveryForLastTest);
    document.getElementById("viewAnalytics").addEventListener("click", openAnalyticsForLastTest);
    document.getElementById("viewEvents").addEventListener("click", () => {
      openAnalyticsEventsForLastTest("events");
    });
    document.getElementById("viewTimeline").addEventListener("click", () => {
      openAnalyticsEventsForLastTest("timeline");
    });
    document.getElementById("recordTestOpen").addEventListener("click", () => {
      recordTestOpen().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("recordTestClick").addEventListener("click", () => {
      recordTestClick().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("refreshTestSend").addEventListener("click", () => {
      refreshLastTestSend().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("approveCampaign").addEventListener("click", () => {
      approveCampaign().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("processDue").addEventListener("click", () => {
      processDueCampaigns().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("launch").addEventListener("click", () => {
      launchCampaign(false).catch((error) => writeResult(error.message, false));
    });
    document.getElementById("continueLaunchPolling").addEventListener("click", () => {
      if (!activeLaunchJobId) {
        writeResult("Launch a campaign first.", false);
        return;
      }
      pollLaunchProgress(activeLaunchJobId, 24).catch((error) => writeResult(error.message, false));
    });
    document.getElementById("processLaunchQueue").addEventListener("click", () => {
      processLaunchQueue().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("viewLaunchDelivery").addEventListener("click", openLaunchDelivery);
    document.getElementById("analytics").addEventListener("click", () => {
      loadAnalytics().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("jobs").addEventListener("click", () => {
      loadJobs().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("records").addEventListener("click", () => {
      loadRecords().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("clear").addEventListener("click", () => {
      result.textContent = "";
    });

    resetForm();
    loadLookups()
      .then(loadCampaigns)
      .catch((error) => writeResult(error.message, false));
  </script>
</body>
</html>"""


ADMIN_JOURNEYS_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Journey Manager</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --red: #b42318;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: 300px minmax(420px, .9fr) minmax(420px, 1fr);
      gap: 14px;
      padding: 14px;
    }
    section {
      min-width: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { min-width: 0; padding: 12px; display: grid; gap: 10px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, select, textarea {
      min-width: 0;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    textarea {
      min-height: 100px;
      resize: vertical;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--blue); }
    button.danger { border-color: var(--red); color: var(--red); background: #fff; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .inline { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .items {
      display: grid;
      gap: 6px;
      max-height: calc(100vh - 190px);
      overflow: auto;
    }
    .item {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 8px;
      text-align: left;
      color: var(--text);
    }
    .item small { display: block; color: var(--muted); margin-top: 3px; }
    .item.selected { border-color: var(--blue); background: #eff6ff; box-shadow: inset 3px 0 0 var(--blue); }
    pre {
      margin: 0;
      min-height: 300px;
      max-height: calc(100vh - 220px);
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    .graph {
      min-height: 360px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafc;
    }
    .graph-canvas {
      position: relative;
      min-width: 920px;
      min-height: 520px;
    }
    .graph svg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 1;
    }
    .graph-edge-label {
      position: absolute;
      z-index: 3;
      width: 190px;
      max-height: 74px;
      overflow: auto;
      padding: 5px 7px;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      background: rgba(255, 255, 255, .94);
      color: #475569;
      font-size: 11px;
      line-height: 1.3;
      white-space: normal;
      overflow-wrap: anywhere;
      pointer-events: none;
      box-shadow: 0 1px 2px rgba(15, 23, 42, .08);
    }
	    .graph-node {
	      position: absolute;
	      z-index: 2;
	      width: 220px;
	      min-height: 112px;
	      display: grid;
	      gap: 6px;
	      align-content: start;
	      border: 1px solid var(--line);
	      border-left: 5px solid var(--muted);
	      border-radius: 8px;
	      background: #fff;
	      padding: 10px;
	      box-shadow: 0 1px 2px rgba(15, 23, 42, .08);
	      white-space: normal;
	    }
	    .graph-node.active { border-left-color: var(--blue); }
	    .graph-node.failed { border-left-color: var(--red); }
	    .graph-node.visited { border-left-color: #047857; }
    .graph-title { font-weight: 750; line-height: 1.25; overflow-wrap: anywhere; }
    .graph-meta {
      color: var(--muted);
      font-family: var(--mono);
      font-size: 11px;
      line-height: 1.4;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .ai-journey-panel {
      display: grid;
      gap: 10px;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 10px;
      background: #eff6ff;
    }
    .ai-journey-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
    }
    .ai-journey-head strong { display: block; }
    .ai-journey-head small { color: var(--muted); }
    .ai-journey-summary {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
    }
    .ai-journey-list { display: grid; gap: 8px; }
    .ai-journey-card {
      display: grid;
      gap: 5px;
      border: 1px solid var(--line);
      border-left: 5px solid #64748b;
      border-radius: 7px;
      background: #fff;
      padding: 9px;
    }
    .ai-journey-card.high { border-left-color: var(--red); }
    .ai-journey-card.medium { border-left-color: #d97706; }
    .ai-journey-card.low { border-left-color: #047857; }
    .ai-journey-card p { margin: 0; color: var(--muted); line-height: 1.4; }
    @media (max-width: 1280px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      .inline { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Journey Manager</h1>
    <div class="actions">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/admin/journeys'">Journey Manager</button>
      <button class="secondary" onclick="location.href='/admin/delivery'">Delivery Manager</button>
      <button class="secondary" onclick="location.href='/admin/suppressions'">Suppressions</button>
      <button class="secondary" onclick="location.href='/admin/analytics'">Analytics</button>
      <button class="secondary" onclick="location.href='/admin/data-sources'">Data Sources</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <section>
      <div class="head"><h2>Journeys</h2><button id="refreshJourneys">Refresh</button></div>
      <div class="body">
        <button class="secondary" id="newJourney">New Journey</button>
        <div class="items" id="journeys"></div>
      </div>
    </section>
    <section>
      <div class="head">
        <h2>Journey Editor</h2>
        <div class="actions">
          <button id="saveJourney">Save Journey</button>
          <button class="danger" id="deleteJourney">Delete Journey</button>
        </div>
      </div>
      <div class="body">
        <label>Name
          <input id="journeyName" />
        </label>
        <div class="inline">
          <label>Status
            <select id="journeyStatus">
              <option value="draft">draft</option>
              <option value="active">active</option>
              <option value="paused">paused</option>
              <option value="archived">archived</option>
            </select>
          </label>
          <label>Description
            <input id="journeyDescription" />
          </label>
        </div>
        <label>Entry rule tree JSON
          <textarea id="entryRuleTree"></textarea>
        </label>
        <label>Exit rule tree JSON
          <textarea id="exitRuleTree"></textarea>
        </label>
        <label>Metadata JSON
          <textarea id="journeyMetadata"></textarea>
        </label>
        <div class="head">
          <h2>Steps</h2>
          <div class="actions">
            <button class="secondary" id="loadGraph">Graph</button>
            <button class="secondary" id="newStep">New Step</button>
          </div>
        </div>
        <div class="actions">
          <button id="saveStep">Save Step</button>
          <button class="danger" id="deleteStep">Delete Step</button>
        </div>
        <div class="inline">
          <label>Step name
            <input id="stepName" />
          </label>
          <label>Step type
            <select id="stepType">
              <option value="send_email">send_email</option>
              <option value="wait">wait</option>
              <option value="branch">branch</option>
              <option value="update_contact">update_contact</option>
              <option value="webhook">webhook</option>
            </select>
          </label>
        </div>
        <label>Position
          <input id="stepPosition" type="number" value="0" />
        </label>
        <label>Step config JSON
          <textarea id="stepConfig"></textarea>
        </label>
        <div class="items" id="steps"></div>
        <div class="head">
          <h2>Execution</h2>
          <button class="secondary" id="loadEnrollments">Load Enrollments</button>
        </div>
        <div class="actions">
          <button id="enrollContact">Enroll Contact</button>
          <button id="processDue">Process Due</button>
          <button class="secondary" id="loadExecutions">Step History</button>
        </div>
        <label>Contact id
          <input id="contactId" />
        </label>
        <label>Enrollment variables JSON
          <textarea id="enrollmentVariables"></textarea>
        </label>
      </div>
    </section>
    <section>
      <div class="head">
        <h2>Journey Graph</h2>
        <div class="actions">
          <button class="secondary" id="refreshGraph">Refresh</button>
          <button class="secondary" id="aiJourneyReview">AI Review</button>
        </div>
      </div>
      <div class="body">
        <div class="ai-journey-panel" id="aiJourneyPanel" hidden>
          <div class="ai-journey-head">
            <div>
              <strong>AI Journey Review</strong>
              <small id="aiJourneyMeta">Review the selected journey path and execution state.</small>
            </div>
          </div>
          <ul class="ai-journey-summary" id="aiJourneySummary"></ul>
          <div class="ai-journey-list" id="aiJourneyList"></div>
        </div>
        <div class="graph" id="graph"></div>
        <div class="head"><h2>Response</h2><button class="secondary" id="clear">Clear</button></div>
        <pre id="result"></pre>
      </div>
    </section>
  </main>
  <script>
    let selectedJourneyId = "";
    let selectedStepId = "";
    let selectedJourney = null;
    let lastJourneyGraph = null;
    const result = document.getElementById("result");

    function writeResult(data, ok = true) {
      result.textContent = JSON.stringify({ ok, data }, null, 2);
    }

    async function readResponse(response) {
      const text = await response.text();
      try { return text ? JSON.parse(text) : null; } catch { return text; }
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      const data = await readResponse(response);
      writeResult(data, response.ok);
      if (!response.ok) throw new Error(data.detail || `${path} failed`);
      return data;
    }

    function markSelected(containerId, id) {
      document.querySelectorAll(`#${containerId} .item`).forEach((item) => {
        item.classList.toggle("selected", item.dataset.id === id);
      });
    }

    function parseJson(id, fallback) {
      const raw = document.getElementById(id).value.trim();
      return raw ? JSON.parse(raw) : fallback;
    }

    function hideJourneyAiReview() {
      document.getElementById("aiJourneyPanel").hidden = true;
      document.getElementById("aiJourneySummary").textContent = "";
      document.getElementById("aiJourneyList").textContent = "";
    }

    function resetJourney() {
      selectedJourneyId = "";
      selectedJourney = null;
      lastJourneyGraph = null;
      hideJourneyAiReview();
      document.getElementById("journeyName").value = `journey-${Date.now()}`;
      document.getElementById("journeyStatus").value = "draft";
      document.getElementById("journeyDescription").value = "";
      document.getElementById("entryRuleTree").value = JSON.stringify(
        { operator: "and", rules: [] },
        null,
        2
      );
      document.getElementById("exitRuleTree").value = "{}";
      document.getElementById("journeyMetadata").value = "{}";
      resetStep();
      renderSteps([]);
      document.getElementById("graph").textContent = "";
    }

    function resetStep() {
      selectedStepId = "";
      document.getElementById("stepName").value = `step-${Date.now()}`;
      document.getElementById("stepType").value = "send_email";
      document.getElementById("stepPosition").value = "0";
      document.getElementById("stepConfig").value = JSON.stringify(
        {
          template_id: "",
          campaign_id: null,
          wait_seconds: 0,
          variables: {},
          next_step_id: "",
          branches: [
            {
              label: "matched",
              condition: { field: "attributes.segment", comparator: "eq", value: "vip" },
              next_step_id: ""
            }
          ],
          default_next_step_id: ""
        },
        null,
        2
      );
      document.getElementById("contactId").value = "";
      document.getElementById("enrollmentVariables").value = "{}";
    }

    function selectJourney(item) {
      selectedJourneyId = item.id;
      selectedJourney = item;
      selectedStepId = "";
      lastJourneyGraph = null;
      hideJourneyAiReview();
      markSelected("journeys", selectedJourneyId);
      document.getElementById("journeyName").value = item.name || "";
      document.getElementById("journeyStatus").value = item.status || "draft";
      document.getElementById("journeyDescription").value = item.description || "";
      document.getElementById("entryRuleTree").value = JSON.stringify(
        item.entry_rule_tree || {},
        null,
        2
      );
      document.getElementById("exitRuleTree").value = JSON.stringify(
        item.exit_rule_tree || {},
        null,
        2
      );
      document.getElementById("journeyMetadata").value = JSON.stringify(
        item.metadata_json || {},
        null,
        2
      );
      resetStep();
      renderSteps(item.steps || []);
      writeResult(item);
      loadGraph().catch((error) => writeResult(error.message, false));
    }

    function selectStep(item) {
      selectedStepId = item.id;
      markSelected("steps", selectedStepId);
      document.getElementById("stepName").value = item.name || "";
      document.getElementById("stepType").value = item.step_type || "send_email";
      document.getElementById("stepPosition").value = item.position || 0;
      document.getElementById("stepConfig").value = JSON.stringify(item.config || {}, null, 2);
      writeResult(item);
    }

    function renderSteps(steps) {
      const container = document.getElementById("steps");
      container.textContent = "";
      steps
        .slice()
        .sort((left, right) => left.position - right.position)
        .forEach((item) => {
          const button = document.createElement("button");
          button.className = `item${selectedStepId === item.id ? " selected" : ""}`;
          button.dataset.id = item.id;
          button.type = "button";
          button.textContent = `${item.position}. ${item.name}`;
          const detail = document.createElement("small");
          detail.textContent = `${item.step_type} - ${item.id}`;
          button.appendChild(detail);
          button.addEventListener("click", () => selectStep(item));
          container.appendChild(button);
        });
    }

    function renderGraph(graph) {
      const container = document.getElementById("graph");
      container.textContent = "";
      if (!graph.nodes.length) {
        container.textContent = "No steps to render.";
        return;
      }
      const canvas = document.createElement("div");
      canvas.className = "graph-canvas";
      const maxX = Math.max(...graph.nodes.map((node) => node.x)) + 280;
      const maxY = Math.max(...graph.nodes.map((node) => node.y)) + 180;
      canvas.style.width = `${Math.max(maxX, 920)}px`;
      canvas.style.height = `${Math.max(maxY, 520)}px`;

      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", `0 0 ${Math.max(maxX, 920)} ${Math.max(maxY, 520)}`);
      const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
      marker.setAttribute("id", "arrow");
      marker.setAttribute("viewBox", "0 0 10 10");
      marker.setAttribute("refX", "9");
      marker.setAttribute("refY", "5");
      marker.setAttribute("markerWidth", "6");
      marker.setAttribute("markerHeight", "6");
      marker.setAttribute("orient", "auto-start-reverse");
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
      path.setAttribute("fill", "#64748b");
      marker.appendChild(path);
      const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      defs.appendChild(marker);
      svg.appendChild(defs);

      const byId = new Map(graph.nodes.map((node) => [node.id, node]));
      const edgeLabels = [];
      graph.edges.forEach((edge) => {
        const source = byId.get(edge.source);
        const target = byId.get(edge.target);
        if (!source || !target) return;
	        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
	        line.setAttribute("x1", String(source.x + 220));
	        line.setAttribute("y1", String(source.y + 56));
	        line.setAttribute("x2", String(target.x));
	        line.setAttribute("y2", String(target.y + 56));
	        line.setAttribute("stroke", edge.edge_type === "branch" ? "#2563eb" : "#64748b");
	        line.setAttribute("stroke-width", "2");
        line.setAttribute("marker-end", "url(#arrow)");
        svg.appendChild(line);
        if (edge.label || edge.condition) {
	          edgeLabels.push({
	            x: Math.max(8, ((source.x + target.x + 220) / 2) - 95),
	            y: Math.max(8, ((source.y + target.y) / 2) + 22),
	            text: edge.condition
	              ? `${edge.label || edge.edge_type}: ${JSON.stringify(edge.condition)}`
	              : edge.label
	          });
        }
      });
      canvas.appendChild(svg);

      graph.nodes.forEach((node) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = `graph-node ${node.state}`;
        card.style.left = `${node.x}px`;
        card.style.top = `${node.y}px`;
        const title = document.createElement("div");
        title.className = "graph-title";
        title.textContent = `${node.position}. ${node.label}`;
        const meta = document.createElement("div");
        meta.className = "graph-meta";
        meta.textContent = [
          node.step_type,
          `state=${node.state}`,
          `active=${node.counts.active_count}`,
          `done=${node.counts.completed_count}`,
          `failed=${node.counts.failed_count}`,
          `queued=${node.counts.queued_send_count}`
        ].join(" | ");
        const error = document.createElement("div");
        error.className = "graph-meta";
        error.textContent = node.recent_error ? `error=${node.recent_error}` : node.step_id;
        card.appendChild(title);
        card.appendChild(meta);
        card.appendChild(error);
        card.addEventListener("click", () => {
          const step = (selectedJourney?.steps || []).find((item) => item.id === node.step_id);
          if (step) selectStep(step);
          writeResult(node);
        });
        canvas.appendChild(card);
      });

      edgeLabels.forEach((item) => {
        const label = document.createElement("div");
        label.className = "graph-edge-label";
        label.style.left = `${item.x}px`;
        label.style.top = `${item.y}px`;
        label.textContent = item.text;
        canvas.appendChild(label);
      });

      container.appendChild(canvas);
    }

    async function loadJourneys() {
      const data = await request("/api/v1/journeys/list?limit=100&offset=0");
      const container = document.getElementById("journeys");
      container.textContent = "";
      data.items.forEach((item) => {
        const button = document.createElement("button");
        button.className = `item${selectedJourneyId === item.id ? " selected" : ""}`;
        button.dataset.id = item.id;
        button.type = "button";
        button.textContent = item.name;
        const detail = document.createElement("small");
        detail.textContent = `${item.status} - ${item.steps.length} steps - ${item.id}`;
        button.appendChild(detail);
        button.addEventListener("click", () => selectJourney(item));
        container.appendChild(button);
      });
    }

    async function refreshSelectedJourney() {
      if (!selectedJourneyId) return;
      const data = await request(`/api/v1/journeys/${selectedJourneyId}`);
      selectJourney(data);
      await loadJourneys();
    }

    async function saveJourney() {
      const payload = {
        name: document.getElementById("journeyName").value.trim(),
        description: document.getElementById("journeyDescription").value.trim() || null,
        entry_rule_tree: parseJson("entryRuleTree", {}),
        exit_rule_tree: parseJson("exitRuleTree", {}),
        metadata_json: parseJson("journeyMetadata", {})
      };
      if (selectedJourneyId) payload.status = document.getElementById("journeyStatus").value;
      const path = selectedJourneyId
        ? `/api/v1/journeys/${selectedJourneyId}`
        : "/api/v1/journeys";
      const method = selectedJourneyId ? "PATCH" : "POST";
      const saved = await request(path, { method, body: JSON.stringify(payload) });
      selectJourney(saved);
      await loadJourneys();
    }

    async function deleteJourney() {
      if (!selectedJourneyId) {
        writeResult("Select a journey first.", false);
        return;
      }
      await request(`/api/v1/journeys/${selectedJourneyId}`, { method: "DELETE" });
      resetJourney();
      await loadJourneys();
    }

    async function saveStep() {
      if (!selectedJourneyId) {
        writeResult("Select or save a journey first.", false);
        return;
      }
      const payload = {
        name: document.getElementById("stepName").value.trim(),
        step_type: document.getElementById("stepType").value,
        position: Number(document.getElementById("stepPosition").value || 0),
        config: parseJson("stepConfig", {})
      };
      const path = selectedStepId
        ? `/api/v1/journey-steps/${selectedStepId}`
        : `/api/v1/journeys/${selectedJourneyId}/steps`;
      const method = selectedStepId ? "PATCH" : "POST";
      const saved = await request(path, { method, body: JSON.stringify(payload) });
      selectedStepId = saved.id;
      await refreshSelectedJourney();
    }

    async function deleteStep() {
      if (!selectedStepId) {
        writeResult("Select a journey step first.", false);
        return;
      }
      await request(`/api/v1/journey-steps/${selectedStepId}`, { method: "DELETE" });
      resetStep();
      await refreshSelectedJourney();
    }

    async function enrollContact() {
      if (!selectedJourneyId) {
        writeResult("Select or save a journey first.", false);
        return;
      }
      const contactId = document.getElementById("contactId").value.trim();
      if (!contactId) {
        writeResult("Enter a contact id.", false);
        return;
      }
      await request(`/api/v1/journeys/${selectedJourneyId}/enrollments`, {
        method: "POST",
        body: JSON.stringify({
          contact_id: contactId,
          variables: parseJson("enrollmentVariables", {})
        })
      });
      await loadEnrollments();
    }

    async function loadEnrollments() {
      const params = new URLSearchParams({ limit: "100", offset: "0" });
      if (selectedJourneyId) params.set("journey_id", selectedJourneyId);
      return request(`/api/v1/journey-enrollments/list?${params.toString()}`);
    }

    async function loadExecutions() {
      const params = new URLSearchParams({ limit: "100", offset: "0" });
      if (selectedJourneyId) params.set("journey_id", selectedJourneyId);
      return request(`/api/v1/journey-step-executions/list?${params.toString()}`);
    }

    async function loadGraph() {
      if (!selectedJourneyId) {
        writeResult("Select or save a journey first.", false);
        return null;
      }
      const graph = await request(`/api/v1/journeys/${selectedJourneyId}/graph`);
      lastJourneyGraph = graph;
      renderGraph(graph);
      return graph;
    }

    function renderJourneyAiReview(data) {
      const panel = document.getElementById("aiJourneyPanel");
      const summary = document.getElementById("aiJourneySummary");
      const list = document.getElementById("aiJourneyList");
      document.getElementById("aiJourneyMeta").textContent = `${data.provider} / ${data.model}`;
      summary.textContent = "";
      list.textContent = "";
      (data.summary || []).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        summary.appendChild(li);
      });
      (data.recommendations || []).forEach((item) => {
        const card = document.createElement("div");
        card.className = `ai-journey-card ${item.priority || "low"}`;
        const title = document.createElement("strong");
        title.textContent = `${(item.priority || "low").toUpperCase()} - ${item.title}`;
        const detail = document.createElement("p");
        detail.textContent = item.detail;
        const action = document.createElement("p");
        action.textContent = item.suggested_action;
        card.appendChild(title);
        card.appendChild(detail);
        card.appendChild(action);
        list.appendChild(card);
      });
      panel.hidden = false;
    }

    async function reviewJourneyWithAi() {
      if (!selectedJourneyId) {
        writeResult("Select or save a journey first.", false);
        return;
      }
      const button = document.getElementById("aiJourneyReview");
      button.disabled = true;
      button.textContent = "Reviewing...";
      try {
        const graph = lastJourneyGraph || await loadGraph();
        const enrollmentParams = new URLSearchParams({ limit: "100", offset: "0", journey_id: selectedJourneyId });
        const executionParams = new URLSearchParams({ limit: "100", offset: "0", journey_id: selectedJourneyId });
        const [enrollments, executions] = await Promise.all([
          request(`/api/v1/journey-enrollments/list?${enrollmentParams.toString()}`),
          request(`/api/v1/journey-step-executions/list?${executionParams.toString()}`)
        ]);
        const data = await request("/api/v1/ai/journeys/analyze", {
          method: "POST",
          body: JSON.stringify({
            journey_context: {
              journey: selectedJourney,
              graph,
              enrollments,
              executions
            },
            goals: ["Assess journey structure and execution readiness"]
          })
        });
        renderJourneyAiReview(data);
      } finally {
        button.disabled = false;
        button.textContent = "AI Review";
      }
    }

    async function processDue() {
      const params = new URLSearchParams({ limit: "25" });
      if (selectedJourneyId) params.set("journey_id", selectedJourneyId);
      await request(`/api/v1/journeys/process?${params.toString()}`, { method: "POST" });
      await loadEnrollments();
      await refreshSelectedJourney();
      await loadGraph();
    }

    document.getElementById("refreshJourneys").addEventListener("click", () => {
      loadJourneys().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("newJourney").addEventListener("click", resetJourney);
    document.getElementById("saveJourney").addEventListener("click", () => {
      saveJourney().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("deleteJourney").addEventListener("click", () => {
      deleteJourney().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("newStep").addEventListener("click", resetStep);
    document.getElementById("loadGraph").addEventListener("click", () => {
      loadGraph().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("refreshGraph").addEventListener("click", () => {
      loadGraph().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("aiJourneyReview").addEventListener("click", () => {
      reviewJourneyWithAi().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("saveStep").addEventListener("click", () => {
      saveStep().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("deleteStep").addEventListener("click", () => {
      deleteStep().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("enrollContact").addEventListener("click", () => {
      enrollContact().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("loadEnrollments").addEventListener("click", () => {
      loadEnrollments().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("loadExecutions").addEventListener("click", () => {
      loadExecutions().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("processDue").addEventListener("click", () => {
      processDue().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("clear").addEventListener("click", () => {
      result.textContent = "";
    });

    resetJourney();
    loadJourneys().catch((error) => writeResult(error.message, false));
  </script>
</body>
</html>"""


ADMIN_DELIVERY_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Delivery Manager</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: minmax(520px, .9fr) minmax(420px, 1.1fr);
      gap: 14px;
      padding: 14px;
    }
    section {
      min-width: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { min-width: 0; padding: 12px; display: grid; gap: 10px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, select {
      min-width: 0;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--blue); }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .inline {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 10px;
    }
    .ai-delivery-panel {
      border: 1px solid #c7d7fe;
      border-radius: 8px;
      background: #f7f9ff;
      padding: 10px;
      display: grid;
      gap: 8px;
    }
    .ai-delivery-panel[hidden] { display: none; }
    .ai-delivery-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .ai-delivery-head strong { font-size: 13px; }
    .ai-delivery-head span {
      color: var(--muted);
      font-size: 11px;
    }
    .ai-delivery-summary {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 12px;
    }
    .ai-delivery-list {
      display: grid;
      gap: 7px;
    }
    .ai-delivery-card {
      border: 1px solid #dbe4ff;
      border-radius: 7px;
      background: #fff;
      padding: 9px;
      display: grid;
      gap: 4px;
    }
    .ai-delivery-card.high { border-color: #f3c8c5; background: #fff7f7; }
    .ai-delivery-card.medium { border-color: #f1d09a; background: #fffaf0; }
    .ai-delivery-card strong { font-size: 13px; }
    .ai-delivery-card p {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    pre {
      margin: 0;
      min-height: calc(100vh - 180px);
      max-height: calc(100vh - 180px);
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    @media (max-width: 1000px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      .inline { grid-template-columns: 1fr; }
      pre { min-height: 360px; max-height: 520px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Delivery Manager</h1>
    <div class="actions">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/admin/journeys'">Journey Manager</button>
      <button class="secondary" onclick="location.href='/admin/delivery'">Delivery Manager</button>
      <button class="secondary" onclick="location.href='/admin/suppressions'">Suppressions</button>
      <button class="secondary" onclick="location.href='/admin/analytics'">Analytics</button>
      <button class="secondary" onclick="location.href='/admin/data-sources'">Data Sources</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <section>
      <div class="head"><h2>Operations</h2></div>
      <div class="body">
        <div class="inline">
          <label>Campaign
            <select id="campaignId">
              <option value="">All campaigns</option>
            </select>
          </label>
          <label>Send job
            <select id="sendJobId">
              <option value="">All send jobs</option>
            </select>
          </label>
        </div>
        <div class="inline">
          <label>Send record
            <select id="sendRecordId">
              <option value="">Select send record</option>
            </select>
          </label>
          <label>Limit
            <input id="limit" type="number" min="1" max="500" value="25" />
          </label>
        </div>
        <label>Click target URL
          <input id="clickTargetUrl" placeholder="https://email-engine.app/" />
        </label>
        <div class="actions">
          <button id="processQueued">Process Queued</button>
          <button class="secondary" id="loadJobs">Load Jobs</button>
          <button class="secondary" id="loadRecords">Load Records</button>
          <button class="secondary" id="requeueRecord">Requeue Record</button>
          <button class="secondary" id="skipRecord">Skip Record</button>
          <button class="danger" id="deleteRecord">Delete Record</button>
          <button class="secondary" id="loadSuppressions">Suppressions</button>
          <button class="secondary" id="trackingLinks">Tracking Links</button>
          <button class="secondary" id="recordOpen">Record Open</button>
          <button class="secondary" id="recordClick">Record Click</button>
          <button class="secondary" id="aiDeliveryReview">AI Review</button>
          <button class="secondary" id="clear">Clear</button>
        </div>
        <div class="ai-delivery-panel" id="aiDeliveryPanel" hidden>
          <div class="ai-delivery-head">
            <strong>AI Delivery Review</strong>
            <span id="aiDeliveryMeta"></span>
          </div>
          <ul class="ai-delivery-summary" id="aiDeliverySummary"></ul>
          <div class="ai-delivery-list" id="aiDeliveryList"></div>
        </div>
      </div>
    </section>
    <section>
      <div class="head"><h2>Response</h2></div>
      <div class="body">
        <pre id="result"></pre>
      </div>
    </section>
  </main>
  <script>
    const result = document.getElementById("result");
    const campaigns = [];
    const jobs = [];
    const records = [];
    let lastDeliveryRun = null;
    const initialParams = new URLSearchParams(location.search);

    function writeResult(data, ok = true) {
      result.textContent = JSON.stringify({ ok, data }, null, 2);
    }

    async function readResponse(response) {
      const text = await response.text();
      try { return text ? JSON.parse(text) : null; } catch { return text; }
    }

    async function request(path, options = {}) {
      const response = await fetch(path, options);
      const data = await readResponse(response);
      writeResult(data, response.ok);
      if (!response.ok) throw new Error(data.detail || `${path} failed`);
      return data;
    }

    function value(id) {
      return document.getElementById(id).value.trim();
    }

    function option(label, value) {
      const node = document.createElement("option");
      node.value = value || "";
      node.textContent = label;
      return node;
    }

    function resetSelect(id, placeholder) {
      const select = document.getElementById(id);
      select.textContent = "";
      select.appendChild(option(placeholder, ""));
      return select;
    }

    function renderCampaigns(items) {
      campaigns.splice(0, campaigns.length, ...items);
      const select = resetSelect("campaignId", "All campaigns");
      items.forEach((item) => {
        select.appendChild(option(`${item.name} - ${item.status} - ${item.id}`, item.id));
      });
      if (initialParams.get("campaign_id")) {
        select.value = initialParams.get("campaign_id");
      }
    }

    function renderJobs(items) {
      jobs.splice(0, jobs.length, ...items);
      const select = resetSelect("sendJobId", "All send jobs");
      items.forEach((item) => {
        const campaign = item.campaign_id ? item.campaign_id : "no campaign";
        select.appendChild(option(`${item.status} - ${campaign} - ${item.id}`, item.id));
      });
      if (initialParams.get("send_job_id")) {
        select.value = initialParams.get("send_job_id");
      }
    }

    function renderRecords(items) {
      records.splice(0, records.length, ...items);
      const select = resetSelect("sendRecordId", "Select send record");
      items.forEach((item) => {
        select.appendChild(option(`${item.status} - ${item.to_email} - ${item.id}`, item.id));
      });
      if (initialParams.get("send_record_id")) {
        select.value = initialParams.get("send_record_id");
      }
    }

    function limitQuery() {
      return `limit=${encodeURIComponent(value("limit") || "25")}&offset=0`;
    }

    function scopedQuery() {
      const params = new URLSearchParams(limitQuery());
      if (value("campaignId")) params.set("campaign_id", value("campaignId"));
      if (value("sendJobId")) params.set("send_job_id", value("sendJobId"));
      return params.toString();
    }

    async function processQueued() {
      const params = new URLSearchParams();
      params.set("limit", value("limit") || "25");
      if (value("campaignId")) params.set("campaign_id", value("campaignId"));
      if (value("sendJobId")) params.set("send_job_id", value("sendJobId"));
      await request(`/api/v1/delivery/process-queued?${params.toString()}`, {
        method: "POST"
      }).then((data) => { lastDeliveryRun = data; return data; });
    }

    async function loadCampaigns() {
      const data = await request(`/api/v1/campaigns/list?${limitQuery()}`);
      renderCampaigns(data.items || []);
    }

    async function loadJobs() {
      const params = new URLSearchParams(limitQuery());
      if (value("campaignId")) params.set("campaign_id", value("campaignId"));
      const data = await request(`/api/v1/campaign-send-jobs/list?${params.toString()}`);
      renderJobs(data.items || []);
      return data;
    }

    async function loadRecords() {
      const data = await request(`/api/v1/email-send-records/list?${scopedQuery()}`);
      renderRecords(data.items || []);
      return data;
    }

    function renderDeliveryAiReview(data) {
      const panel = document.getElementById("aiDeliveryPanel");
      const meta = document.getElementById("aiDeliveryMeta");
      const summary = document.getElementById("aiDeliverySummary");
      const list = document.getElementById("aiDeliveryList");
      panel.hidden = false;
      meta.textContent = `${data.provider || "email-engine"} - ${data.model || "delivery-analysis"}`;
      summary.innerHTML = (data.summary || [])
        .map((item) => `<li>${String(item).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]))}</li>`)
        .join("");
      list.innerHTML = (data.recommendations || []).map((item) => `
        <div class="ai-delivery-card ${String(item.priority || "").replace(/[&<>"']/g, "")}">
          <strong>${String(item.title || item.code || "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]))}</strong>
          <p>${String(item.detail || "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]))}</p>
          <p>${String(item.suggested_action || "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]))}</p>
        </div>
      `).join("") || '<div>No recommendations returned.</div>';
    }

    async function reviewDeliveryWithAi() {
      const button = document.getElementById("aiDeliveryReview");
      button.disabled = true;
      button.textContent = "Reviewing...";
      try {
        const jobsData = await loadJobs();
        const recordsData = await loadRecords();
        const data = await request("/api/v1/ai/delivery/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            delivery_context: {
              filters: {
                campaign_id: value("campaignId") || null,
                send_job_id: value("sendJobId") || null,
                send_record_id: value("sendRecordId") || null,
              },
              jobs: jobsData,
              records: recordsData,
              last_run: lastDeliveryRun,
            },
            goals: [
              "Assess delivery queue health.",
              "Identify failed, stuck, suppressed, and retry-risk records.",
              "Recommend concrete next steps for delivery operations.",
            ],
          })
        });
        renderDeliveryAiReview(data);
      } finally {
        button.disabled = false;
        button.textContent = "AI Review";
      }
    }

    async function recordAction(action, method = "POST") {
      if (!value("sendRecordId")) {
        writeResult("Enter a send record ID first.", false);
        return;
      }
      await request(`/api/v1/email-send-records/${value("sendRecordId")}${action}`, { method });
    }

    async function loadSuppressions() {
      await request(`/api/v1/suppressions?${limitQuery()}`);
    }

    async function trackingLinks() {
      if (!value("sendRecordId")) {
        writeResult("Enter a send record ID first.", false);
        return;
      }
      await request(`/api/v1/email-send-records/${value("sendRecordId")}/tracking-links`);
    }

    async function recordOpen() {
      if (!value("sendRecordId")) {
        writeResult("Enter a send record ID first.", false);
        return;
      }
      await request(`/api/v1/tests/email-send-records/${value("sendRecordId")}/open`, {
        method: "POST"
      });
    }

    async function recordClick() {
      if (!value("sendRecordId")) {
        writeResult("Enter a send record ID first.", false);
        return;
      }
      const params = new URLSearchParams();
      if (value("clickTargetUrl")) params.set("target_url", value("clickTargetUrl"));
      const suffix = params.toString() ? `?${params.toString()}` : "";
      await request(`/api/v1/tests/email-send-records/${value("sendRecordId")}/click${suffix}`, {
        method: "POST"
      });
    }

    document.getElementById("processQueued").addEventListener("click", () => {
      processQueued().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("campaignId").addEventListener("change", () => {
      loadJobs()
        .then(loadRecords)
        .catch((error) => writeResult(error.message, false));
    });
    document.getElementById("sendJobId").addEventListener("change", () => {
      loadRecords().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("loadJobs").addEventListener("click", () => {
      loadJobs().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("loadRecords").addEventListener("click", () => {
      loadRecords().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("requeueRecord").addEventListener("click", () => {
      recordAction("/requeue").catch((error) => writeResult(error.message, false));
    });
    document.getElementById("skipRecord").addEventListener("click", () => {
      recordAction("/skip").catch((error) => writeResult(error.message, false));
    });
    document.getElementById("deleteRecord").addEventListener("click", () => {
      recordAction("", "DELETE").catch((error) => writeResult(error.message, false));
    });
    document.getElementById("loadSuppressions").addEventListener("click", () => {
      loadSuppressions().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("trackingLinks").addEventListener("click", () => {
      trackingLinks().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("recordOpen").addEventListener("click", () => {
      recordOpen().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("recordClick").addEventListener("click", () => {
      recordClick().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("aiDeliveryReview").addEventListener("click", () => {
      reviewDeliveryWithAi().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("clear").addEventListener("click", () => {
      result.textContent = "";
      document.getElementById("aiDeliveryPanel").hidden = true;
    });

    loadCampaigns()
      .then(loadJobs)
      .then(loadRecords)
      .then(() => {
        if (value("sendRecordId")) {
          return trackingLinks();
        }
        return null;
      })
      .catch((error) => writeResult(error.message, false));
  </script>
</body>
</html>"""


ADMIN_ANALYTICS_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Analytics</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: minmax(520px, .9fr) minmax(420px, 1.1fr);
      gap: 14px;
      padding: 14px;
    }
    section {
      min-width: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { min-width: 0; padding: 12px; display: grid; gap: 10px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, select {
      min-width: 0;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--blue); }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .inline {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 10px;
    }
    .report {
      display: grid;
      gap: 12px;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 8px;
    }
    .kpi {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfe;
      min-width: 0;
    }
    .kpi .label {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .02em;
    }
    .kpi .value {
      margin-top: 4px;
      font-size: 22px;
      font-weight: 750;
    }
    .insight-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 8px;
    }
    .insight {
      border: 1px solid #cfe7d7;
      border-radius: 8px;
      padding: 10px;
      background: #f6fbf8;
      min-width: 0;
    }
    .insight.warn {
      border-color: #f1d09a;
      background: #fffaf0;
    }
    .insight .label {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .02em;
    }
    .insight .value {
      margin-top: 4px;
      font-size: 18px;
      font-weight: 750;
    }
    .insight .sub {
      margin-top: 3px;
      overflow: hidden;
      color: var(--muted);
      font-size: 12px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .performance-summary {
      border: 1px solid #c7d7fe;
      border-radius: 8px;
      background: #f7f9ff;
      padding: 10px;
      display: grid;
      gap: 8px;
    }
    .performance-summary h3 { margin: 0; font-size: 13px; }
    .performance-summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 8px;
    }
    .performance-summary-card {
      border: 1px solid #dbe4ff;
      border-radius: 7px;
      background: #fff;
      padding: 9px;
      min-width: 0;
    }
    .performance-summary-card.warn {
      border-color: #f1d09a;
      background: #fffaf0;
    }
    .performance-summary-card strong,
    .performance-summary-card span {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .performance-summary-card strong { font-size: 13px; }
    .performance-summary-card span {
      margin-top: 3px;
      color: var(--muted);
      font-size: 12px;
    }
    .ai-analysis-panel {
      border: 1px solid #c7d7fe;
      border-radius: 8px;
      background: #f7f9ff;
      padding: 10px;
      display: grid;
      gap: 9px;
    }
    .ai-analysis-panel[hidden] { display: none; }
    .ai-analysis-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    .ai-analysis-head strong { font-size: 13px; }
    .ai-analysis-head span {
      color: var(--muted);
      font-size: 11px;
    }
    .ai-analysis-list {
      display: grid;
      gap: 7px;
    }
    .ai-analysis-card {
      border: 1px solid #dbe4ff;
      border-radius: 7px;
      background: #fff;
      padding: 9px;
      display: grid;
      gap: 4px;
    }
    .ai-analysis-card.high { border-color: #f3c8c5; background: #fff7f7; }
    .ai-analysis-card.medium { border-color: #f1d09a; background: #fffaf0; }
    .ai-analysis-card strong { font-size: 13px; }
    .ai-analysis-card p {
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    .focused-campaign-panel {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) minmax(260px, 2fr) auto;
      gap: 10px;
      align-items: center;
      border: 1px solid #b8e0c6;
      border-radius: 8px;
      background: #f4fbf6;
      padding: 10px;
    }
    .focused-campaign-panel.warn {
      grid-template-columns: minmax(180px, 1fr) auto;
      border-color: #f3d39a;
      background: #fffaf0;
    }
    .focused-campaign-main { min-width: 0; }
    .focused-campaign-main strong,
    .focused-campaign-main small {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .focused-campaign-main small { color: var(--muted); font-size: 11px; margin-top: 2px; }
    .focused-campaign-metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }
    .focused-metric {
      border: 1px solid #d6eadc;
      border-radius: 6px;
      background: #fff;
      padding: 8px;
      min-width: 0;
    }
    .focused-metric.warn { border-color: #f3c8c5; background: #fff7f7; }
    .focused-metric span {
      display: block;
      color: var(--muted);
      font-size: 10px;
      text-transform: uppercase;
    }
    .focused-metric strong { display: block; margin-top: 2px; }
    .focused-campaign-actions {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 6px;
    }
    .chart {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fff;
      display: grid;
      gap: 8px;
      min-width: 0;
    }
    .chart h3 { margin: 0; font-size: 13px; }
    .bar-row {
      display: grid;
      grid-template-columns: minmax(92px, 150px) minmax(0, 1fr) 64px;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
      min-width: 0;
    }
    .bar-track {
      min-width: 0;
      height: 10px;
      border-radius: 999px;
      background: #eef2f7;
      overflow: hidden;
    }
    .bar {
      height: 100%;
      min-width: 2px;
      border-radius: 999px;
      background: var(--blue);
    }
    .bar.green { background: #15803d; }
    .bar.amber { background: #b45309; }
    .bar.red { background: #b42318; }
    .rate-comparison {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fff;
      display: grid;
      gap: 8px;
      min-width: 0;
    }
    .rate-comparison h3 { margin: 0; font-size: 13px; }
    .rate-row {
      display: grid;
      grid-template-columns: minmax(160px, 1fr) repeat(3, minmax(120px, 1fr));
      gap: 10px;
      align-items: center;
      padding: 7px 0;
      border-top: 1px solid #eef2f7;
    }
    .rate-row:first-of-type { border-top: none; }
    .rate-name {
      display: grid;
      gap: 2px;
      min-width: 0;
    }
    .rate-name strong,
    .rate-name span {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .rate-name span {
      color: var(--muted);
      font-size: 11px;
    }
    .rate-track-row {
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr) 44px;
      gap: 6px;
      align-items: center;
      color: var(--muted);
      font-size: 11px;
    }
    .rate-track {
      height: 8px;
      border-radius: 999px;
      background: #eef2f7;
      overflow: hidden;
    }
    .rate-fill {
      height: 100%;
      min-width: 2px;
      border-radius: 999px;
      background: var(--blue);
    }
	    .rate-fill.open { background: #2563eb; }
	    .rate-fill.click { background: #15803d; }
	    .rate-fill.bounce { background: #b42318; }
	    .journey-dashboard {
	      display: grid;
	      gap: 12px;
	    }
	    .journey-status-grid {
	      display: grid;
	      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
	      gap: 10px;
	    }
	    .journey-status-card {
	      border: 1px solid var(--line);
	      border-radius: 8px;
	      background: #fff;
	      padding: 10px;
	      display: grid;
	      gap: 8px;
	      min-width: 0;
	    }
	    .journey-status-card strong,
	    .journey-status-card small {
	      display: block;
	      overflow: hidden;
	      text-overflow: ellipsis;
	      white-space: nowrap;
	    }
	    .journey-status-card small { color: var(--muted); }
	    .stacked-bar {
	      display: flex;
	      width: 100%;
	      height: 12px;
	      overflow: hidden;
	      border-radius: 999px;
	      background: #eef2f7;
	    }
	    .stacked-segment { min-width: 2px; height: 100%; }
	    .stacked-segment.active { background: #2563eb; }
	    .stacked-segment.completed { background: #15803d; }
	    .stacked-segment.failed { background: #b42318; }
	    .stacked-segment.exited { background: #b45309; }
	    .stacked-segment.paused { background: #64748b; }
	    .stacked-segment.skipped { background: #94a3b8; }
	    .journey-legend {
	      display: flex;
	      flex-wrap: wrap;
	      gap: 8px 12px;
	      color: var(--muted);
	      font-size: 11px;
	    }
	    .legend-dot {
	      display: inline-block;
	      width: 8px;
	      height: 8px;
	      margin-right: 4px;
	      border-radius: 999px;
	      vertical-align: middle;
	    }
	    .journey-step-grid {
	      display: grid;
	      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
	      gap: 8px;
	    }
	    .journey-step-card {
	      border: 1px solid var(--line);
	      border-radius: 8px;
	      background: #fbfcfe;
	      padding: 9px;
	      display: grid;
	      gap: 5px;
	      min-width: 0;
	    }
	    .journey-step-card.warn { border-color: #f3c8c5; background: #fff7f7; }
	    .journey-step-card strong,
	    .journey-step-card span {
	      display: block;
	      overflow-wrap: anywhere;
	    }
	    .journey-step-card span { color: var(--muted); font-size: 12px; }
	    .table-wrap {
	      overflow: auto;
	      border: 1px solid var(--line);
      border-radius: 8px;
    }
    table {
      width: 100%;
      min-width: 640px;
      border-collapse: collapse;
      font-size: 12px;
    }
    th, td {
      padding: 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: nowrap;
    }
    th { color: var(--muted); background: #f8fafc; font-weight: 650; }
    .empty-state {
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 12px;
      color: var(--muted);
      background: #fbfcfe;
    }
    pre {
      margin: 0;
      min-height: 260px;
      max-height: 420px;
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    @media (max-width: 1000px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      .inline { grid-template-columns: 1fr; }
      pre { min-height: 360px; max-height: 520px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Analytics</h1>
    <div class="actions">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/admin/journeys'">Journey Manager</button>
      <button class="secondary" onclick="location.href='/admin/delivery'">Delivery Manager</button>
      <button class="secondary" onclick="location.href='/admin/suppressions'">Suppressions</button>
      <button class="secondary" onclick="location.href='/admin/analytics'">Analytics</button>
      <button class="secondary" onclick="location.href='/admin/data-sources'">Data Sources</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <section>
      <div class="head"><h2>Inputs</h2></div>
      <div class="body">
        <label>Campaign
          <select id="campaignId">
            <option value="">All campaigns</option>
          </select>
        </label>
        <label>Send job
          <select id="sendJobId">
            <option value="">All send jobs</option>
          </select>
        </label>
        <label>Send record
          <select id="sendRecordId">
            <option value="">Select send record</option>
          </select>
        </label>
        <label>Journey
          <select id="journeyId">
            <option value="">All journeys</option>
          </select>
        </label>
        <label>Audience
          <select id="audienceId">
            <option value="">All audiences</option>
          </select>
        </label>
        <label>Provider
          <input id="provider" placeholder="sendgrid" />
        </label>
        <label>Event type
          <select id="eventType">
            <option value="">All event types</option>
            <option value="queued">queued</option>
            <option value="sent">sent</option>
            <option value="delivered">delivered</option>
            <option value="opened">opened</option>
            <option value="clicked">clicked</option>
            <option value="bounced">bounced</option>
            <option value="complained">complained</option>
            <option value="unsubscribed">unsubscribed</option>
          </select>
        </label>
        <div class="inline">
          <label>Limit
            <input id="limit" type="number" min="1" max="500" value="100" />
          </label>
          <label>Offset
            <input id="offset" type="number" min="0" value="0" />
          </label>
        </div>
        <label>Timeline days
          <input id="days" type="number" min="1" max="365" value="30" />
        </label>
        <div class="actions">
          <button id="campaignAnalytics">Campaign Analytics</button>
          <button class="secondary" id="campaignTimeline">Campaign Timeline</button>
          <button class="secondary" id="analyticsOverview">Analytics Overview</button>
          <button class="secondary" id="audiencePerformance">Audience Performance</button>
          <button class="secondary" id="campaignPerformance">Campaign Performance</button>
          <button class="secondary" id="domainDeliverability">Domain Deliverability</button>
          <button class="secondary" id="journeyPerformance">Journey Performance</button>
          <button class="secondary" id="eventTimeline">Event Timeline</button>
          <button class="secondary" id="events">Raw Events</button>
          <button class="secondary" id="jobs">Send Jobs</button>
          <button class="secondary" id="records">Send Records</button>
          <button class="secondary" id="trackingLinks">Tracking Links</button>
          <button class="secondary" id="aiAnalyze">AI Analysis</button>
          <button class="secondary" id="clear">Clear</button>
        </div>
      </div>
    </section>
    <section>
      <div class="head"><h2>Report</h2></div>
      <div class="body">
        <div id="focusedCampaign"></div>
        <div class="ai-analysis-panel" id="aiAnalysisPanel" hidden>
          <div class="ai-analysis-head">
            <strong>AI Analysis</strong>
            <span id="aiAnalysisMeta"></span>
          </div>
          <div id="aiAnalysisSummary"></div>
          <div class="ai-analysis-list" id="aiAnalysisList"></div>
        </div>
        <div id="report" class="report">
          <div class="empty-state">Run a report to view charts and tables.</div>
        </div>
        <pre id="result"></pre>
      </div>
    </section>
  </main>
  <script>
    const result = document.getElementById("result");
    const report = document.getElementById("report");
    const audiences = [];
    const campaigns = [];
    const journeys = [];
    const sendJobs = [];
    const sendRecords = [];
    const initialParams = new URLSearchParams(location.search);
    let lastReportData = null;
    let lastReportType = "analytics";

    function writeResult(data, ok = true) {
      result.textContent = JSON.stringify({ ok, data }, null, 2);
      if (ok) lastReportData = data;
      renderReport(data, ok);
    }

    async function readResponse(response) {
      const text = await response.text();
      try { return text ? JSON.parse(text) : null; } catch { return text; }
    }

    async function request(path) {
      const response = await fetch(path);
      const data = await readResponse(response);
      writeResult(data, response.ok);
      if (!response.ok) throw new Error(data.detail || `${path} failed`);
      return data;
    }

    async function postJson(path, body) {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await readResponse(response);
      result.textContent = JSON.stringify({ ok: response.ok, data }, null, 2);
      if (!response.ok) throw new Error(data.detail || `${path} failed`);
      return data;
    }

    async function fetchJson(path) {
      const response = await fetch(path);
      const data = await readResponse(response);
      if (!response.ok) throw new Error(data.detail || `${path} failed`);
      return data;
    }

    function value(id) {
      return document.getElementById(id).value.trim();
    }

    function option(label, value) {
      const item = document.createElement("option");
      item.textContent = label;
      item.value = value;
      return item;
    }

    function resetSelect(id, label) {
      const select = document.getElementById(id);
      select.innerHTML = "";
      select.appendChild(option(label, ""));
      return select;
    }

    function shortId(id) {
      return id ? id.slice(0, 8) : "-";
    }

    function pct(value) {
      return `${Math.round((Number(value || 0)) * 1000) / 10}%`;
    }

    function int(value) {
      return Number(value || 0).toLocaleString();
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function kpis(items) {
      return `<div class="kpi-grid">${items.map((item) => `
        <div class="kpi">
          <div class="label">${escapeHtml(item.label)}</div>
          <div class="value">${escapeHtml(item.value)}</div>
        </div>
      `).join("")}</div>`;
    }

    function insights(items) {
      return `<div class="insight-grid">${items.map((item) => `
        <div class="insight ${item.tone === "warn" ? "warn" : ""}">
          <div class="label">${escapeHtml(item.label)}</div>
          <div class="value">${escapeHtml(item.value)}</div>
          <div class="sub">${escapeHtml(item.sub || "")}</div>
        </div>
      `).join("")}</div>`;
    }

    function maxBy(items, fn) {
      return (items || []).reduce((best, item) => {
        if (!best) return item;
        return Number(fn(item) || 0) > Number(fn(best) || 0) ? item : best;
      }, null);
    }

    function campaignInsights(items) {
      const rows = items || [];
      const bestOpen = maxBy(rows, (row) => row.open_rate);
      const bestClick = maxBy(rows, (row) => row.click_rate);
      const failed = rows.reduce((sum, row) => sum + Number(row.failed_count || 0), 0);
      const bounced = rows.reduce((sum, row) => sum + Number(row.bounced_count || 0), 0);
      return insights([
        {
          label: "Best open campaign",
          value: bestOpen ? pct(bestOpen.open_rate) : "-",
          sub: bestOpen ? (bestOpen.name || shortId(bestOpen.campaign_id)) : "No campaign activity",
        },
        {
          label: "Best click campaign",
          value: bestClick ? pct(bestClick.click_rate) : "-",
          sub: bestClick ? (bestClick.name || shortId(bestClick.campaign_id)) : "No click activity",
        },
        {
          label: "Failed records",
          value: int(failed),
          sub: failed ? "Review delivery manager" : "No failures in this page",
          tone: failed ? "warn" : "",
        },
        {
          label: "Bounced records",
          value: int(bounced),
          sub: bounced ? "Review domain deliverability" : "No bounces in this page",
          tone: bounced ? "warn" : "",
        },
      ]);
    }

	    function domainInsights(items) {
	      const rows = items || [];
	      const highestBounce = maxBy(rows, (row) => row.bounce_rate);
	      const failed = rows.reduce((sum, row) => sum + Number(row.failed_count || 0), 0);
      return insights([
        {
          label: "Highest bounce domain",
          value: highestBounce ? pct(highestBounce.bounce_rate) : "-",
          sub: highestBounce ? highestBounce.domain : "No domain activity",
          tone: highestBounce && Number(highestBounce.bounce_rate || 0) > 0 ? "warn" : "",
        },
        {
          label: "Failed records",
          value: int(failed),
          sub: failed ? "Review provider errors" : "No failures in this page",
          tone: failed ? "warn" : "",
	        },
	      ]);
	    }

	    function journeyInsights(items) {
	      const rows = items || [];
	      const active = rows.reduce((sum, row) => sum + Number(row.active_count || 0), 0);
	      const completed = rows.reduce((sum, row) => sum + Number(row.completed_count || 0), 0);
	      const failed = rows.reduce((sum, row) =>
	        sum + Number(row.failed_count || 0) + Number(row.step_failed_count || 0), 0);
	      const queued = rows.reduce((sum, row) => sum + Number(row.queued_send_count || 0), 0);
	      return insights([
	        {
	          label: "Active enrollments",
	          value: int(active),
	          sub: active ? "Contacts still moving through journeys" : "No active enrollments in this page",
	        },
	        {
	          label: "Completed enrollments",
	          value: int(completed),
	          sub: "Completed journey exits",
	        },
	        {
	          label: "Journey failures",
	          value: int(failed),
	          sub: failed ? "Review step history and graph state" : "No failures in this page",
	          tone: failed ? "warn" : "",
	        },
	        {
	          label: "Queued journey sends",
	          value: int(queued),
	          sub: queued ? "Process delivery queue" : "No queued sends in this page",
	          tone: queued ? "warn" : "",
	        },
	      ]);
	    }

    function performanceSummary(kind, items) {
      const rows = items || [];
      if (!rows.length) return "";
      let cards = [];
      if (kind === "campaign") {
        const bestOpen = maxBy(rows, (row) => row.open_rate);
        const bestClick = maxBy(rows, (row) => row.click_rate);
        const highestBounce = maxBy(rows, (row) => row.bounce_rate);
        const totalFailed = rows.reduce((sum, row) => sum + Number(row.failed_count || 0), 0);
        cards = [
          {
            label: "Best open rate",
            value: bestOpen ? `${pct(bestOpen.open_rate)} ${bestOpen.name || shortId(bestOpen.campaign_id)}` : "-",
            detail: "Use this as a subject/content benchmark.",
          },
          {
            label: "Best click rate",
            value: bestClick ? `${pct(bestClick.click_rate)} ${bestClick.name || shortId(bestClick.campaign_id)}` : "-",
            detail: "Review CTA and offer structure.",
          },
          {
            label: "Delivery risk",
            value: totalFailed ? `${int(totalFailed)} failed records` : "No failures in this page",
            detail: highestBounce ? `Highest bounce: ${pct(highestBounce.bounce_rate)}` : "No bounce signal.",
            warn: totalFailed > 0 || Number(highestBounce?.bounce_rate || 0) > 0,
          },
          {
            label: "Recommended next action",
            value: totalFailed ? "Open Delivery Manager" : "Compare top templates",
            detail: totalFailed ? "Triage failed records before scaling." : "Apply winning copy patterns.",
          },
        ];
      } else if (kind === "domain") {
        const highestBounce = maxBy(rows, (row) => row.bounce_rate);
        const highestFailure = maxBy(rows, (row) => row.failed_count);
        cards = [
          {
            label: "Highest bounce domain",
            value: highestBounce ? `${highestBounce.domain} ${pct(highestBounce.bounce_rate)}` : "-",
            detail: "Watch domain-specific deliverability.",
            warn: Number(highestBounce?.bounce_rate || 0) > 0,
          },
          {
            label: "Highest failure domain",
            value: highestFailure ? `${highestFailure.domain} ${int(highestFailure.failed_count)} failed` : "-",
            detail: "Review provider responses and suppression rules.",
            warn: Number(highestFailure?.failed_count || 0) > 0,
          },
          {
            label: "Recommended next action",
            value: Number(highestBounce?.bounce_rate || 0) > 0 ? "Review suppressions" : "Keep monitoring",
            detail: "Use domain view before increasing volume.",
          },
        ];
	      } else if (kind === "audience") {
	        const bestOpen = maxBy(rows, (row) => row.open_rate);
	        const bestClick = maxBy(rows, (row) => row.click_rate);
        cards = [
          {
            label: "Most engaged audience",
            value: bestOpen ? `${bestOpen.name || shortId(bestOpen.audience_id)} ${pct(bestOpen.open_rate)}` : "-",
            detail: "Use this segment as a targeting benchmark.",
          },
          {
            label: "Best click audience",
            value: bestClick ? `${bestClick.name || shortId(bestClick.audience_id)} ${pct(bestClick.click_rate)}` : "-",
            detail: "Consider similar constraints for future campaigns.",
          },
          {
            label: "Recommended next action",
            value: "Refine audience builder",
            detail: "Preview contacts and test constraints before launch.",
	          },
	        ];
	      } else if (kind === "journey") {
	        const mostActive = maxBy(rows, (row) => row.active_count);
	        const mostFailed = maxBy(rows, (row) => row.step_failed_count + row.failed_count);
	        const queued = rows.reduce((sum, row) => sum + Number(row.queued_send_count || 0), 0);
	        cards = [
	          {
	            label: "Most active journey",
	            value: mostActive ? `${mostActive.name || shortId(mostActive.journey_id)} ${int(mostActive.active_count)} active` : "-",
	            detail: "Watch active enrollment volume and due work.",
	          },
	          {
	            label: "Highest failure risk",
	            value: mostFailed ? `${mostFailed.name || shortId(mostFailed.journey_id)} ${int(Number(mostFailed.step_failed_count || 0) + Number(mostFailed.failed_count || 0))} failures` : "-",
	            detail: "Review failed enrollments and step executions.",
	            warn: mostFailed && (Number(mostFailed.step_failed_count || 0) + Number(mostFailed.failed_count || 0)) > 0,
	          },
	          {
	            label: "Queued sends",
	            value: queued ? `${int(queued)} queued` : "No queued journey sends",
	            detail: queued ? "Open Delivery Manager or process queued sends." : "No delivery backlog visible.",
	            warn: queued > 0,
	          },
	          {
	            label: "Recommended next action",
	            value: queued || Number(mostFailed?.step_failed_count || 0) ? "Review journey execution" : "Enroll a test contact",
	            detail: "Use Journey Manager graph plus AI Review for path-level diagnosis.",
	          },
	        ];
	      }
      if (!cards.length) return "";
      return `<div class="performance-summary">
        <h3>Performance Summary</h3>
        <div class="performance-summary-grid">
          ${cards.map((card) => `
            <div class="performance-summary-card ${card.warn ? "warn" : ""}">
              <strong>${escapeHtml(card.label)}</strong>
              <span>${escapeHtml(card.value)}</span>
              <span>${escapeHtml(card.detail)}</span>
            </div>
          `).join("")}
        </div>
      </div>`;
    }

    function renderAiAnalysis(data) {
      const panel = document.getElementById("aiAnalysisPanel");
      const meta = document.getElementById("aiAnalysisMeta");
      const summary = document.getElementById("aiAnalysisSummary");
      const list = document.getElementById("aiAnalysisList");
      panel.hidden = false;
      meta.textContent = `${data.provider || "email-engine"} - ${data.model || "analytics-analysis"}`;
      summary.innerHTML = insights((data.summary || []).map((item, index) => ({
        label: index === 0 ? "Summary" : "Context",
        value: item,
        sub: "",
      })));
      list.textContent = "";
      (data.recommendations || []).forEach((item) => {
        const card = document.createElement("div");
        card.className = `ai-analysis-card ${item.priority || ""}`;
        card.innerHTML = `
          <strong>${escapeHtml(item.title || item.code)}</strong>
          <p>${escapeHtml(item.detail || "")}</p>
          <p>${escapeHtml(item.suggested_action || "")}</p>
        `;
        list.appendChild(card);
      });
      if (!list.children.length) {
        list.innerHTML = '<div class="empty-state">No recommendations returned.</div>';
      }
    }

    function metricBars(title, rows, color = "") {
      const filtered = rows.filter((row) => Number(row.count || 0) > 0);
      if (!filtered.length) return "";
      const max = Math.max(...filtered.map((row) => Number(row.count || 0)), 1);
      return `<div class="chart">
        <h3>${escapeHtml(title)}</h3>
        ${filtered.map((row) => `
          <div class="bar-row">
            <div>${escapeHtml(row.name)}</div>
            <div class="bar-track"><div class="bar ${color}" style="width:${Math.max(2, (Number(row.count || 0) / max) * 100)}%"></div></div>
            <div>${int(row.count)}</div>
          </div>
        `).join("")}
      </div>`;
    }

    function rateTrack(label, value, tone) {
      const percent = Math.max(0, Math.min(100, Number(value || 0) * 100));
      return `<div class="rate-track-row">
        <span>${escapeHtml(label)}</span>
        <div class="rate-track">
          <div class="rate-fill ${escapeHtml(tone)}" style="width:${Math.max(2, percent)}%"></div>
        </div>
        <strong>${pct(value)}</strong>
      </div>`;
    }

	    function campaignRateComparison(items) {
	      const rows = (items || [])
	        .filter((row) =>
          Number(row.sent_count || 0) > 0 ||
          Number(row.opened_count || 0) > 0 ||
          Number(row.clicked_count || 0) > 0 ||
          Number(row.bounced_count || 0) > 0
        )
        .slice(0, 8);
      if (!rows.length) return "";
      return `<div class="rate-comparison">
        <h3>Campaign Rate Comparison</h3>
        ${rows.map((row) => `
          <div class="rate-row">
            <div class="rate-name">
              <strong>${escapeHtml(row.name || shortId(row.campaign_id))}</strong>
              <span>${escapeHtml(row.status || "")} - ${int(row.sent_count)} sent</span>
            </div>
            ${rateTrack("Open", row.open_rate, "open")}
            ${rateTrack("Click", row.click_rate, "click")}
            ${rateTrack("Bounce", row.bounce_rate, "bounce")}
          </div>
	        `).join("")}
	      </div>`;
	    }

	    function journeyStackedBar(parts) {
	      const total = parts.reduce((sum, item) => sum + Number(item.count || 0), 0);
	      if (!total) return '<div class="stacked-bar"></div>';
	      return `<div class="stacked-bar">${parts
	        .filter((item) => Number(item.count || 0) > 0)
	        .map((item) => `<span class="stacked-segment ${escapeHtml(item.className)}" style="width:${Math.max(2, (Number(item.count || 0) / total) * 100)}%" title="${escapeHtml(item.label)}: ${int(item.count)}"></span>`)
	        .join("")}</div>`;
	    }

	    function journeyLegend(parts) {
	      return `<div class="journey-legend">${parts.map((item) => `
	        <span><i class="legend-dot stacked-segment ${escapeHtml(item.className)}"></i>${escapeHtml(item.label)} ${int(item.count)}</span>
	      `).join("")}</div>`;
	    }

	    function journeyStatusCharts(items) {
	      const rows = (items || []).slice(0, 8);
	      if (!rows.length) return "";
	      return `<div class="chart">
	        <h3>Journey State Comparison</h3>
	        <div class="journey-status-grid">
	          ${rows.map((row) => {
	            const enrollmentParts = [
	              { label: "Active", count: row.active_count, className: "active" },
	              { label: "Completed", count: row.completed_count, className: "completed" },
	              { label: "Exited", count: row.exited_count, className: "exited" },
	              { label: "Paused", count: row.paused_count, className: "paused" },
	              { label: "Failed", count: row.failed_count, className: "failed" },
	            ];
	            const executionParts = [
	              { label: "Step completed", count: row.step_completed_count, className: "completed" },
	              { label: "Step failed", count: row.step_failed_count, className: "failed" },
	              { label: "Step skipped", count: row.step_skipped_count, className: "skipped" },
	              { label: "Queued sends", count: row.queued_send_count, className: "active" },
	            ];
	            return `<div class="journey-status-card">
	              <strong>${escapeHtml(row.name || shortId(row.journey_id))}</strong>
	              <small>${escapeHtml(row.status || "")} - ${int(row.enrollment_count)} enrollments - ${int(row.execution_count)} executions</small>
	              ${journeyStackedBar(enrollmentParts)}
	              ${journeyLegend(enrollmentParts)}
	              ${journeyStackedBar(executionParts)}
	              ${journeyLegend(executionParts)}
	            </div>`;
	          }).join("")}
	        </div>
	      </div>`;
	    }

	    function journeyStepBreakdown(items) {
	      const steps = (items || [])
	        .flatMap((journey) => (journey.steps || []).map((step) => ({ ...step, journey_name: journey.name, journey_id: journey.journey_id })))
	        .filter((step) =>
	          Number(step.execution_count || 0) > 0 ||
	          Number(step.failed_count || 0) > 0 ||
	          Number(step.queued_send_count || 0) > 0
	        )
	        .slice(0, 12);
	      if (!steps.length) {
	        return `<div class="chart"><h3>Journey Step Breakdown</h3><div class="empty-state">No step execution activity yet.</div></div>`;
	      }
	      return `<div class="chart">
	        <h3>Journey Step Breakdown</h3>
	        <div class="journey-step-grid">
	          ${steps.map((step) => `
	            <div class="journey-step-card ${Number(step.failed_count || 0) ? "warn" : ""}">
	              <strong>${escapeHtml(step.name || shortId(step.step_id))}</strong>
	              <span>${escapeHtml(step.journey_name || shortId(step.journey_id))} - ${escapeHtml(step.step_type || "")}</span>
	              <span>${int(step.execution_count)} executions - ${int(step.completed_count)} done - ${int(step.failed_count)} failed - ${int(step.queued_send_count)} queued sends</span>
	            </div>
	          `).join("")}
	        </div>
	      </div>`;
	    }

	    function journeyDashboard(items) {
	      const rows = items || [];
	      const totals = rows.reduce((acc, row) => {
	        acc.enrollments += Number(row.enrollment_count || 0);
	        acc.active += Number(row.active_count || 0);
	        acc.completed += Number(row.completed_count || 0);
	        acc.failed += Number(row.failed_count || 0) + Number(row.step_failed_count || 0);
	        acc.queued += Number(row.queued_send_count || 0);
	        acc.executions += Number(row.execution_count || 0);
	        return acc;
	      }, { enrollments: 0, active: 0, completed: 0, failed: 0, queued: 0, executions: 0 });
	      return `<div class="journey-dashboard">
	        ${performanceSummary("journey", rows)}
	        ${kpis([
	          { label: "Journeys", value: int(rows.length) },
	          { label: "Enrollments", value: int(totals.enrollments) },
	          { label: "Active", value: int(totals.active) },
	          { label: "Completed", value: int(totals.completed) },
	          { label: "Failures", value: int(totals.failed) },
	          { label: "Queued sends", value: int(totals.queued) },
	          { label: "Step executions", value: int(totals.executions) },
	        ])}
	        ${journeyInsights(rows)}
	        ${journeyStatusCharts(rows)}
	        ${journeyStepBreakdown(rows)}
	      </div>`;
	    }

	    function renderFocusedCampaign(data = null) {
      const container = document.getElementById("focusedCampaign");
      const campaignId = value("campaignId") || data?.campaign_id || "";
      if (!campaignId) {
        container.innerHTML = "";
        return;
      }
      const campaign = campaigns.find((item) => item.id === campaignId);
      if (!data || !data.status_counts) {
        container.innerHTML = `
          <div class="focused-campaign-panel warn">
            <div class="focused-campaign-main">
              <strong>${escapeHtml(campaign?.name || shortId(campaignId))}</strong>
              <small>${escapeHtml(campaign?.status || "Select Campaign Analytics for metrics")}</small>
            </div>
            <div class="focused-campaign-actions">
              <button class="secondary" type="button" onclick="campaignAnalytics().catch((error) => writeResult(error.message, false))">Load Metrics</button>
            </div>
          </div>
        `;
        return;
      }
      container.innerHTML = `
        <div class="focused-campaign-panel">
          <div class="focused-campaign-main">
            <strong>${escapeHtml(campaign?.name || shortId(campaignId))}</strong>
            <small>${escapeHtml(campaign?.status || "")} - ${escapeHtml(campaignId)}</small>
          </div>
          <div class="focused-campaign-metrics">
            <div class="focused-metric"><span>Sent</span><strong>${int(data.sent_count)}</strong></div>
            <div class="focused-metric"><span>Open rate</span><strong>${pct(data.open_rate)}</strong></div>
            <div class="focused-metric"><span>Click rate</span><strong>${pct(data.click_rate)}</strong></div>
            <div class="focused-metric ${Number(data.bounce_rate || 0) ? "warn" : ""}"><span>Bounce rate</span><strong>${pct(data.bounce_rate)}</strong></div>
          </div>
          <div class="focused-campaign-actions">
            <button class="secondary" type="button" onclick="campaignTimeline().catch((error) => writeResult(error.message, false))">Timeline</button>
            <button class="secondary" type="button" onclick="location.href='/admin/delivery?campaign_id=${encodeURIComponent(campaignId)}'">Delivery</button>
          </div>
        </div>
      `;
    }

    function table(title, rows, columns) {
      if (!rows || !rows.length) {
        return `<div class="chart"><h3>${escapeHtml(title)}</h3><div class="empty-state">No rows returned.</div></div>`;
      }
      return `<div class="chart">
        <h3>${escapeHtml(title)}</h3>
        <div class="table-wrap">
          <table>
            <thead><tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}</tr></thead>
            <tbody>
              ${rows.map((row) => `<tr>${columns.map((column) => {
                const raw = typeof column.value === "function" ? column.value(row) : row[column.key];
                return `<td>${escapeHtml(raw)}</td>`;
              }).join("")}</tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>`;
    }

    function timelineChart(data) {
      const points = (data.points || []).filter((point) =>
        ["requested_count", "sent_count", "opened_count", "clicked_count", "failed_count"].some(
          (key) => Number(point[key] || 0) > 0
        )
      );
      if (!points.length) {
        return `<div class="chart"><h3>Campaign Timeline</h3><div class="empty-state">No activity in the selected window.</div></div>`;
      }
      const max = Math.max(...points.map((point) =>
        Math.max(
          Number(point.requested_count || 0),
          Number(point.sent_count || 0),
          Number(point.opened_count || 0),
          Number(point.clicked_count || 0),
          Number(point.failed_count || 0)
        )
      ), 1);
      return `<div class="chart">
        <h3>Campaign Timeline</h3>
        ${points.map((point) => `
          <div class="bar-row">
            <div>${escapeHtml(point.date)}</div>
            <div class="bar-track" title="sent ${int(point.sent_count)}, opened ${int(point.opened_count)}, clicked ${int(point.clicked_count)}, failed ${int(point.failed_count)}">
              <div class="bar green" style="width:${Math.max(2, (Number(point.sent_count || 0) / max) * 100)}%"></div>
            </div>
            <div>${int(point.sent_count)} sent</div>
          </div>
          <div class="bar-row">
            <div></div>
            <div class="bar-track"><div class="bar" style="width:${Math.max(2, (Number(point.opened_count || 0) / max) * 100)}%"></div></div>
            <div>${int(point.opened_count)} open</div>
          </div>
          <div class="bar-row">
            <div></div>
            <div class="bar-track"><div class="bar amber" style="width:${Math.max(2, (Number(point.clicked_count || 0) / max) * 100)}%"></div></div>
            <div>${int(point.clicked_count)} click</div>
          </div>
        `).join("")}
      </div>`;
    }

    function renderReport(data, ok = true) {
      if (!ok) {
        report.innerHTML = `<div class="empty-state">${escapeHtml(data)}</div>`;
        return;
      }
      if (!data) {
        renderFocusedCampaign(null);
        report.innerHTML = `<div class="empty-state">No report data.</div>`;
        return;
      }
      if (data.points) {
        report.innerHTML = timelineChart(data);
        return;
      }
      if (data.campaign_count !== undefined && data.recent_events) {
        report.innerHTML = [
          kpis([
            { label: "Campaigns", value: int(data.campaign_count) },
            { label: "Contacts", value: int(data.contact_count) },
            { label: "Send jobs", value: int(data.send_job_count) },
            { label: "Send records", value: int(data.send_record_count) },
            { label: "Events", value: int(data.event_count) },
          ]),
          metricBars("Send Status", data.status_counts || [], "green"),
          metricBars("Events", data.event_counts || []),
          table("Recent Events", data.recent_events || [], [
            { label: "Type", value: (row) => row.event_type },
            { label: "Occurred", value: (row) => row.occurred_at },
            { label: "Campaign", value: (row) => shortId(row.campaign_id) },
            { label: "Send job", value: (row) => shortId(row.send_job_id) },
            { label: "Record", value: (row) => shortId(row.send_record_id) },
          ]),
        ].join("");
        return;
      }
      if (data.campaign_id && data.status_counts && data.event_counts) {
        renderFocusedCampaign(data);
        report.innerHTML = [
          performanceSummary("campaign", [data]),
          kpis([
            { label: "Requested", value: int(data.requested_count) },
            { label: "Sent", value: int(data.sent_count) },
            { label: "Opened", value: int(data.opened_count) },
            { label: "Clicked", value: int(data.clicked_count) },
            { label: "Open rate", value: pct(data.open_rate) },
            { label: "Click rate", value: pct(data.click_rate) },
            { label: "Bounce rate", value: pct(data.bounce_rate) },
          ]),
          metricBars("Send Status", data.status_counts || [], "green"),
          metricBars("Events", data.event_counts || []),
        ].join("");
        return;
      }
      if (data.items) {
        renderFocusedCampaign(null);
        renderListReport(data.items);
        return;
      }
      renderFocusedCampaign(null);
      report.innerHTML = `<div class="empty-state">Raw response only for this request.</div>`;
    }

    function renderListReport(items) {
      const first = items[0] || {};
      if ("campaign_id" in first && "open_rate" in first) {
        report.innerHTML = performanceSummary("campaign", items) + campaignInsights(items) + campaignRateComparison(items) + table("Campaign Performance", items, [
          { label: "Campaign", value: (row) => row.name || shortId(row.campaign_id) },
          { label: "Status", value: (row) => row.status },
          { label: "Requested", value: (row) => int(row.requested_count) },
          { label: "Sent", value: (row) => int(row.sent_count) },
          { label: "Failed", value: (row) => int(row.failed_count) },
          { label: "Opened", value: (row) => int(row.opened_count) },
          { label: "Clicked", value: (row) => int(row.clicked_count) },
          { label: "Open rate", value: (row) => pct(row.open_rate) },
          { label: "Click rate", value: (row) => pct(row.click_rate) },
          { label: "Bounce rate", value: (row) => pct(row.bounce_rate) },
        ]);
        return;
      }
      if ("audience_id" in first && "estimated_count" in first) {
        report.innerHTML = performanceSummary("audience", items) + table("Audience Performance", items, [
          { label: "Audience", value: (row) => row.name || shortId(row.audience_id) },
          { label: "Estimated", value: (row) => int(row.estimated_count) },
          { label: "Jobs", value: (row) => int(row.send_job_count) },
          { label: "Sent", value: (row) => int(row.sent_count) },
          { label: "Open rate", value: (row) => pct(row.open_rate) },
          { label: "Click rate", value: (row) => pct(row.click_rate) },
        ]);
        return;
      }
      if ("domain" in first && "send_record_count" in first) {
        report.innerHTML = performanceSummary("domain", items) + domainInsights(items) + table("Domain Deliverability", items, [
          { label: "Domain", value: (row) => row.domain },
          { label: "Provider", value: (row) => row.provider || "-" },
          { label: "Records", value: (row) => int(row.send_record_count) },
          { label: "Sent", value: (row) => int(row.sent_count) },
          { label: "Failed", value: (row) => int(row.failed_count) },
          { label: "Opened", value: (row) => int(row.opened_count) },
          { label: "Clicked", value: (row) => int(row.clicked_count) },
          { label: "Bounce rate", value: (row) => pct(row.bounce_rate) },
        ]);
        return;
	      }
	      if ("journey_id" in first && "enrollment_count" in first) {
	        report.innerHTML = journeyDashboard(items) + table("Journey Performance", items, [
	          { label: "Journey", value: (row) => row.name || shortId(row.journey_id) },
	          { label: "Status", value: (row) => row.status },
	          { label: "Enrollments", value: (row) => int(row.enrollment_count) },
	          { label: "Active", value: (row) => int(row.active_count) },
	          { label: "Completed", value: (row) => int(row.completed_count) },
	          { label: "Exited", value: (row) => int(row.exited_count) },
	          { label: "Paused", value: (row) => int(row.paused_count) },
	          { label: "Failed", value: (row) => int(row.failed_count) },
	          { label: "Executions", value: (row) => int(row.execution_count) },
	          { label: "Step done", value: (row) => int(row.step_completed_count) },
	          { label: "Step failures", value: (row) => int(row.step_failed_count) },
	          { label: "Queued sends", value: (row) => int(row.queued_send_count) },
	        ]);
	        return;
	      }
      if ("event_type" in first) {
        report.innerHTML = table("Events", items, [
          { label: "Type", value: (row) => row.event_type },
          { label: "Occurred", value: (row) => row.occurred_at },
          { label: "Campaign", value: (row) => shortId(row.campaign_id) },
          { label: "Send job", value: (row) => shortId(row.send_job_id) },
          { label: "Record", value: (row) => shortId(row.send_record_id) },
        ]);
        return;
      }
      report.innerHTML = `<div class="empty-state">Raw response only for this request.</div>`;
    }

    function pageQuery() {
      const params = new URLSearchParams();
      params.set("limit", value("limit") || "100");
      params.set("offset", value("offset") || "0");
      return params;
    }

    function eventQuery() {
      const params = pageQuery();
      if (value("campaignId")) params.set("campaign_id", value("campaignId"));
      if (value("sendJobId")) params.set("send_job_id", value("sendJobId"));
      if (value("sendRecordId")) params.set("send_record_id", value("sendRecordId"));
      if (value("eventType")) params.set("event_type", value("eventType"));
      return params;
    }

    function applyInitialFilters() {
      if (initialParams.get("event_type")) {
        document.getElementById("eventType").value = initialParams.get("event_type");
      }
    }

    async function loadCampaignOptions() {
      const data = await fetchJson(`/api/v1/campaigns/list?${pageQuery().toString()}`);
      campaigns.splice(0, campaigns.length, ...data.items);
      const select = resetSelect("campaignId", "All campaigns");
      for (const item of campaigns) {
        select.appendChild(option(`${item.name} - ${item.status} - ${shortId(item.id)}`, item.id));
      }
      if (initialParams.get("campaign_id")) {
        select.value = initialParams.get("campaign_id");
      }
    }

    async function loadAudienceOptions() {
      const data = await fetchJson(`/api/v1/audiences/list?${pageQuery().toString()}`);
      audiences.splice(0, audiences.length, ...data.items);
      const select = resetSelect("audienceId", "All audiences");
      for (const item of audiences) {
        select.appendChild(option(`${item.name} - ${item.status} - ${shortId(item.id)}`, item.id));
      }
    }

    async function loadJourneyOptions() {
      const data = await fetchJson(`/api/v1/journeys/list?${pageQuery().toString()}`);
      journeys.splice(0, journeys.length, ...data.items);
      const select = resetSelect("journeyId", "All journeys");
      for (const item of journeys) {
        select.appendChild(option(`${item.name} - ${item.status} - ${shortId(item.id)}`, item.id));
      }
    }

    async function loadJobOptions() {
      const params = pageQuery();
      if (value("campaignId")) params.set("campaign_id", value("campaignId"));
      const data = await fetchJson(`/api/v1/campaign-send-jobs/list?${params.toString()}`);
      sendJobs.splice(0, sendJobs.length, ...data.items);
      const select = resetSelect("sendJobId", "All send jobs");
      for (const item of sendJobs) {
        const campaign = item.campaign_id ? shortId(item.campaign_id) : "no campaign";
        select.appendChild(option(`${item.status} - ${campaign} - ${shortId(item.id)}`, item.id));
      }
      if (initialParams.get("send_job_id")) {
        select.value = initialParams.get("send_job_id");
      }
    }

    async function loadRecordOptions() {
      const params = pageQuery();
      if (value("campaignId")) params.set("campaign_id", value("campaignId"));
      if (value("sendJobId")) params.set("send_job_id", value("sendJobId"));
      const data = await fetchJson(`/api/v1/email-send-records/list?${params.toString()}`);
      sendRecords.splice(0, sendRecords.length, ...data.items);
      const select = resetSelect("sendRecordId", "Select send record");
      for (const item of sendRecords) {
        select.appendChild(
          option(`${item.status} - ${item.to_email} - ${shortId(item.id)}`, item.id)
        );
      }
      if (initialParams.get("send_record_id")) {
        select.value = initialParams.get("send_record_id");
      }
    }

    async function campaignAnalytics() {
      if (!value("campaignId")) {
        writeResult("Enter a campaign ID first.", false);
        return;
      }
      lastReportType = "campaign_analytics";
      const params = new URLSearchParams();
      if (value("sendJobId")) params.set("send_job_id", value("sendJobId"));
      const suffix = params.toString() ? `?${params.toString()}` : "";
      await request(`/api/v1/campaigns/${value("campaignId")}/analytics${suffix}`);
    }

    async function campaignTimeline() {
      if (!value("campaignId")) {
        writeResult("Enter a campaign ID first.", false);
        return;
      }
      lastReportType = "campaign_timeline";
      const params = new URLSearchParams();
      params.set("days", value("days") || "30");
      if (value("sendJobId")) params.set("send_job_id", value("sendJobId"));
      await request(`/api/v1/campaigns/${value("campaignId")}/analytics/timeline?${params.toString()}`);
    }

    async function analyticsOverview() {
      lastReportType = "analytics_overview";
      const params = new URLSearchParams();
      params.set("recent_event_limit", value("limit") || "25");
      await request(`/api/v1/analytics/overview?${params.toString()}`);
    }

    async function campaignPerformance() {
      lastReportType = "campaign_performance";
      await request(`/api/v1/analytics/campaigns?${pageQuery().toString()}`);
    }

    async function audiencePerformance() {
      lastReportType = "audience_performance";
      const params = pageQuery();
      if (value("audienceId")) params.set("audience_id", value("audienceId"));
      await request(`/api/v1/analytics/audiences?${params.toString()}`);
    }

    async function domainDeliverability() {
      lastReportType = "domain_deliverability";
      const params = pageQuery();
      if (value("campaignId")) params.set("campaign_id", value("campaignId"));
      if (value("sendJobId")) params.set("send_job_id", value("sendJobId"));
      if (value("provider")) params.set("provider", value("provider"));
      await request(`/api/v1/analytics/domains?${params.toString()}`);
    }

    async function journeyPerformance() {
      lastReportType = "journey_performance";
      const params = pageQuery();
      if (value("journeyId")) params.set("journey_id", value("journeyId"));
      await request(`/api/v1/analytics/journeys?${params.toString()}`);
    }

    async function eventTimeline() {
      lastReportType = "event_timeline";
      await request(`/api/v1/events/timeline?${eventQuery().toString()}`);
    }

    async function loadEvents() {
      lastReportType = "events";
      await request(`/api/v1/events/list?${eventQuery().toString()}`);
    }

    async function loadJobs() {
      lastReportType = "send_jobs";
      const params = pageQuery();
      if (value("campaignId")) params.set("campaign_id", value("campaignId"));
      await request(`/api/v1/campaign-send-jobs/list?${params.toString()}`);
    }

    async function loadRecords() {
      lastReportType = "send_records";
      const params = pageQuery();
      if (value("campaignId")) params.set("campaign_id", value("campaignId"));
      if (value("sendJobId")) params.set("send_job_id", value("sendJobId"));
      await request(`/api/v1/email-send-records/list?${params.toString()}`);
    }

    async function trackingLinks() {
      if (!value("sendRecordId")) {
        writeResult("Enter a send record ID first.", false);
        return;
      }
      await request(`/api/v1/email-send-records/${value("sendRecordId")}/tracking-links`);
    }

    async function aiAnalyzeReport() {
      if (!lastReportData) {
        writeResult("Run a report before requesting AI Analysis.", false);
        return;
      }
      const button = document.getElementById("aiAnalyze");
      button.disabled = true;
      button.textContent = "Analyzing...";
      try {
        const data = await postJson("/api/v1/ai/analytics/analyze", {
          report_type: lastReportType,
          report_context: lastReportData,
          goals: [
            "Identify performance risks",
            "Recommend next action",
            "Improve campaign workflow decisions",
          ],
        });
        renderAiAnalysis(data);
      } finally {
        button.disabled = false;
        button.textContent = "AI Analysis";
      }
    }

    document.getElementById("campaignAnalytics").addEventListener("click", () => {
      campaignAnalytics().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("campaignTimeline").addEventListener("click", () => {
      campaignTimeline().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("analyticsOverview").addEventListener("click", () => {
      analyticsOverview().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("audiencePerformance").addEventListener("click", () => {
      audiencePerformance().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("campaignPerformance").addEventListener("click", () => {
      campaignPerformance().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("domainDeliverability").addEventListener("click", () => {
      domainDeliverability().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("journeyPerformance").addEventListener("click", () => {
      journeyPerformance().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("eventTimeline").addEventListener("click", () => {
      eventTimeline().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("events").addEventListener("click", () => {
      loadEvents().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("jobs").addEventListener("click", () => {
      loadJobs().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("records").addEventListener("click", () => {
      loadRecords().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("trackingLinks").addEventListener("click", () => {
      trackingLinks().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("aiAnalyze").addEventListener("click", () => {
      aiAnalyzeReport().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("clear").addEventListener("click", () => {
      result.textContent = "";
      lastReportData = null;
      document.getElementById("aiAnalysisPanel").hidden = true;
    });
    document.getElementById("campaignId").addEventListener("change", () => {
      renderFocusedCampaign(null);
      loadJobOptions()
        .then(loadRecordOptions)
        .catch((error) => writeResult(error.message, false));
    });
    document.getElementById("sendJobId").addEventListener("change", () => {
      loadRecordOptions().catch((error) => writeResult(error.message, false));
    });

    loadCampaignOptions()
      .then(loadAudienceOptions)
      .then(loadJourneyOptions)
      .then(loadJobOptions)
      .then(loadRecordOptions)
      .then(applyInitialFilters)
      .then(() => {
        if (initialParams.get("view") === "events") return loadEvents();
        if (initialParams.get("view") === "timeline") return eventTimeline();
        return value("campaignId") ? campaignAnalytics() : analyticsOverview();
      })
      .catch((error) => writeResult(error.message, false));
  </script>
</body>
</html>"""


ADMIN_SUPPRESSIONS_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Suppressions</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --red: #b42318;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: 360px minmax(420px, 1fr) minmax(360px, .8fr);
      gap: 14px;
      padding: 14px;
    }
    section {
      min-width: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { min-width: 0; padding: 12px; display: grid; gap: 10px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, select, textarea {
      min-width: 0;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    textarea {
      min-height: 150px;
      resize: vertical;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--blue); }
    button.danger { border-color: var(--red); color: var(--red); background: #fff; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .inline {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .items {
      display: grid;
      gap: 6px;
      max-height: calc(100vh - 260px);
      overflow: auto;
    }
    .item {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 8px;
      text-align: left;
      color: var(--text);
    }
    .item small { display: block; color: var(--muted); margin-top: 3px; }
    .item.selected { border-color: var(--blue); background: #eff6ff; box-shadow: inset 3px 0 0 var(--blue); }
    .stats {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    .stat {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfcfe;
    }
    .stat strong { display: block; font-size: 18px; }
    .stat span { color: var(--muted); font-size: 12px; }
    pre {
      margin: 0;
      min-height: 300px;
      max-height: calc(100vh - 220px);
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    @media (max-width: 1180px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      .inline, .stats { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Suppressions</h1>
    <div class="actions">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/admin/journeys'">Journey Manager</button>
      <button class="secondary" onclick="location.href='/admin/delivery'">Delivery Manager</button>
      <button class="secondary" onclick="location.href='/admin/suppressions'">Suppressions</button>
      <button class="secondary" onclick="location.href='/admin/analytics'">Analytics</button>
      <button class="secondary" onclick="location.href='/admin/data-sources'">Data Sources</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <section>
      <div class="head"><h2>Suppression List</h2><button id="refresh">Refresh</button></div>
      <div class="body">
        <label>Search email or reason
          <input id="search" placeholder="customer@example.com or spam_complaint" />
        </label>
        <div class="stats" id="stats"></div>
        <div class="items" id="items"></div>
      </div>
    </section>
    <section>
      <div class="head">
        <h2>Manual Suppression</h2>
        <div class="actions">
          <button id="save">Save Suppression</button>
          <button class="danger" id="delete">Delete Selected</button>
        </div>
      </div>
      <div class="body">
        <label>Email
          <input id="email" type="email" />
        </label>
        <div class="inline">
          <label>Reason
            <select id="reason">
              <option value="manual">manual</option>
              <option value="unsubscribe">unsubscribe</option>
              <option value="hard_bounce">hard_bounce</option>
              <option value="spam_complaint">spam_complaint</option>
            </select>
          </label>
          <label>Source
            <input id="source" value="manual_admin" />
          </label>
        </div>
        <div class="inline">
          <label>Provider message id
            <input id="providerMessageId" />
          </label>
          <label>Contact id
            <input id="contactId" />
          </label>
        </div>
        <label>Metadata JSON
          <textarea id="metadataJson"></textarea>
        </label>
      </div>
    </section>
    <section>
      <div class="head"><h2>Response</h2><button class="secondary" id="clear">Clear</button></div>
      <div class="body">
        <pre id="result"></pre>
      </div>
    </section>
  </main>
  <script>
    let selectedId = "";
    let suppressions = [];
    const result = document.getElementById("result");

    function writeResult(data, ok = true) {
      result.textContent = JSON.stringify({ ok, data }, null, 2);
    }

    async function readResponse(response) {
      const text = await response.text();
      try { return text ? JSON.parse(text) : null; } catch { return text; }
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      const data = await readResponse(response);
      writeResult(data, response.ok);
      if (!response.ok) throw new Error(data.detail || `${path} failed`);
      return data;
    }

    function markSelected(containerId, id) {
      document.querySelectorAll(`#${containerId} .item`).forEach((item) => {
        item.classList.toggle("selected", item.dataset.id === id);
      });
    }

    function parseMetadata() {
      const raw = document.getElementById("metadataJson").value.trim();
      return raw ? JSON.parse(raw) : {};
    }

    function resetForm() {
      selectedId = "";
      document.getElementById("email").value = "";
      document.getElementById("reason").value = "manual";
      document.getElementById("source").value = "manual_admin";
      document.getElementById("providerMessageId").value = "";
      document.getElementById("contactId").value = "";
      document.getElementById("metadataJson").value = JSON.stringify({ source: "admin" }, null, 2);
    }

    function selectSuppression(item) {
      selectedId = item.id;
      markSelected("items", selectedId);
      document.getElementById("email").value = item.email || "";
      document.getElementById("reason").value = item.reason || "manual";
      document.getElementById("source").value = item.source || "manual_admin";
      document.getElementById("providerMessageId").value = item.provider_message_id || "";
      document.getElementById("contactId").value = item.contact_id || "";
      document.getElementById("metadataJson").value = JSON.stringify(
        item.metadata_json || {},
        null,
        2
      );
      writeResult(item);
    }

    function renderStats(items, total) {
      const counts = items.reduce((acc, item) => {
        acc[item.reason] = (acc[item.reason] || 0) + 1;
        return acc;
      }, {});
      const stats = document.getElementById("stats");
      stats.textContent = "";
      [{ label: "Total", value: total }, ...Object.entries(counts).map(([label, value]) => ({
        label,
        value
      }))].forEach((item) => {
        const node = document.createElement("div");
        node.className = "stat";
        node.innerHTML = `<strong>${item.value}</strong><span>${item.label}</span>`;
        stats.appendChild(node);
      });
    }

    function renderItems() {
      const query = document.getElementById("search").value.trim().toLowerCase();
      const filtered = suppressions.filter((item) => {
        const text = `${item.email} ${item.reason} ${item.source}`.toLowerCase();
        return !query || text.includes(query);
      });
      const container = document.getElementById("items");
      container.textContent = "";
      filtered.forEach((item) => {
        const button = document.createElement("button");
        button.className = `item${selectedId === item.id ? " selected" : ""}`;
        button.dataset.id = item.id;
        button.type = "button";
        button.textContent = item.email;
        const detail = document.createElement("small");
        detail.textContent = `${item.reason} - ${item.source} - ${item.id}`;
        button.appendChild(detail);
        button.addEventListener("click", () => selectSuppression(item));
        container.appendChild(button);
      });
    }

    async function loadSuppressions() {
      const data = await request("/api/v1/suppressions/list?limit=500&offset=0");
      suppressions = data.items;
      renderStats(suppressions, data.total);
      renderItems();
    }

    async function saveSuppression() {
      const payload = {
        email: document.getElementById("email").value.trim(),
        reason: document.getElementById("reason").value,
        source: document.getElementById("source").value.trim() || "manual_admin",
        provider_message_id: document.getElementById("providerMessageId").value.trim() || null,
        contact_id: document.getElementById("contactId").value.trim() || null,
        metadata_json: parseMetadata()
      };
      await request("/api/v1/suppressions", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      await loadSuppressions();
    }

    async function deleteSuppression() {
      if (!selectedId) {
        writeResult("Select a suppression first.", false);
        return;
      }
      await request(`/api/v1/suppressions/${selectedId}`, { method: "DELETE" });
      resetForm();
      await loadSuppressions();
    }

    document.getElementById("refresh").addEventListener("click", () => {
      loadSuppressions().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("search").addEventListener("input", renderItems);
    document.getElementById("save").addEventListener("click", () => {
      saveSuppression().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("delete").addEventListener("click", () => {
      deleteSuppression().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("clear").addEventListener("click", () => {
      result.textContent = "";
    });

    resetForm();
    loadSuppressions().catch((error) => writeResult(error.message, false));
  </script>
</body>
</html>"""


ADMIN_DATA_SOURCES_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Data Sources</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --red: #b42318;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: 280px minmax(420px, .9fr) minmax(420px, 1fr);
      gap: 14px;
      padding: 14px;
    }
    section {
      min-width: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { min-width: 0; padding: 12px; display: grid; gap: 10px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, select, textarea {
      min-width: 0;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    textarea {
      min-height: 120px;
      resize: vertical;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--blue); }
    button.danger { border-color: var(--red); color: var(--red); background: #fff; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .items {
      display: grid;
      gap: 6px;
      max-height: calc(100vh - 190px);
      overflow: auto;
    }
    .item {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 8px;
      text-align: left;
      color: var(--text);
    }
    .item small { display: block; color: var(--muted); margin-top: 3px; }
    .item.selected { border-color: var(--blue); background: #eff6ff; box-shadow: inset 3px 0 0 var(--blue); }
    .inline {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    pre {
      margin: 0;
      min-height: 300px;
      max-height: calc(100vh - 220px);
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    @media (max-width: 1280px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      .inline { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Data Sources</h1>
    <div class="actions">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/admin/journeys'">Journey Manager</button>
      <button class="secondary" onclick="location.href='/admin/delivery'">Delivery Manager</button>
      <button class="secondary" onclick="location.href='/admin/suppressions'">Suppressions</button>
      <button class="secondary" onclick="location.href='/admin/analytics'">Analytics</button>
      <button class="secondary" onclick="location.href='/admin/data-sources'">Data Sources</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <section>
      <div class="head"><h2>Sources</h2><button id="refreshSources">Refresh</button></div>
      <div class="body">
        <button class="secondary" id="newSource">New Source</button>
        <div class="items" id="sources"></div>
      </div>
    </section>
    <section>
      <div class="head">
        <h2>Editor</h2>
        <div class="actions">
          <button id="saveSource">Save Source</button>
          <button class="danger" id="deleteSource">Delete Source</button>
        </div>
      </div>
      <div class="body">
        <label>Name
          <input id="sourceName" />
        </label>
        <div class="inline">
          <label>Type
            <select id="sourceType">
              <option value="manual">manual</option>
              <option value="csv">csv</option>
              <option value="rest_api">rest_api</option>
              <option value="postgres">postgres</option>
              <option value="mysql">mysql</option>
              <option value="snowflake">snowflake</option>
              <option value="bigquery">bigquery</option>
            </select>
          </label>
          <label>Secret ref
            <input id="secretRef" />
          </label>
        </div>
        <label>Config JSON
          <textarea id="sourceConfig"></textarea>
        </label>
        <div class="head">
          <h2>Mappings</h2>
          <div class="actions">
            <button class="secondary" id="validateSource">Validate Source</button>
            <button class="secondary" id="discoverSchema">Discover Schema</button>
            <button class="secondary" id="refreshMappings">Refresh</button>
          </div>
        </div>
        <div class="actions">
          <button class="secondary" id="newMapping">New Mapping</button>
          <button id="saveMapping">Save Mapping</button>
          <button class="danger" id="deleteMapping">Delete Mapping</button>
        </div>
        <label>Mapping name
          <input id="mappingName" />
        </label>
        <label>Object type
          <input id="objectType" value="contact" />
        </label>
        <label>Mapping JSON
          <textarea id="mappingJson"></textarea>
        </label>
        <label>Extraction plan JSON
          <textarea id="extractionPlan"></textarea>
        </label>
        <div class="items" id="mappings"></div>
        <div class="head">
          <h2>Ingestion</h2>
          <button class="secondary" id="loadImportJobs">Import Jobs</button>
        </div>
        <div class="actions">
          <button id="ingestRows">Ingest Rows</button>
          <button class="secondary" id="dryRunRows">Dry Run</button>
        </div>
        <label>Rows JSON
          <textarea id="ingestRowsJson"></textarea>
        </label>
      </div>
    </section>
    <section>
      <div class="head"><h2>Response</h2><button class="secondary" id="clear">Clear</button></div>
      <div class="body">
        <pre id="result"></pre>
      </div>
    </section>
  </main>
  <script>
    let selectedSourceId = "";
    let selectedMappingId = "";
    const result = document.getElementById("result");

    function writeResult(data, ok = true) {
      result.textContent = JSON.stringify({ ok, data }, null, 2);
    }

    async function readResponse(response) {
      const text = await response.text();
      try { return text ? JSON.parse(text) : null; } catch { return text; }
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      const data = await readResponse(response);
      writeResult(data, response.ok);
      if (!response.ok) throw new Error(data.detail || `${path} failed`);
      return data;
    }

    function markSelected(containerId, id) {
      document.querySelectorAll(`#${containerId} .item`).forEach((item) => {
        item.classList.toggle("selected", item.dataset.id === id);
      });
    }

    function parseJson(id, fallback) {
      const raw = document.getElementById(id).value.trim();
      return raw ? JSON.parse(raw) : fallback;
    }

    function resetSource() {
      selectedSourceId = "";
      selectedMappingId = "";
      document.getElementById("sourceName").value = `source-${Date.now()}`;
      document.getElementById("sourceType").value = "manual";
      document.getElementById("secretRef").value = "";
      document.getElementById("sourceConfig").value = JSON.stringify({ source: "admin" }, null, 2);
      resetMapping();
    }

    function resetMapping() {
      selectedMappingId = "";
      document.getElementById("mappingName").value = `mapping-${Date.now()}`;
      document.getElementById("objectType").value = "contact";
      document.getElementById("mappingJson").value = JSON.stringify(
        { email: "email", first_name: "first_name", attributes: {} },
        null,
        2
      );
      document.getElementById("extractionPlan").value = "{}";
      document.getElementById("ingestRowsJson").value = JSON.stringify(
        [{ email: "person@example.com", first_name: "Person", segment: "demo" }],
        null,
        2
      );
    }

    function selectSource(item) {
      selectedSourceId = item.id;
      selectedMappingId = "";
      markSelected("sources", selectedSourceId);
      document.getElementById("sourceName").value = item.name || "";
      document.getElementById("sourceType").value = item.source_type || "manual";
      document.getElementById("secretRef").value = item.secret_ref || "";
      document.getElementById("sourceConfig").value = JSON.stringify(item.config || {}, null, 2);
      writeResult(item);
      resetMapping();
      loadMappings().catch((error) => writeResult(error.message, false));
    }

    function selectMapping(item) {
      selectedMappingId = item.id;
      selectedSourceId = item.data_source_id || selectedSourceId;
      markSelected("mappings", selectedMappingId);
      document.getElementById("mappingName").value = item.name || "";
      document.getElementById("objectType").value = item.object_type || "contact";
      document.getElementById("mappingJson").value = JSON.stringify(item.mapping || {}, null, 2);
      document.getElementById("extractionPlan").value = JSON.stringify(
        item.extraction_plan || {},
        null,
        2
      );
      writeResult(item);
    }

    async function loadSources() {
      const data = await request("/api/v1/data-sources/list?limit=100&offset=0");
      const container = document.getElementById("sources");
      container.textContent = "";
      data.items.forEach((item) => {
        const button = document.createElement("button");
        button.className = `item${selectedSourceId === item.id ? " selected" : ""}`;
        button.dataset.id = item.id;
        button.type = "button";
        button.textContent = item.name;
        const detail = document.createElement("small");
        detail.textContent = `${item.source_type} - ${item.status} - ${item.id}`;
        button.appendChild(detail);
        button.addEventListener("click", () => selectSource(item));
        container.appendChild(button);
      });
    }

    async function loadMappings() {
      const query = selectedSourceId
        ? `?data_source_id=${selectedSourceId}`
        : "?limit=100&offset=0";
      const data = await request(`/api/v1/data-source-mappings/list${query}`);
      const container = document.getElementById("mappings");
      container.textContent = "";
      data.items.forEach((item) => {
        const button = document.createElement("button");
        button.className = `item${selectedMappingId === item.id ? " selected" : ""}`;
        button.dataset.id = item.id;
        button.type = "button";
        button.textContent = item.name;
        const detail = document.createElement("small");
        detail.textContent = `${item.object_type} - ${item.id}`;
        button.appendChild(detail);
        button.addEventListener("click", () => selectMapping(item));
        container.appendChild(button);
      });
    }

    async function saveSource() {
      const payload = {
        name: document.getElementById("sourceName").value.trim(),
        source_type: document.getElementById("sourceType").value,
        config: parseJson("sourceConfig", {}),
        secret_ref: document.getElementById("secretRef").value.trim() || null
      };
      const path = selectedSourceId
        ? `/api/v1/data-sources/${selectedSourceId}`
        : "/api/v1/data-sources";
      const method = selectedSourceId ? "PATCH" : "POST";
      const saved = await request(path, { method, body: JSON.stringify(payload) });
      selectedSourceId = saved.id;
      await loadSources();
    }

    async function deleteSource() {
      if (!selectedSourceId) {
        writeResult("Select a data source first.", false);
        return;
      }
      await request(`/api/v1/data-sources/${selectedSourceId}`, { method: "DELETE" });
      resetSource();
      await loadSources();
      await loadMappings();
    }

    async function validateSource() {
      if (!selectedSourceId) {
        writeResult("Select or save a data source first.", false);
        return;
      }
      await request(`/api/v1/data-sources/${selectedSourceId}/validate`, { method: "POST" });
    }

    async function discoverSchema() {
      if (!selectedSourceId) {
        writeResult("Select or save a data source first.", false);
        return;
      }
      await request(`/api/v1/data-sources/${selectedSourceId}/schema`);
    }

    async function saveMapping() {
      if (!selectedSourceId) {
        writeResult("Select or save a data source first.", false);
        return;
      }
      const payload = {
        data_source_id: selectedSourceId,
        name: document.getElementById("mappingName").value.trim(),
        object_type: document.getElementById("objectType").value.trim(),
        mapping: parseJson("mappingJson", {}),
        extraction_plan: parseJson("extractionPlan", {})
      };
      const path = selectedMappingId
        ? `/api/v1/data-source-mappings/${selectedMappingId}`
        : "/api/v1/data-source-mappings";
      const method = selectedMappingId ? "PATCH" : "POST";
      const saved = await request(path, { method, body: JSON.stringify(payload) });
      selectedMappingId = saved.id;
      await loadMappings();
    }

    async function deleteMapping() {
      if (!selectedMappingId) {
        writeResult("Select a mapping first.", false);
        return;
      }
      await request(`/api/v1/data-source-mappings/${selectedMappingId}`, { method: "DELETE" });
      resetMapping();
      await loadMappings();
    }

    async function ingestRows(dryRun) {
      if (!selectedSourceId || !selectedMappingId) {
        writeResult("Select a data source and mapping first.", false);
        return;
      }
      const payload = {
        mapping_id: selectedMappingId,
        rows: parseJson("ingestRowsJson", []),
        dry_run: dryRun,
        metadata_json: { source: "admin_data_sources" }
      };
      await request(`/api/v1/data-sources/${selectedSourceId}/ingest`, {
        method: "POST",
        body: JSON.stringify(payload)
      });
    }

    async function loadImportJobs() {
      const query = selectedSourceId
        ? `?data_source_id=${selectedSourceId}&limit=100&offset=0`
        : "?limit=100&offset=0";
      await request(`/api/v1/data-source-import-jobs/list${query}`);
    }

    document.getElementById("refreshSources").addEventListener("click", () => {
      loadSources().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("refreshMappings").addEventListener("click", () => {
      loadMappings().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("newSource").addEventListener("click", resetSource);
    document.getElementById("newMapping").addEventListener("click", resetMapping);
    document.getElementById("saveSource").addEventListener("click", () => {
      saveSource().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("deleteSource").addEventListener("click", () => {
      deleteSource().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("validateSource").addEventListener("click", () => {
      validateSource().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("discoverSchema").addEventListener("click", () => {
      discoverSchema().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("saveMapping").addEventListener("click", () => {
      saveMapping().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("deleteMapping").addEventListener("click", () => {
      deleteMapping().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("ingestRows").addEventListener("click", () => {
      ingestRows(false).catch((error) => writeResult(error.message, false));
    });
    document.getElementById("dryRunRows").addEventListener("click", () => {
      ingestRows(true).catch((error) => writeResult(error.message, false));
    });
    document.getElementById("loadImportJobs").addEventListener("click", () => {
      loadImportJobs().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("clear").addEventListener("click", () => {
      result.textContent = "";
    });

    resetSource();
    loadSources()
      .then(loadMappings)
      .catch((error) => writeResult(error.message, false));
  </script>
</body>
</html>"""


ADMIN_ENTITIES_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Entity Workbench</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --red: #b42318;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      font-size: 14px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: 260px minmax(360px, .8fr) minmax(420px, 1fr);
      gap: 14px;
      padding: 14px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .head {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { padding: 12px; display: grid; gap: 10px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    textarea {
      min-height: 360px;
      resize: vertical;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
    }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #fff; color: var(--blue); }
    button.danger { border-color: var(--red); color: var(--red); background: #fff; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .items { display: grid; gap: 6px; max-height: calc(100vh - 180px); overflow: auto; }
    .item {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 8px;
      text-align: left;
      color: var(--text);
    }
    .item small { display: block; color: var(--muted); margin-top: 3px; }
    .item.selected { border-color: var(--blue); background: #eff6ff; box-shadow: inset 3px 0 0 var(--blue); }
    pre {
      margin: 0;
      min-height: 260px;
      max-height: 420px;
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    @media (max-width: 1100px) {
      main { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Entity Workbench</h1>
    <div class="actions">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/admin/journeys'">Journey Manager</button>
      <button class="secondary" onclick="location.href='/admin/delivery'">Delivery Manager</button>
      <button class="secondary" onclick="location.href='/admin/suppressions'">Suppressions</button>
      <button class="secondary" onclick="location.href='/admin/analytics'">Analytics</button>
      <button class="secondary" onclick="location.href='/admin/data-sources'">Data Sources</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <section>
      <div class="head"><h2>Resource</h2><button id="refresh">Refresh</button></div>
      <div class="body">
        <label>Entity
          <select id="resource"></select>
        </label>
        <label>Query string
          <input id="query" value="limit=100&offset=0" />
        </label>
        <div class="items" id="items"></div>
      </div>
    </section>
    <section>
      <div class="head">
        <h2>Editor</h2>
        <div class="actions">
          <button class="secondary" id="new">New</button>
          <button id="save">Save</button>
          <button class="danger" id="delete">Delete</button>
        </div>
      </div>
      <div class="body">
        <textarea id="editor"></textarea>
      </div>
    </section>
    <section>
      <div class="head"><h2>Response</h2><button class="secondary" id="clear">Clear</button></div>
      <div class="body">
        <pre id="result"></pre>
      </div>
    </section>
  </main>
  <script>
    const resources = {
      templates: {
        label: "Templates",
        list: "/api/v1/templates",
        create: "/api/v1/templates",
        item: "/api/v1/templates/{id}",
        sample: {
          name: `template-${Date.now()}`,
          subject: "Hello {{ first_name }}",
          html_body: "<p>Hello {{ first_name }}</p>",
          css_body: "body { font-family: Arial, sans-serif; }",
          text_body: "Hello {{ first_name }}"
        }
      },
      contacts: {
        label: "Contacts",
        list: "/api/v1/audiences/contacts",
        create: "/api/v1/audiences/contacts",
        item: "/api/v1/audiences/contacts/{id}",
        sample: {
          email: `contact-${Date.now()}@example.com`,
          first_name: "Alex",
          last_name: "Tester",
          source: "admin_workbench",
          attributes: { plan: "trial" }
        }
      },
      campaigns: {
        label: "Campaigns",
        list: "/api/v1/campaigns",
        create: "/api/v1/campaigns",
        item: "/api/v1/campaigns/{id}",
        sample: {
          name: `campaign-${Date.now()}`,
          template_id: "00000000-0000-0000-0000-000000000000",
          audience_query: {}
        }
      },
      audiences: {
        label: "Audiences",
        list: "/api/v1/audiences",
        create: "/api/v1/audiences",
        item: "/api/v1/audiences/{id}",
        sample: {
          name: `audience-${Date.now()}`,
          description: "Created from admin workbench",
          rule_tree: {}
        }
      },
      dataSources: {
        label: "Data Sources",
        list: "/api/v1/data-sources",
        create: "/api/v1/data-sources",
        item: "/api/v1/data-sources/{id}",
        sample: {
          name: `source-${Date.now()}`,
          source_type: "manual",
          config: { source: "admin_workbench" }
        }
      },
      mappings: {
        label: "Data Source Mappings",
        list: "/api/v1/data-source-mappings",
        create: "/api/v1/data-source-mappings",
        item: "/api/v1/data-source-mappings/{id}",
        sample: {
          data_source_id: "00000000-0000-0000-0000-000000000000",
          name: `mapping-${Date.now()}`,
          object_type: "contact",
          mapping: { email: "email" },
          extraction_plan: {}
        }
      },
      sendJobs: {
        label: "Send Jobs",
        list: "/api/v1/campaign-send-jobs/list",
        readonly: true,
        sample: {}
      },
      sendRecords: {
        label: "Send Records",
        list: "/api/v1/email-send-records/list",
        readonly: true,
        sample: {}
      },
      suppressions: {
        label: "Suppressions",
        list: "/api/v1/suppressions",
        readonly: true,
        sample: {}
      },
      events: {
        label: "Events",
        list: "/api/v1/events",
        create: "/api/v1/events",
        item: "/api/v1/events/{id}",
        sample: {
          event_type: "opened",
          metadata_json: { source: "admin_workbench" }
        }
      }
    };

    let selectedId = "";

    function current() {
      return resources[document.getElementById("resource").value];
    }

    function writeResult(data, ok = true) {
      document.getElementById("result").textContent = JSON.stringify({ ok, data }, null, 2);
    }

    function readEditor() {
      return JSON.parse(document.getElementById("editor").value || "{}");
    }

    function urlWithQuery(url) {
      const query = document.getElementById("query").value.trim();
      return query ? `${url}?${query}` : url;
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
      });
      const text = await response.text();
      let data;
      try { data = text ? JSON.parse(text) : null; } catch { data = text; }
      writeResult(data, response.ok);
      if (!response.ok) throw new Error(`${path} failed`);
      return data;
    }

    function pickItems(data) {
      return Array.isArray(data) ? data : data.items || [];
    }

    function titleFor(item) {
      return item.name || item.email || item.to_email || item.id || "(item)";
    }

    async function loadList() {
      const resource = current();
      const data = await request(urlWithQuery(resource.list));
      const list = document.getElementById("items");
      list.textContent = "";
      pickItems(data).forEach((item) => {
        const button = document.createElement("button");
        button.className = `item${selectedId === item.id ? " selected" : ""}`;
        button.dataset.id = item.id || "";
        button.type = "button";
        const title = document.createTextNode(titleFor(item));
        const detail = document.createElement("small");
        detail.textContent = item.id || item.status || "";
        button.append(title, detail);
        button.addEventListener("click", () => {
          selectedId = item.id || "";
          document.querySelectorAll("#items .item").forEach((node) => {
            node.classList.toggle("selected", node.dataset.id === selectedId);
          });
          document.getElementById("editor").value = JSON.stringify(item, null, 2);
          writeResult(item);
        });
        list.appendChild(button);
      });
    }

    function newItem() {
      selectedId = "";
      document.getElementById("editor").value = JSON.stringify(current().sample, null, 2);
    }

    async function saveItem() {
      const resource = current();
      if (resource.readonly) {
        writeResult("This resource is read-only in the workbench.", false);
        return;
      }
      const body = readEditor();
      const method = selectedId && resource.item ? "PATCH" : "POST";
      const path = selectedId && resource.item
        ? resource.item.replace("{id}", selectedId)
        : resource.create;
      const saved = await request(path, { method, body: JSON.stringify(body) });
      selectedId = saved && saved.id ? saved.id : selectedId;
      await loadList();
    }

    async function deleteItem() {
      const resource = current();
      if (!selectedId || !resource.item || resource.readonly) {
        writeResult("Select a deletable item first.", false);
        return;
      }
      await request(resource.item.replace("{id}", selectedId), { method: "DELETE" });
      selectedId = "";
      newItem();
      await loadList();
    }

    const select = document.getElementById("resource");
    Object.entries(resources).forEach(([key, value]) => {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = value.label;
      select.appendChild(option);
    });
    select.addEventListener("change", () => {
      selectedId = "";
      newItem();
      loadList().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("refresh").addEventListener("click", () => {
      loadList().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("new").addEventListener("click", newItem);
    document.getElementById("save").addEventListener("click", () => {
      saveItem().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("delete").addEventListener("click", () => {
      deleteItem().catch((error) => writeResult(error.message, false));
    });
    document.getElementById("clear").addEventListener("click", () => {
      document.getElementById("result").textContent = "";
    });
    newItem();
    loadList().catch((error) => writeResult(error.message, false));
  </script>
</body>
</html>"""
