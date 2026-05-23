from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get('/template-editor', response_class=HTMLResponse, include_in_schema=False)
def template_editor() -> str:
    return TEMPLATE_EDITOR_HTML


TEMPLATE_EDITOR_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine Template Editor</title>
  <style>
    :root {
      color-scheme: light;
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
      gap: 16px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { margin: 0; font-size: 20px; }
    main {
      display: grid;
      grid-template-columns: 280px minmax(420px, 1fr) minmax(360px, .8fr);
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
      padding: 11px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    h2 { margin: 0; font-size: 14px; }
    .body { padding: 12px; display: grid; gap: 10px; }
    label { display: grid; gap: 5px; color: var(--muted); font-size: 12px; }
    input, textarea, select {
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
    #htmlBody { min-height: 320px; }
    button {
      border: 1px solid var(--blue);
      background: var(--blue);
      color: white;
      border-radius: 6px;
      padding: 8px 10px;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: white; color: var(--blue); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
      padding: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f9fafb;
    }
    .toolbar button, .toolbar select {
      min-height: 32px;
      padding: 5px 8px;
      font-size: 12px;
    }
    .toolbar button {
      min-width: 34px;
      background: white;
      color: var(--blue);
    }
    .toolbar select {
      width: auto;
    }
    .css-builder {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #f9fafb;
      display: grid;
      gap: 10px;
    }
    .css-builder-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .css-builder input[type="color"] {
      min-height: 36px;
      padding: 4px;
    }
    .template-list { display: grid; gap: 6px; max-height: calc(100vh - 160px); overflow: auto; }
    .template-item {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      cursor: pointer;
      background: #fff;
      text-align: left;
      color: var(--text);
      font-weight: 500;
    }
    .template-item small { display: block; color: var(--muted); margin-top: 3px; }
    pre {
      margin: 0;
      min-height: 150px;
      max-height: 280px;
      overflow: auto;
      background: #0f172a;
      color: #e5edf8;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    iframe {
      width: 100%;
      min-height: 320px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: white;
    }
    .variable-panel {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f9fafb;
      padding: 10px;
      display: grid;
      gap: 8px;
    }
    .variable-list {
      display: grid;
      gap: 6px;
    }
    .variable-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 7px 8px;
    }
    .variable-row strong,
    .variable-row small {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .variable-row small { color: var(--muted); margin-top: 2px; }
    .variable-kind {
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--muted);
      padding: 2px 7px;
      font-size: 11px;
      font-weight: 700;
      background: #fff;
    }
    #visualEditor { min-height: 360px; }
    .error { color: var(--red); }
    @media (max-width: 1100px) {
      main { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine Template Editor</h1>
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
        <h2>Templates</h2>
        <button class="secondary" id="refreshTemplates">Refresh</button>
      </div>
      <div class="body">
        <div class="template-list" id="templateList"></div>
      </div>
    </section>

    <section>
      <div class="head">
        <h2>Editor</h2>
        <div class="actions">
          <button class="secondary" id="newTemplate">New</button>
          <button id="saveTemplate">Save</button>
        </div>
      </div>
      <div class="body">
        <label>Name
          <input id="templateName" />
        </label>
        <label>Subject
          <input id="subject" value="Hello {{ first_name }}" />
        </label>
        <label>Visual Designer
          <div class="toolbar">
            <select id="formatBlock">
              <option value="p">Paragraph</option>
              <option value="h1">Heading 1</option>
              <option value="h2">Heading 2</option>
              <option value="h3">Heading 3</option>
              <option value="blockquote">Quote</option>
            </select>
            <button class="secondary" type="button" data-command="bold">B</button>
            <button class="secondary" type="button" data-command="italic">I</button>
            <button class="secondary" type="button" data-command="underline">U</button>
            <button class="secondary" type="button" data-command="insertUnorderedList">List</button>
            <button class="secondary" type="button" data-command="insertOrderedList">1-2</button>
            <button class="secondary" type="button" id="insertLink">Link</button>
            <button class="secondary" type="button" id="insertVariable">Variable</button>
            <button class="secondary" type="button" id="syncFromSource">Source -> Visual</button>
            <button class="secondary" type="button" id="syncToSource">Visual -> Source</button>
          </div>
          <iframe id="visualEditor"></iframe>
        </label>
        <label>HTML
          <textarea id="htmlBody"><p>Hello {{ first_name }},</p>
{% if plan == "trial" %}
  <p>Your trial plan is active.</p>
{% else %}
  <p>Your plan is {{ plan }}.</p>
{% endif %}
<ul>
{% for item in recommendations %}
  <li>{{ loop.index }}. {{ item }}</li>
{% endfor %}
</ul></textarea>
        </label>
        <label>CSS
          <textarea id="cssBody">body {
  font-family: Arial, sans-serif;
  color: #17202a;
}
p {
  line-height: 1.5;
}
li {
  margin: 4px 0;
}</textarea>
        </label>
        <div class="css-builder">
          <strong>CSS Builder</strong>
          <div class="css-builder-grid">
            <label>Preset
              <select id="cssPreset">
                <option value="newsletter">Newsletter</option>
                <option value="announcement">Announcement</option>
                <option value="transactional">Transactional</option>
              </select>
            </label>
            <label>Font
              <select id="cssFont">
                <option value="Arial, sans-serif">Arial</option>
                <option value="Helvetica, Arial, sans-serif">Helvetica</option>
                <option value="Georgia, serif">Georgia</option>
                <option value="'Trebuchet MS', Arial, sans-serif">Trebuchet</option>
              </select>
            </label>
            <label>Brand color
              <input id="cssBrandColor" type="color" value="#2563eb" />
            </label>
            <label>Accent color
              <input id="cssAccentColor" type="color" value="#16a34a" />
            </label>
            <label>Max width
              <select id="cssMaxWidth">
                <option value="600">600px</option>
                <option value="640">640px</option>
                <option value="720">720px</option>
              </select>
            </label>
            <label>Button radius
              <select id="cssButtonRadius">
                <option value="4">4px</option>
                <option value="8">8px</option>
                <option value="999">Pill</option>
              </select>
            </label>
            <label>Block
              <select id="emailBlock">
                <option value="shell">Email shell</option>
                <option value="hero">Hero</option>
                <option value="card">Card</option>
                <option value="callout">Callout</option>
                <option value="summary">Summary table</option>
                <option value="footer">Footer</option>
              </select>
            </label>
          </div>
          <div class="actions">
            <button class="secondary" type="button" id="generateCss">Generate CSS</button>
            <button class="secondary" type="button" id="appendCss">Append CSS</button>
            <button class="secondary" type="button" id="insertButtonHtml">Insert Button</button>
            <button class="secondary" type="button" id="insertBlockHtml">Insert Block</button>
          </div>
        </div>
        <label>Text
          <textarea id="textBody">Hello {{ first_name }}. Your plan is {{ plan }}.</textarea>
        </label>
      </div>
    </section>

    <section>
      <div class="head">
        <h2>Render</h2>
        <div class="actions">
          <button class="secondary" id="inspectVariables">Inspect Variables</button>
          <button class="secondary" id="lintTemplate">Lint</button>
          <button class="secondary" id="validateTemplate">Validate</button>
          <button id="previewTemplate">Preview</button>
        </div>
      </div>
      <div class="body">
        <label>Variables JSON
          <textarea id="variablesJson">{
  "first_name": "Alex",
  "plan": "trial",
  "recommendations": ["Map data", "Build audience", "Launch campaign"]
}</textarea>
        </label>
        <div class="variable-panel">
          <div class="actions">
            <strong>Detected Variables</strong>
            <button class="secondary" type="button" id="applySampleVariables">
              Use Sample JSON
            </button>
          </div>
          <div class="variable-list" id="variableList">
            <span class="muted">Run Inspect Variables to detect user and native fields.</span>
          </div>
        </div>
        <pre id="result"></pre>
        <iframe id="htmlPreview" sandbox=""></iframe>
      </div>
    </section>
  </main>

  <script>
    const state = { templateId: "", visualReady: false, sampleVariables: null };

    function value(id) { return document.getElementById(id).value; }

    function log(data) {
      document.getElementById("result").textContent = JSON.stringify(data, null, 2);
    }

    function variables() {
      return JSON.parse(value("variablesJson") || "{}");
    }

    function renderVariables(data) {
      state.sampleVariables = data.sample_variables || null;
      const list = document.getElementById("variableList");
      list.textContent = "";
      const rows = [...(data.variables || []), ...(data.native_variables || [])];
      if (!rows.length) {
        list.textContent = data.errors?.length ? "Unable to inspect template." : "No variables detected.";
        return;
      }
      rows.forEach((item) => {
        const row = document.createElement("div");
        row.className = "variable-row";
        const copy = document.createElement("div");
        const name = document.createElement("strong");
        const sources = document.createElement("small");
        const kind = document.createElement("span");
        name.textContent = item.name;
        sources.textContent = `sources: ${(item.sources || []).join(", ") || "unknown"}`;
        kind.className = "variable-kind";
        kind.textContent = item.native ? "native" : "user";
        copy.append(name, sources);
        row.append(copy, kind);
        list.appendChild(row);
      });
    }

    function visualDocument() {
      return document.getElementById("visualEditor").contentDocument;
    }

    function htmlDocument(html, css) {
      return `<!doctype html><html><head><style>
        body { padding: 14px; min-height: 320px; outline: none; }
        ${css || ""}
      </style></head><body contenteditable="true">${html || ""}</body></html>`;
    }

    function loadVisualFromSource() {
      const frame = document.getElementById("visualEditor");
      frame.srcdoc = htmlDocument(value("htmlBody"), value("cssBody"));
    }

    function syncSourceFromVisual() {
      const doc = visualDocument();
      if (!doc || !doc.body) return;
      document.getElementById("htmlBody").value = doc.body.innerHTML.trim();
    }

    function runCommand(command, value = null) {
      const doc = visualDocument();
      if (!doc) return;
      doc.body.focus();
      doc.execCommand(command, false, value);
      syncSourceFromVisual();
    }

    function emailCss() {
      const preset = value("cssPreset");
      const font = value("cssFont");
      const brand = value("cssBrandColor");
      const accent = value("cssAccentColor");
      const maxWidth = value("cssMaxWidth");
      const radius = value("cssButtonRadius");
      const presetRules = {
        newsletter: `
.eyebrow { color: ${accent}; font-size: 12px; font-weight: 700; text-transform: uppercase; }
.content-card { border: 1px solid #d8dee6; border-radius: 8px; padding: 20px; }
.article-list li { margin: 8px 0; }`,
        announcement: `
.hero { background: ${brand}; color: #ffffff; padding: 28px 24px; text-align: center; }
.hero h1 { color: #ffffff; margin: 0; }
.callout { background: #eff6ff; border-left: 4px solid ${brand}; padding: 14px; }`,
        transactional: `
.summary { width: 100%; border-collapse: collapse; }
.summary th, .summary td { border-bottom: 1px solid #d8dee6; padding: 10px; text-align: left; }
.meta { color: #5b6673; font-size: 13px; }`,
      };
      return `body {
  margin: 0;
  background: #f6f7f9;
  color: #17202a;
  font-family: ${font};
}
.email-shell {
  width: 100%;
  background: #f6f7f9;
  padding: 24px 0;
}
.email-container {
  max-width: ${maxWidth}px;
  margin: 0 auto;
  background: #ffffff;
  padding: 24px;
}
h1, h2, h3 {
  color: #17202a;
  margin: 0 0 12px;
}
p {
  margin: 0 0 14px;
  line-height: 1.55;
}
a {
  color: ${brand};
}
.button {
  display: inline-block;
  background: ${brand};
  color: #ffffff;
  text-decoration: none;
  padding: 11px 16px;
  border-radius: ${radius}px;
  font-weight: 700;
}
.secondary-text {
  color: #5b6673;
  font-size: 13px;
}
${presetRules[preset] || ""}`;
    }

    function applyGeneratedCss(mode) {
      const css = emailCss();
      const field = document.getElementById("cssBody");
      field.value = mode === "append" && field.value.trim()
        ? `${field.value.trim()}\n\n${css}`
        : css;
      loadVisualFromSource();
    }

    function blockHtml() {
      const block = value("emailBlock");
      const blocks = {
        shell: `<div class="email-shell">
  <div class="email-container">
    <p class="eyebrow">Update</p>
    <h1>Hello {{ first_name }}</h1>
    <p>Add your message here.</p>
    <p><a class="button" href="{{ cta_url }}">Call to Action</a></p>
  </div>
</div>`,
        hero: `<div class="hero">
  <p class="eyebrow">Announcement</p>
  <h1>Main headline</h1>
  <p>Short supporting message for {{ first_name }}.</p>
</div>`,
        card: `<div class="content-card">
  <h2>Section title</h2>
  <p>Use this block for grouped content, recommendations, or a product update.</p>
</div>`,
        callout: `<div class="callout">
  <strong>Important note</strong>
  <p>Add a concise message or status update here.</p>
</div>`,
        summary: `<table class="summary" role="presentation">
  <tr><th>Item</th><th>Status</th></tr>
  <tr><td>{{ item_name }}</td><td>{{ item_status }}</td></tr>
</table>`,
        footer: `<p class="secondary-text">
  You are receiving this email because you subscribed to updates.
  <a href="{{ unsubscribe_url }}">Unsubscribe</a>
</p>`,
      };
      return blocks[block] || "";
    }

    function payload() {
      syncSourceFromVisual();
      return {
        name: value("templateName"),
        subject: value("subject"),
        html_body: value("htmlBody"),
        css_body: value("cssBody") || null,
        text_body: value("textBody") || null,
      };
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
      });
      const text = await response.text();
      let data;
      try { data = text ? JSON.parse(text) : null; } catch { data = text; }
      if (!response.ok) {
        log({ error: data, status: response.status });
        throw new Error(`${path} failed`);
      }
      return data;
    }

    async function loadTemplates() {
      const templates = await request("/api/v1/templates?limit=100&offset=0");
      const list = document.getElementById("templateList");
      list.textContent = "";
      templates.forEach((template) => {
        const item = document.createElement("button");
        item.className = "template-item";
        const name = document.createTextNode(template.name);
        const subject = document.createElement("small");
        subject.textContent = template.subject;
        item.append(name, subject);
        item.addEventListener("click", () => selectTemplate(template));
        list.appendChild(item);
      });
    }

    function selectTemplate(template) {
      state.templateId = template.id;
      document.getElementById("templateName").value = template.name;
      document.getElementById("subject").value = template.subject;
      document.getElementById("htmlBody").value = template.html_body;
      document.getElementById("cssBody").value = template.css_body || "";
      document.getElementById("textBody").value = template.text_body || "";
      loadVisualFromSource();
      log({ selected: template.id });
    }

    async function validateTemplate() {
      const data = await request("/api/v1/templates/validate", {
        method: "POST",
        body: JSON.stringify({ ...payload(), variables: variables() }),
      });
      log(data);
    }

    async function inspectVariables() {
      const data = await request("/api/v1/templates/variables", {
        method: "POST",
        body: JSON.stringify({ ...payload(), variables: variables() }),
      });
      renderVariables(data);
      log(data);
    }

    async function lintTemplate() {
      const data = await request("/api/v1/templates/lint", {
        method: "POST",
        body: JSON.stringify({ ...payload(), variables: variables() }),
      });
      log(data);
    }

    async function previewTemplate() {
      const data = await request("/api/v1/templates/preview", {
        method: "POST",
        body: JSON.stringify({ ...payload(), variables: variables() }),
      });
      log(data);
      document.getElementById("htmlPreview").srcdoc = data.ok ? data.html_body : "";
    }

    async function saveTemplate() {
      const body = payload();
      const path = state.templateId ? `/api/v1/templates/${state.templateId}` : "/api/v1/templates";
      const method = state.templateId ? "PATCH" : "POST";
      const saved = await request(path, { method, body: JSON.stringify(body) });
      state.templateId = saved.id;
      log(saved);
      await loadTemplates();
    }

    document.getElementById("refreshTemplates").addEventListener("click", loadTemplates);
    document.getElementById("inspectVariables").addEventListener("click", inspectVariables);
    document.getElementById("applySampleVariables").addEventListener("click", () => {
      if (!state.sampleVariables) return;
      document.getElementById("variablesJson").value = JSON.stringify(
        state.sampleVariables,
        null,
        2,
      );
      log({ applied_sample_variables: Object.keys(state.sampleVariables) });
    });
    document.getElementById("lintTemplate").addEventListener("click", lintTemplate);
    document.getElementById("validateTemplate").addEventListener("click", validateTemplate);
    document.getElementById("previewTemplate").addEventListener("click", previewTemplate);
    document.getElementById("saveTemplate").addEventListener("click", saveTemplate);
    document.getElementById("htmlBody").addEventListener("blur", loadVisualFromSource);
    document.getElementById("cssBody").addEventListener("blur", loadVisualFromSource);
    document.getElementById("syncFromSource").addEventListener("click", loadVisualFromSource);
    document.getElementById("syncToSource").addEventListener("click", syncSourceFromVisual);
    document
      .getElementById("generateCss")
      .addEventListener("click", () => applyGeneratedCss("replace"));
    document
      .getElementById("appendCss")
      .addEventListener("click", () => applyGeneratedCss("append"));
    document.getElementById("insertButtonHtml").addEventListener("click", () => {
      runCommand("insertHTML", '<p><a class="button" href="{{ cta_url }}">Call to Action</a></p>');
    });
    document.getElementById("insertBlockHtml").addEventListener("click", () => {
      runCommand("insertHTML", blockHtml());
    });
    document.getElementById("formatBlock").addEventListener("change", (event) => {
      runCommand("formatBlock", event.target.value);
    });
    document.querySelectorAll("[data-command]").forEach((button) => {
      button.addEventListener("click", () => runCommand(button.dataset.command));
    });
    document.getElementById("insertLink").addEventListener("click", () => {
      const url = prompt("URL");
      if (url) runCommand("createLink", url);
    });
    document.getElementById("insertVariable").addEventListener("click", () => {
      const variable = prompt("Variable name", "first_name");
      if (variable) runCommand("insertText", `{{ ${variable} }}`);
    });
    document.getElementById("visualEditor").addEventListener("load", () => {
      const doc = visualDocument();
      if (!doc) return;
      doc.designMode = "on";
      doc.body.addEventListener("input", syncSourceFromVisual);
      doc.body.addEventListener("blur", syncSourceFromVisual);
      state.visualReady = true;
    });
    document.getElementById("newTemplate").addEventListener("click", () => {
      state.templateId = "";
      document.getElementById("templateName").value = `template-${Date.now()}`;
      loadVisualFromSource();
      log({ mode: "new" });
    });
    document.getElementById("templateName").value = `template-${Date.now()}`;
    loadVisualFromSource();
    loadTemplates().catch((error) => log({ error: error.message }));
  </script>
</body>
</html>"""
