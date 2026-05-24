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
    .editor-tabs {
      display: flex;
      gap: 6px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 8px;
    }
    .editor-tabs button {
      background: white;
      color: var(--blue);
    }
    .editor-tabs button.active {
      background: var(--blue);
      color: white;
    }
    .editor-panel { display: none; gap: 10px; }
    .editor-panel.active { display: grid; }
    .wysiwyg-shell {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }
    .wysiwyg-toolbar {
      border: 0;
      border-bottom: 1px solid var(--line);
      border-radius: 0;
    }
    .wysiwyg-blocks {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 8px;
      border-bottom: 1px solid var(--line);
      background: #fff;
    }
    .wysiwyg-blocks button {
      background: white;
      color: var(--blue);
      font-size: 12px;
      padding: 6px 8px;
    }
    .design-builder {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      display: grid;
      gap: 0;
      overflow: hidden;
    }
    .design-palette,
    .design-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 8px;
      background: #f9fafb;
      border-bottom: 1px solid var(--line);
    }
    .design-palette button,
    .design-actions button {
      background: white;
      color: var(--blue);
      font-size: 12px;
      padding: 6px 8px;
    }
    .design-block-list {
      display: grid;
      gap: 8px;
      padding: 10px;
    }
    .design-block-row {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      display: grid;
      gap: 7px;
      background: #fff;
    }
    .design-block-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }
    .design-block-head strong {
      font-size: 12px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: .03em;
    }
    .design-block-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    .design-doc-json {
      border-top: 1px solid var(--line);
      padding: 10px;
      display: grid;
      gap: 8px;
      background: #f9fafb;
    }
    #designDocJson {
      min-height: 130px;
      max-height: 260px;
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
    .ai-builder {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #f9fafb;
      display: grid;
      gap: 10px;
    }
    .ai-builder textarea {
      min-height: 90px;
      font-family: var(--sans);
      font-size: 13px;
    }
    .ai-meta-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }
    .ai-meta-tile {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 8px;
      display: grid;
      gap: 3px;
      min-width: 0;
    }
    .ai-meta-tile span {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 700;
    }
    .ai-meta-tile strong {
      overflow-wrap: anywhere;
      font-size: 13px;
    }
    .ai-variable-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .ai-variable-chip {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #fff;
      color: var(--text);
      padding: 3px 8px;
      font-size: 12px;
      font-weight: 650;
    }
    .ai-variable-chip.native {
      color: var(--muted);
    }
    .ai-sample-json {
      min-height: 72px;
      max-height: 170px;
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
    .template-item.selected {
      border-color: var(--blue);
      background: #eff6ff;
      box-shadow: inset 3px 0 0 var(--blue);
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
      grid-template-columns: minmax(0, 1fr) auto auto;
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
    .insert-target {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .insert-target select { width: auto; }
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
        <div class="actions">
          <button class="secondary" id="seedSamples">Seed Samples</button>
          <button class="secondary" id="refreshTemplates">Refresh</button>
        </div>
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
        <div class="ai-builder">
          <strong>AI Builder</strong>
          <label>Brief
            <textarea id="aiBrief" placeholder="Describe the template you want to generate. Include audience, offer, tone, required sections, and any variables you want to use."></textarea>
          </label>
          <div class="actions">
            <button type="button" id="aiDraft">Generate Draft</button>
            <button class="secondary" type="button" id="aiEdit">Modify Current</button>
            <button class="secondary" type="button" id="aiPreviewDraft" disabled>Preview Draft</button>
            <button class="secondary" type="button" id="aiApplyDraft" disabled>Apply Draft</button>
            <button class="secondary" type="button" id="aiUseSampleVariables" disabled>Use Sample JSON</button>
          </div>
          <div class="ai-meta-grid" id="aiDraftMeta">
            <div class="ai-meta-tile"><span>Provider</span><strong>-</strong></div>
            <div class="ai-meta-tile"><span>Model</span><strong>-</strong></div>
            <div class="ai-meta-tile"><span>Validation</span><strong>-</strong></div>
            <div class="ai-meta-tile"><span>Variables</span><strong>-</strong></div>
          </div>
          <div class="ai-variable-list" id="aiDraftVariables"></div>
          <pre class="ai-sample-json" id="aiSampleJson">Generate a draft to see sample variables.</pre>
        </div>
        <div class="editor-tabs" role="tablist" aria-label="Template editor modes">
          <button class="secondary active" type="button" data-editor-tab="source">Source</button>
          <button class="secondary" type="button" data-editor-tab="visual">WYSIWYG</button>
          <button class="secondary" type="button" data-editor-tab="blocks">Design Blocks</button>
        </div>
        <div class="editor-panel active" id="sourcePanel">
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
        </div>
        <div class="editor-panel" id="visualPanel">
          <div class="wysiwyg-shell">
            <div class="toolbar wysiwyg-toolbar">
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
            <div class="wysiwyg-blocks">
              <button type="button" data-block="shell">Email shell</button>
              <button type="button" data-block="hero">Hero</button>
              <button type="button" data-block="card">Card</button>
              <button type="button" data-block="callout">Callout</button>
              <button type="button" data-block="summary">Summary</button>
              <button type="button" data-block="footer">Footer</button>
            </div>
            <iframe id="visualEditor"></iframe>
          </div>
        </div>
        <div class="editor-panel" id="blocksPanel">
          <div class="design-builder">
            <div class="design-palette">
              <button type="button" data-design-add="heading">Heading</button>
              <button type="button" data-design-add="paragraph">Paragraph</button>
              <button type="button" data-design-add="button">Button</button>
              <button type="button" data-design-add="list">List</button>
              <button type="button" data-design-add="image">Image</button>
              <button type="button" data-design-add="divider">Divider</button>
              <button type="button" data-design-add="spacer">Spacer</button>
              <button type="button" data-design-add="trust_signal">Trust Text</button>
              <button type="button" data-design-add="html">HTML</button>
            </div>
            <div class="design-actions">
              <button class="secondary" type="button" id="sourceToBlocks">Source -> Blocks</button>
              <button class="secondary" type="button" id="blocksToSource">Blocks -> Source</button>
              <button class="secondary" type="button" id="exportBlocks">Export JSON</button>
              <button class="secondary" type="button" id="importBlocks">Import JSON</button>
            </div>
            <div class="design-block-list" id="designBlockList"></div>
            <div class="design-doc-json">
              <label>Block Document JSON
                <textarea id="designDocJson" spellcheck="false"></textarea>
              </label>
            </div>
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
  "recommendations": ["Map data", "Build audience", "Launch campaign"],
  "cta_url": "https://example.com/dashboard"
}</textarea>
        </label>
        <div class="variable-panel">
          <div class="actions">
            <strong>Detected Variables</strong>
            <label class="insert-target">Insert into
              <select id="insertTarget">
                <option value="htmlBody">HTML</option>
                <option value="subject">Subject</option>
                <option value="textBody">Text</option>
              </select>
            </label>
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
    const state = {
      templateId: "",
      visualReady: false,
      sampleVariables: null,
      variableTimer: null,
      inspectingVariables: false,
      editorTab: "source",
      designDoc: { blocks: [] },
      aiDraft: null,
    };

    function value(id) { return document.getElementById(id).value; }

    function log(data) {
      document.getElementById("result").textContent = JSON.stringify(data, null, 2);
    }

    function variables(fallbackToEmpty = false) {
      try {
        return JSON.parse(value("variablesJson") || "{}");
      } catch (error) {
        if (fallbackToEmpty) return {};
        throw error;
      }
    }

    async function renderVariablesContext(fallbackToEmpty = false) {
      if (!state.sampleVariables) {
        await inspectVariables({ silent: true });
      }
      return { ...(state.sampleVariables || {}), ...variables(fallbackToEmpty) };
    }

    function insertIntoTarget(snippet) {
      const target = document.getElementById(value("insertTarget"));
      if (!target) return;
      target.focus();
      if (typeof target.setRangeText === "function") {
        const start = target.selectionStart ?? target.value.length;
        const end = target.selectionEnd ?? target.value.length;
        target.setRangeText(snippet, start, end, "end");
      } else {
        target.value = `${target.value}${snippet}`;
      }
      if (target.id === "htmlBody") loadVisualFromSource();
      scheduleVariableRefresh();
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
        const insert = document.createElement("button");
        name.textContent = item.name;
        sources.textContent = `sources: ${(item.sources || []).join(", ") || "unknown"}`;
        kind.className = "variable-kind";
        kind.textContent = item.native ? "native" : "user";
        insert.className = "secondary";
        insert.type = "button";
        insert.textContent = "Insert";
        insert.addEventListener("click", () => insertIntoTarget(`{{ ${item.name} }}`));
        copy.append(name, sources);
        row.append(copy, kind, insert);
        list.appendChild(row);
      });
    }

    function detectedVariableNames() {
      const rows = document.querySelectorAll("#variableList .variable-row strong");
      const values = Array.from(rows).map((row) => row.textContent).filter(Boolean);
      if (values.length) return values;
      const source = `${value("subject")}\n${value("htmlBody")}\n${value("textBody")}`;
      return Array.from(source.matchAll(/{{\s*([a-zA-Z_][\w.]*)/g))
        .map((match) => match[1].split(".")[0])
        .filter((name, index, list) => list.indexOf(name) === index);
    }

    function renderAiDraft(data) {
      state.aiDraft = data;
      document.getElementById("aiPreviewDraft").disabled = !data;
      document.getElementById("aiApplyDraft").disabled = !data;
      document.getElementById("aiUseSampleVariables").disabled = !data?.sample_variables;
      const variables = data?.template_variables?.variables || [];
      const nativeVariables = data?.template_variables?.native_variables || [];
      document.getElementById("aiDraftMeta").innerHTML = `
        <div class="ai-meta-tile"><span>Provider</span><strong>${data?.provider || "-"}</strong></div>
        <div class="ai-meta-tile"><span>Model</span><strong>${data?.model || "-"}</strong></div>
        <div class="ai-meta-tile"><span>Validation</span><strong>${data?.validation?.ok ? "OK" : "Needs review"}</strong></div>
        <div class="ai-meta-tile"><span>Variables</span><strong>${variables.length} user / ${nativeVariables.length} native</strong></div>
      `;
      const list = document.getElementById("aiDraftVariables");
      list.textContent = "";
      [...variables, ...nativeVariables].forEach((item) => {
        const chip = document.createElement("span");
        chip.className = `ai-variable-chip${item.native ? " native" : ""}`;
        chip.textContent = item.native ? `${item.name} native` : item.name;
        list.appendChild(chip);
      });
      if (!list.childNodes.length) {
        const empty = document.createElement("span");
        empty.className = "muted";
        empty.textContent = "No variables detected in draft.";
        list.appendChild(empty);
      }
      document.getElementById("aiSampleJson").textContent = JSON.stringify(
        data?.sample_variables || {},
        null,
        2,
      );
    }

    function applyAiSampleVariables() {
      if (!state.aiDraft?.sample_variables) return;
      state.sampleVariables = state.aiDraft.sample_variables;
      document.getElementById("variablesJson").value = JSON.stringify(
        state.aiDraft.sample_variables,
        null,
        2,
      );
      log({ applied_ai_sample_variables: Object.keys(state.aiDraft.sample_variables) });
    }

    async function draftTemplateWithAi() {
      const brief = value("aiBrief").trim();
      if (!brief) {
        log({ error: "AI brief is required." });
        return;
      }
      await inspectVariables({ silent: true }).catch(() => {});
      const data = await request("/api/v1/ai/templates/draft", {
        method: "POST",
        body: JSON.stringify({
          brief,
          brand: {
            name: value("templateName") || "Email Engine",
            primary_color: value("cssBrandColor") || "#2563eb",
            tone: "clear, useful, and production ready",
          },
          required_variables: detectedVariableNames(),
        }),
      });
      renderAiDraft(data);
      log({ ai_draft: data.subject, provider: data.provider, model: data.model, validation: data.validation });
    }

    async function editTemplateWithAi() {
      const instruction = value("aiBrief").trim();
      if (!instruction) {
        log({ error: "AI edit instruction is required." });
        return;
      }
      await inspectVariables({ silent: true }).catch(() => {});
      const data = await request("/api/v1/ai/templates/edit", {
        method: "POST",
        body: JSON.stringify({
          instruction,
          current_subject: value("subject"),
          current_html: state.editorTab === "blocks" ? designDocumentTemplateSource() : value("htmlBody"),
          current_css: value("cssBody") || null,
          current_text: value("textBody") || null,
          brand: {
            name: value("templateName") || "Email Engine",
            primary_color: value("cssBrandColor") || "#2563eb",
            tone: "clear, useful, and production ready",
          },
          required_variables: detectedVariableNames(),
          sample_variables: variables(true),
        }),
      });
      renderAiDraft(data);
      applyAiSampleVariables();
      await previewAiDraft();
      log({ ai_edit: data.subject, provider: data.provider, model: data.model, validation: data.validation });
    }

    async function previewAiDraft() {
      if (!state.aiDraft) return;
      const data = await request("/api/v1/templates/preview", {
        method: "POST",
        body: JSON.stringify({
          name: value("templateName") || "ai-draft",
          subject: state.aiDraft.subject,
          html_body: state.aiDraft.html_body,
          css_body: state.aiDraft.css_body || null,
          text_body: state.aiDraft.text_body || null,
          variables: state.aiDraft.sample_variables || {},
        }),
      });
      document.getElementById("htmlPreview").srcdoc = data.ok ? data.html_body : "";
      log(data);
    }

    async function applyAiDraft() {
      if (!state.aiDraft) return;
      document.getElementById("subject").value = state.aiDraft.subject || "";
      document.getElementById("htmlBody").value = state.aiDraft.html_body || "";
      document.getElementById("cssBody").value = state.aiDraft.css_body || "";
      document.getElementById("textBody").value = state.aiDraft.text_body || "";
      applyAiSampleVariables();
      state.designDoc = { blocks: [] };
      renderDesignBlocks();
      loadVisualFromSource();
      await refreshVariablesAndPreview({ applySample: false, silent: true });
      log({ applied_ai_draft: state.aiDraft.subject });
    }

    function scheduleVariableRefresh() {
      window.clearTimeout(state.variableTimer);
      state.variableTimer = window.setTimeout(() => {
        inspectVariables({ silent: true }).catch((error) => {
          renderVariables({ errors: [error.message], variables: [], native_variables: [] });
        });
      }, 650);
    }

    function visualDocument() {
      return document.getElementById("visualEditor").contentDocument;
    }

    function hasComplexTemplateSource(html) {
      return /<table\b|{%\s*(?:for|if|elif|else|endif|endfor)\b/i.test(String(html || ""));
    }

    function htmlDocument(html, css) {
      const bodyHtml = extractBodyHtml(html || "");
      const editable = hasComplexTemplateSource(bodyHtml) ? "false" : "true";
      const warning = editable === "false"
        ? '<div style="padding:8px 10px;margin-bottom:10px;border:1px solid #bfdbfe;background:#eff6ff;color:#1d4ed8;font:12px Arial,sans-serif;">Complex Jinja/table template: edit in Source or Design Blocks to preserve preview rendering.</div>'
        : "";
      return `<!doctype html><html><head><style>
        body { padding: 14px; min-height: 320px; outline: none; }
        ${css || ""}
      </style></head><body contenteditable="${editable}">${warning}${bodyHtml}</body></html>`;
    }

    function extractBodyHtml(html) {
      if (!html) return "";
      const match = String(html).match(/<body[^>]*>([\s\S]*?)<\/body>/i);
      return match ? match[1] : html;
    }

    function loadVisualFromSource() {
      const frame = document.getElementById("visualEditor");
      frame.srcdoc = htmlDocument(value("htmlBody"), value("cssBody"));
    }

    function syncSourceFromVisual() {
      if (hasComplexTemplateSource(value("htmlBody"))) {
        return;
      }
      const doc = visualDocument();
      if (!doc || !doc.body) return;
      document.getElementById("htmlBody").value = doc.body.innerHTML.trim();
    }

    function setEditorTab(tab) {
      if (state.editorTab === "visual" && tab !== "visual") {
        syncSourceFromVisual();
      }
      state.editorTab = tab;
      document.querySelectorAll("[data-editor-tab]").forEach((button) => {
        button.classList.toggle("active", button.dataset.editorTab === tab);
      });
      document.getElementById("sourcePanel").classList.toggle("active", tab === "source");
      document.getElementById("visualPanel").classList.toggle("active", tab === "visual");
      document.getElementById("blocksPanel").classList.toggle("active", tab === "blocks");
      if (tab === "visual") loadVisualFromSource();
      if (tab === "blocks" && state.designDoc.blocks.length === 0) {
        sourceToDesignBlocks();
      }
    }

    function runCommand(command, value = null) {
      const doc = visualDocument();
      if (!doc) return;
      doc.body.focus();
      doc.execCommand(command, false, value);
      syncSourceFromVisual();
    }

    async function refreshVariablesAndPreview({ applySample = false, silent = false } = {}) {
      await inspectVariables({ silent: true, applySample });
      await previewTemplate({ silent });
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

    function newBlock(type) {
      const id = `b_${Math.random().toString(36).slice(2, 10)}`;
      if (type === "heading") return { id, type, text: "Main headline", level: 1, align: "left" };
      if (type === "paragraph") {
        return { id, type, text: "Add body copy with {{ first_name }}.", align: "left", color: "" };
      }
      if (type === "button") {
        return {
          id,
          type,
          text: "Call to Action",
          href: "{{ cta_url }}",
          bg: "#2563eb",
          color: "#ffffff",
          radius: 6,
          padding_y: 11,
          padding_x: 16,
        };
      }
      if (type === "list") return { id, type, ordered: false, items: ["First point", "Second point"] };
      if (type === "image") return { id, type, src: "https://example.com/image.png", alt: "Image", href: "", width: 600 };
      if (type === "divider") return { id, type, color: "#d8dee6" };
      if (type === "spacer") return { id, type, height: 24 };
      if (type === "trust_signal") return { id, type, text: "Trusted by teams building better email workflows." };
      return { id, type: "html", code: "<p>Custom HTML</p>" };
    }

    function renderDesignBlocks() {
      const list = document.getElementById("designBlockList");
      list.textContent = "";
      if (!state.designDoc.blocks.length) {
        const empty = document.createElement("p");
        empty.className = "secondary-text";
        empty.textContent = "No blocks yet. Add a block or convert from Source.";
        list.appendChild(empty);
        syncDesignDocJson();
        return;
      }
      state.designDoc.blocks.forEach((block, index) => {
        const row = document.createElement("div");
        row.className = "design-block-row";
        const head = document.createElement("div");
        head.className = "design-block-head";
        const title = document.createElement("strong");
        title.textContent = block.type;
        const controls = document.createElement("div");
        controls.className = "actions";
        const moveUp = document.createElement("button");
        moveUp.className = "secondary";
        moveUp.type = "button";
        moveUp.textContent = "Up";
        moveUp.disabled = index === 0;
        moveUp.addEventListener("click", () => {
          const previous = state.designDoc.blocks[index - 1];
          state.designDoc.blocks[index - 1] = block;
          state.designDoc.blocks[index] = previous;
          renderDesignBlocks();
          scheduleVariableRefresh();
        });
        const moveDown = document.createElement("button");
        moveDown.className = "secondary";
        moveDown.type = "button";
        moveDown.textContent = "Down";
        moveDown.disabled = index === state.designDoc.blocks.length - 1;
        moveDown.addEventListener("click", () => {
          const next = state.designDoc.blocks[index + 1];
          state.designDoc.blocks[index + 1] = block;
          state.designDoc.blocks[index] = next;
          renderDesignBlocks();
          scheduleVariableRefresh();
        });
        const duplicate = document.createElement("button");
        duplicate.className = "secondary";
        duplicate.type = "button";
        duplicate.textContent = "Duplicate";
        duplicate.addEventListener("click", () => {
          state.designDoc.blocks.splice(index + 1, 0, cloneBlock(block));
          renderDesignBlocks();
          scheduleVariableRefresh();
        });
        const remove = document.createElement("button");
        remove.className = "secondary";
        remove.type = "button";
        remove.textContent = "Remove";
        remove.addEventListener("click", () => {
          state.designDoc.blocks.splice(index, 1);
          renderDesignBlocks();
          scheduleVariableRefresh();
        });
        controls.append(moveUp, moveDown, duplicate, remove);
        head.append(title, controls);
        row.appendChild(head);
        row.appendChild(blockEditor(block, index));
        list.appendChild(row);
      });
      syncDesignDocJson();
    }

    function cloneBlock(block) {
      const next = JSON.parse(JSON.stringify(block));
      next.id = `b_${Math.random().toString(36).slice(2, 10)}`;
      return next;
    }

    function blockEditor(block, index) {
      const container = document.createElement("div");
      container.className = "design-block-grid";
      const field = (label, key, type = "text") => {
        const wrapper = document.createElement("label");
        wrapper.textContent = label;
        const input = type === "textarea" ? document.createElement("textarea") : document.createElement("input");
        if (type !== "textarea") input.type = type;
        input.value = Array.isArray(block[key]) ? block[key].join("\n") : (block[key] ?? "");
        input.addEventListener("input", () => {
          block[key] = key === "items"
            ? input.value.split("\n").map((item) => item.trim()).filter(Boolean)
            : input.value;
          state.designDoc.blocks[index] = block;
          syncDesignDocJson();
          scheduleVariableRefresh();
        });
        wrapper.appendChild(input);
        return wrapper;
      };
      if (block.type === "heading") {
        container.append(field("Text", "text"), field("Level", "level", "number"), field("Align", "align"));
      } else if (block.type === "paragraph") {
        const mode = document.createElement("button");
        mode.className = "secondary";
        mode.type = "button";
        mode.textContent = block.html != null ? "Use Text Mode" : "Use Inline HTML";
        mode.addEventListener("click", () => {
          if (block.html != null) {
            block.text = stripHtml(block.html);
            delete block.html;
          } else {
            block.html = block.text || "";
            delete block.text;
          }
          state.designDoc.blocks[index] = block;
          renderDesignBlocks();
          scheduleVariableRefresh();
        });
        container.append(
          field(block.html != null ? "Inline HTML" : "Text", block.html != null ? "html" : "text", "textarea"),
          field("Align", "align"),
          field("Color", "color", "color"),
          mode,
        );
      } else if (block.type === "button") {
        container.append(
          field("Text", "text"),
          field("URL", "href"),
          field("Background", "bg", "color"),
          field("Text color", "color", "color"),
          field("Radius", "radius", "number"),
          field("Padding Y", "padding_y", "number"),
          field("Padding X", "padding_x", "number"),
        );
      } else if (block.type === "list") {
        const ordered = document.createElement("label");
        ordered.textContent = "List type";
        const select = document.createElement("select");
        select.innerHTML = '<option value="false">Bulleted</option><option value="true">Numbered</option>';
        select.value = block.ordered ? "true" : "false";
        select.addEventListener("change", () => {
          block.ordered = select.value === "true";
          state.designDoc.blocks[index] = block;
          syncDesignDocJson();
          scheduleVariableRefresh();
        });
        ordered.appendChild(select);
        container.append(ordered, field("Items", "items", "textarea"));
      } else if (block.type === "image") {
        container.append(field("Image URL", "src"), field("Alt text", "alt"), field("Link URL", "href"), field("Width", "width", "number"));
      } else if (block.type === "divider") {
        container.append(field("Color", "color", "color"));
      } else if (block.type === "spacer") {
        container.append(field("Height", "height", "number"));
      } else if (block.type === "trust_signal") {
        container.append(field("Text", "text", "textarea"));
      } else {
        container.append(field("HTML", "code", "textarea"));
      }
      return container;
    }

    function sourceToDesignBlocks() {
      state.designDoc = { blocks: htmlToDesignBlocks(value("htmlBody")) };
      renderDesignBlocks();
    }

    function syncDesignDocJson() {
      const field = document.getElementById("designDocJson");
      if (!field) return;
      field.value = JSON.stringify(state.designDoc, null, 2);
    }

    function applyDesignDocJson() {
      const parsed = JSON.parse(value("designDocJson") || "{}");
      if (!Array.isArray(parsed.blocks)) {
        throw new Error("Block document JSON must contain a blocks array");
      }
      state.designDoc = {
        ...parsed,
        blocks: parsed.blocks.map((block) => ({
          ...block,
          id: block.id || `b_${Math.random().toString(36).slice(2, 10)}`,
        })),
      };
      renderDesignBlocks();
      scheduleVariableRefresh();
    }

    function stripHtml(html) {
      const parsed = new DOMParser().parseFromString(html || "", "text/html");
      return parsed.body.textContent || "";
    }

    function htmlToDesignBlocks(html) {
      const blocks = [];
      splitHtmlForDesignBlocks(html || "").forEach((segment) => {
        if (segment.type === "raw") {
          const code = segment.html.trim();
          if (code) blocks.push({ id: `b_${blocks.length}`, type: "html", code });
          return;
        }
        blocks.push(...nodesToDesignBlocks(segment.html, blocks.length));
      });
      return blocks.length ? blocks : [newBlock("html")];
    }

    function splitHtmlForDesignBlocks(html) {
      const segments = [];
      const complexPattern = /<table\b[\s\S]*?<\/table>|{%\s*(?:for|if|elif|else|endif|endfor)[\s\S]*?%}/gi;
      let cursor = 0;
      let match;
      while ((match = complexPattern.exec(html)) !== null) {
        if (match.index > cursor) {
          segments.push({ type: "html", html: html.slice(cursor, match.index) });
        }
        segments.push({ type: "raw", html: match[0] });
        cursor = match.index + match[0].length;
      }
      if (cursor < html.length) segments.push({ type: "html", html: html.slice(cursor) });
      return segments.length ? segments : [{ type: "html", html }];
    }

    function nodesToDesignBlocks(html, startIndex = 0) {
      const parsed = new DOMParser().parseFromString(html || "", "text/html");
      const blocks = [];
      let children = Array.from(parsed.body.children);
      children = unwrapDesignContainers(children);
      children.forEach((node) => {
        const tag = node.tagName.toLowerCase();
        if (/^h[1-3]$/.test(tag)) {
          blocks.push({
            id: `b_${startIndex + blocks.length}`,
            type: "heading",
            level: Number(tag.slice(1)),
            align: textAlign(node),
            text: node.textContent.trim(),
          });
        } else if (tag === "p") {
          const link = node.querySelector("a");
          if (link && /\b(button|btn|cta)\b/i.test(link.className || "")) {
            const style = window.getComputedStyle(link);
            blocks.push({
              id: `b_${startIndex + blocks.length}`,
              type: "button",
              text: link.textContent.trim(),
              href: link.getAttribute("href") || "",
              bg: rgbToHex(style.backgroundColor) || "#2563eb",
              color: rgbToHex(style.color) || "#ffffff",
              radius: pxNumber(style.borderRadius, 6),
              padding_y: parsePadding(style.padding).y,
              padding_x: parsePadding(style.padding).x,
            });
          } else if (/\b(secondary-text|muted|trust)\b/i.test(node.className || "") && node.textContent.trim()) {
            blocks.push({ id: `b_${startIndex + blocks.length}`, type: "trust_signal", text: node.textContent.trim() });
          } else if (node.children.length === 0) {
            blocks.push({
              id: `b_${startIndex + blocks.length}`,
              type: "paragraph",
              text: node.textContent.trim(),
              align: textAlign(node),
              color: rgbToHex(node.style?.color) || "",
            });
          } else {
            blocks.push({
              id: `b_${startIndex + blocks.length}`,
              type: "paragraph",
              html: node.innerHTML.trim(),
              align: textAlign(node),
              color: rgbToHex(node.style?.color) || "",
            });
          }
        } else if (tag === "ul" || tag === "ol") {
          const items = Array.from(node.children).filter((li) => li.tagName.toLowerCase() === "li").map((li) => li.textContent.trim()).filter(Boolean);
          blocks.push({ id: `b_${startIndex + blocks.length}`, type: "list", ordered: tag === "ol", items });
        } else if (tag === "img") {
          blocks.push({ id: `b_${startIndex + blocks.length}`, type: "image", src: node.getAttribute("src") || "", alt: node.getAttribute("alt") || "", href: "", width: Number(node.getAttribute("width") || 600) });
        } else if (tag === "a" && node.children.length === 1 && node.children[0].tagName.toLowerCase() === "img") {
          const img = node.children[0];
          blocks.push({
            id: `b_${startIndex + blocks.length}`,
            type: "image",
            src: img.getAttribute("src") || "",
            alt: img.getAttribute("alt") || "",
            href: node.getAttribute("href") || "",
            width: Number(img.getAttribute("width") || 600),
          });
        } else if (tag === "hr") {
          blocks.push({ id: `b_${startIndex + blocks.length}`, type: "divider", color: "#d8dee6" });
        } else if (tag === "div" && isSpacer(node)) {
          blocks.push({ id: `b_${startIndex + blocks.length}`, type: "spacer", height: spacerHeight(node) });
        } else {
          blocks.push({ id: `b_${startIndex + blocks.length}`, type: "html", code: node.outerHTML });
        }
      });
      const looseText = Array.from(parsed.body.childNodes)
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .map((node) => node.textContent.trim())
        .filter(Boolean)
        .join("\n");
      if (looseText) blocks.push({ id: `b_${startIndex + blocks.length}`, type: "html", code: looseText });
      return blocks;
    }

    function unwrapDesignContainers(children) {
      let nodes = children;
      while (nodes.length === 1 && nodes[0].tagName.toLowerCase() === "div") {
        const className = nodes[0].getAttribute("class") || "";
        if (!/\b(email-document|email-shell|email-container|content-card)\b/.test(className)) break;
        nodes = Array.from(nodes[0].children);
      }
      return nodes;
    }

    function textAlign(node) {
      const align = (node.style && node.style.textAlign) || node.getAttribute("align") || "left";
      return ["left", "center", "right"].includes(align) ? align : "left";
    }

    function rgbToHex(value) {
      const match = String(value || "").match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([0-9.]+))?/);
      if (!match) return "";
      if (match[4] === "0") return "";
      return `#${[match[1], match[2], match[3]].map((part) => Number(part).toString(16).padStart(2, "0")).join("")}`;
    }

    function isSpacer(node) {
      const height = spacerHeight(node);
      return height > 0 && (!node.textContent.trim() || node.innerHTML.trim() === "&nbsp;");
    }

    function spacerHeight(node) {
      const source = node.style?.height || node.style?.lineHeight || "";
      const parsed = Number(String(source).replace("px", ""));
      return Number.isFinite(parsed) && parsed > 0 ? parsed : 24;
    }

    function pxNumber(value, fallback) {
      const parsed = Number(String(value || "").replace("px", ""));
      return Number.isFinite(parsed) ? parsed : fallback;
    }

    function parsePadding(value) {
      const parts = String(value || "")
        .split(/\s+/)
        .map((part) => pxNumber(part, 0))
        .filter((part) => part > 0);
      if (parts.length >= 2) return { y: parts[0], x: parts[1] };
      if (parts.length === 1) return { y: parts[0], x: parts[0] };
      return { y: 11, x: 16 };
    }

    function designDocumentTemplateSource() {
      return state.designDoc.blocks.map((block) => {
        if (block.type === "heading") return `<h${block.level || 1} style="text-align:${block.align || "left"};">${block.text || ""}</h${block.level || 1}>`;
        if (block.type === "paragraph") {
          const style = `text-align:${block.align || "left"};${block.color ? `color:${block.color};` : ""}`;
          return `<p style="${style}">${block.html != null ? block.html : (block.text || "")}</p>`;
        }
        if (block.type === "button") {
          return `<p><a class="button" href="${block.href || ""}" style="display:inline-block;background:${block.bg || "#2563eb"};color:${block.color || "#ffffff"};padding:${block.padding_y || 11}px ${block.padding_x || 16}px;text-decoration:none;border-radius:${block.radius || 6}px;font-weight:700;">${block.text || ""}</a></p>`;
        }
        if (block.type === "list") {
          const tag = block.ordered ? "ol" : "ul";
          const items = (block.items || []).map((item) => `<li>${item}</li>`).join("");
          return `<${tag}>${items}</${tag}>`;
        }
        if (block.type === "image") {
          const image = `<img src="${block.src || ""}" alt="${block.alt || ""}" width="${block.width || 600}" />`;
          return block.href ? `<a href="${block.href}">${image}</a>` : image;
        }
        if (block.type === "divider") return "<hr />";
        if (block.type === "spacer") return `<div style="height:${block.height || 24}px;line-height:${block.height || 24}px;font-size:0;">&nbsp;</div>`;
        if (block.type === "trust_signal") return `<p class="secondary-text" style="text-align:center;">${block.text || ""}</p>`;
        return block.code || "";
      }).join("\n");
    }

    async function renderDesignDocumentToSource({ silent = false } = {}) {
      const source = designDocumentTemplateSource();
      document.getElementById("htmlBody").value = source;
      loadVisualFromSource();
      if (!silent) log({ design_blocks_synced: state.designDoc.blocks.length });
      return source;
    }

    async function previewDesignDocument({ silent = false } = {}) {
      const data = await request("/api/v1/templates/document/render", {
        method: "POST",
        body: JSON.stringify(await documentRequestPayload(true)),
      });
      document.getElementById("htmlPreview").srcdoc = data.html_body || data.html || "";
      if (!silent) log({ design_blocks_rendered: state.designDoc.blocks.length });
      return data;
    }

    function payload() {
      if (state.editorTab === "visual") syncSourceFromVisual();
      return {
        name: value("templateName"),
        subject: value("subject"),
        html_body: value("htmlBody"),
        css_body: value("cssBody") || null,
        text_body: value("textBody") || null,
        document_json: state.designDoc.blocks.length ? state.designDoc : {},
      };
    }

    function variablePayload() {
      const body = payload();
      if (state.editorTab === "blocks") {
        body.html_body = designDocumentTemplateSource();
      }
      return body;
    }

    async function documentRequestPayload(fallbackToEmpty = false) {
      return {
        subject: value("subject"),
        document_json: state.designDoc,
        css_body: value("cssBody") || null,
        text_body: value("textBody") || null,
        variables: await renderVariablesContext(fallbackToEmpty),
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
        item.className = `template-item${state.templateId === template.id ? " selected" : ""}`;
        item.dataset.id = template.id;
        const name = document.createTextNode(template.name);
        const subject = document.createElement("small");
        subject.textContent = template.subject;
        item.append(name, subject);
        item.addEventListener("click", () => {
          selectTemplate(template).catch((error) => log({ selected: template.id, error: error.message }));
        });
        list.appendChild(item);
      });
    }

    function markSelectedTemplate(id) {
      document.querySelectorAll("#templateList .template-item").forEach((item) => {
        item.classList.toggle("selected", item.dataset.id === id);
      });
    }

    async function templateForEditor(template) {
      if (template.html_body != null) return template;
      return request(`/api/v1/templates/${template.id}`);
    }

    async function selectTemplate(template) {
      const fullTemplate = await templateForEditor(template);
      state.templateId = fullTemplate.id;
      markSelectedTemplate(fullTemplate.id);
      state.sampleVariables = null;
      document.getElementById("templateName").value = fullTemplate.name;
      document.getElementById("subject").value = fullTemplate.subject;
      document.getElementById("htmlBody").value = fullTemplate.html_body || "";
      document.getElementById("cssBody").value = fullTemplate.css_body || "";
      document.getElementById("textBody").value = fullTemplate.text_body || "";
      state.designDoc = await designDocForTemplate(fullTemplate);
      renderDesignBlocks();
      loadVisualFromSource();
      log({ selected: fullTemplate.id });
      refreshVariablesAndPreview({ applySample: true, silent: true })
        .then(() => log({ selected: fullTemplate.id, preview: "updated" }))
        .catch((error) => log({ selected: fullTemplate.id, error: error.message }));
    }

    async function designDocForTemplate(template) {
      try {
        const data = await request(`/api/v1/templates/${template.id}/document`);
        if (data.document_json?.blocks?.length) return data.document_json;
      } catch (error) {
        log({ selected: template.id, document_json_error: error.message });
      }
      if (template.document_json?.blocks?.length) return template.document_json;
      return { blocks: htmlToDesignBlocks(template.html_body || "") };
    }

    async function validateTemplate() {
      if (state.editorTab === "blocks") {
        const data = await request("/api/v1/templates/document/validate", {
          method: "POST",
          body: JSON.stringify(await documentRequestPayload()),
        });
        log(data);
        return;
      }
      const renderVariables = await renderVariablesContext();
      const data = await request("/api/v1/templates/validate", {
        method: "POST",
        body: JSON.stringify({ ...payload(), variables: renderVariables }),
      });
      log(data);
    }

    async function inspectVariables(options = {}) {
      if (state.inspectingVariables) return;
      state.inspectingVariables = true;
      try {
        const path = state.editorTab === "blocks"
          ? "/api/v1/templates/document/variables"
          : "/api/v1/templates/variables";
        const body = state.editorTab === "blocks"
          ? await documentRequestPayload(true)
          : { ...variablePayload(), variables: variables(true) };
        const data = await request(path, { method: "POST", body: JSON.stringify(body) });
        renderVariables(data);
        if (options.applySample) {
          document.getElementById("variablesJson").value = JSON.stringify(
            data.sample_variables || {},
            null,
            2,
          );
        }
        if (!options.silent) log(data);
      } finally {
        state.inspectingVariables = false;
      }
    }

    async function lintTemplate() {
      if (state.editorTab === "blocks") {
        await renderDesignDocumentToSource({ silent: true });
      }
      const data = await request("/api/v1/templates/lint", {
        method: "POST",
        body: JSON.stringify({ ...payload(), variables: variables() }),
      });
      log(data);
    }

    async function previewTemplate(options = {}) {
      if (state.editorTab === "blocks") {
        const data = await previewDesignDocument({ silent: options.silent });
        if (!options.silent) log(data);
        return;
      }
      const renderVariables = await renderVariablesContext();
      const data = await request("/api/v1/templates/preview", {
        method: "POST",
        body: JSON.stringify({ ...payload(), variables: renderVariables }),
      });
      if (!options.silent) log(data);
      document.getElementById("htmlPreview").srcdoc = data.ok ? data.html_body : "";
    }

    async function saveTemplate() {
      if (state.editorTab === "blocks") {
        await renderDesignDocumentToSource({ silent: true });
      }
      const body = payload();
      const path = state.templateId ? `/api/v1/templates/${state.templateId}` : "/api/v1/templates";
      const method = state.templateId ? "PATCH" : "POST";
      const saved = await request(path, { method, body: JSON.stringify(body) });
      state.templateId = saved.id;
      log(saved);
      await loadTemplates();
      scheduleVariableRefresh();
    }

    async function seedSamples() {
      const templates = await request("/api/v1/templates/samples", { method: "POST" });
      log({ seeded_templates: templates.map((template) => template.name) });
      await loadTemplates();
    }

    document.getElementById("refreshTemplates").addEventListener("click", loadTemplates);
    document.getElementById("seedSamples").addEventListener("click", seedSamples);
    document.getElementById("inspectVariables").addEventListener("click", inspectVariables);
    document.getElementById("aiDraft").addEventListener("click", () => {
      draftTemplateWithAi().catch((error) => log({ error: error.message }));
    });
    document.getElementById("aiEdit").addEventListener("click", () => {
      editTemplateWithAi().catch((error) => log({ error: error.message }));
    });
    document.getElementById("aiPreviewDraft").addEventListener("click", () => {
      previewAiDraft().catch((error) => log({ error: error.message }));
    });
    document.getElementById("aiApplyDraft").addEventListener("click", () => {
      applyAiDraft().catch((error) => log({ error: error.message }));
    });
    document.getElementById("aiUseSampleVariables").addEventListener("click", applyAiSampleVariables);
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
    document.querySelectorAll("[data-design-add]").forEach((button) => {
      button.addEventListener("click", () => {
        state.designDoc.blocks.push(newBlock(button.dataset.designAdd));
        renderDesignBlocks();
        scheduleVariableRefresh();
      });
    });
    document.getElementById("sourceToBlocks").addEventListener("click", () => {
      sourceToDesignBlocks();
      scheduleVariableRefresh();
    });
    document.getElementById("blocksToSource").addEventListener("click", () => {
      renderDesignDocumentToSource().catch((error) => log({ error: error.message }));
    });
    document.getElementById("exportBlocks").addEventListener("click", () => {
      syncDesignDocJson();
      log({ exported_blocks: state.designDoc.blocks.length });
    });
    document.getElementById("importBlocks").addEventListener("click", () => {
      try {
        applyDesignDocJson();
        log({ imported_blocks: state.designDoc.blocks.length });
      } catch (error) {
        log({ error: error.message });
      }
    });
    document.querySelectorAll("[data-editor-tab]").forEach((button) => {
      button.addEventListener("click", () => setEditorTab(button.dataset.editorTab));
    });
    ["subject", "htmlBody", "cssBody", "textBody"].forEach((id) => {
      document.getElementById(id).addEventListener("input", scheduleVariableRefresh);
    });
    document.getElementById("htmlBody").addEventListener("blur", () => {
      loadVisualFromSource();
      scheduleVariableRefresh();
    });
    document.getElementById("cssBody").addEventListener("blur", () => {
      loadVisualFromSource();
      scheduleVariableRefresh();
    });
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
    document.querySelectorAll("[data-block]").forEach((button) => {
      button.addEventListener("click", () => {
        document.getElementById("emailBlock").value = button.dataset.block;
        runCommand("insertHTML", blockHtml());
      });
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
      doc.body.addEventListener("input", () => {
        syncSourceFromVisual();
        scheduleVariableRefresh();
      });
      doc.body.addEventListener("blur", () => {
        syncSourceFromVisual();
        scheduleVariableRefresh();
      });
      state.visualReady = true;
    });
    document.getElementById("newTemplate").addEventListener("click", () => {
      state.templateId = "";
      document.getElementById("templateName").value = `template-${Date.now()}`;
      state.designDoc = { blocks: [] };
      renderDesignBlocks();
      loadVisualFromSource();
      log({ mode: "new" });
      scheduleVariableRefresh();
    });
    document.getElementById("templateName").value = `template-${Date.now()}`;
    syncDesignDocJson();
    loadVisualFromSource();
    scheduleVariableRefresh();
    loadTemplates().catch((error) => log({ error: error.message }));
  </script>
</body>
</html>"""
