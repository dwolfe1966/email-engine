from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get('/admin', response_class=HTMLResponse, include_in_schema=False)
def admin_home() -> str:
    return ADMIN_HOME_HTML


@router.get('/admin/entities', response_class=HTMLResponse, include_in_schema=False)
def admin_entities() -> str:
    return ADMIN_ENTITIES_HTML


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
      padding: 18px 22px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      padding: 14px;
      max-width: 1120px;
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
  <header><h1>Email Engine Admin</h1></header>
  <main>
    <a href="/admin/entities">
      <strong>Entity Workbench</strong>
      <span>List, create, update, and delete core API entities from one page.</span>
    </a>
    <a href="/template-editor">
      <strong>Template Editor</strong>
      <span>Edit subject, HTML, CSS, text, variables, validation, and preview.</span>
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
      <button class="secondary" onclick="location.href='/template-editor'">Templates</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
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
        button.className = "item";
        button.type = "button";
        const title = document.createTextNode(titleFor(item));
        const detail = document.createElement("small");
        detail.textContent = item.id || item.status || "";
        button.append(title, detail);
        button.addEventListener("click", () => {
          selectedId = item.id || "";
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
