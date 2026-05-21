from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get('/tester', response_class=HTMLResponse, include_in_schema=False)
def api_test_console() -> str:
    return TEST_CONSOLE_HTML


TEST_CONSOLE_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Email Engine API Tester</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #5b6673;
      --line: #d8dee6;
      --blue: #2563eb;
      --green: #0f766e;
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
      line-height: 1.45;
    }
    header {
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 3;
    }
    h1 { font-size: 20px; margin: 0 0 4px; }
    p { margin: 0; color: var(--muted); }
    main {
      display: grid;
      grid-template-columns: minmax(360px, 520px) minmax(420px, 1fr);
      gap: 16px;
      padding: 16px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .section-head {
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }
    h2 { font-size: 15px; margin: 0; }
    .body { padding: 14px; display: grid; gap: 12px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
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
      min-height: 86px;
      font-family: var(--mono);
      font-size: 12px;
      resize: vertical;
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
    button.secondary {
      background: #fff;
      color: var(--blue);
    }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; }
    .state {
      display: grid;
      grid-template-columns: 120px minmax(0, 1fr);
      gap: 6px 10px;
      font-family: var(--mono);
      font-size: 12px;
      word-break: break-all;
    }
    .state span:nth-child(odd) { color: var(--muted); }
    .ok { color: var(--green); }
    .err { color: var(--red); }
    pre {
      margin: 0;
      min-height: calc(100vh - 174px);
      max-height: calc(100vh - 174px);
      overflow: auto;
      padding: 14px;
      background: #0f172a;
      color: #e5edf8;
      font-family: var(--mono);
      font-size: 12px;
      white-space: pre-wrap;
    }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      pre { min-height: 360px; max-height: 520px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Email Engine API Tester</h1>
    <p>Manual same-origin test console for the deployed FastAPI endpoints.</p>
    <div class="actions" style="margin-top:10px">
      <button class="secondary" onclick="location.href='/admin'">Admin</button>
      <button class="secondary" onclick="location.href='/tester'">Tester</button>
      <button class="secondary" onclick="location.href='/template-editor'">Template Editor</button>
      <button class="secondary" onclick="location.href='/admin/entities'">Entity Workbench</button>
      <button class="secondary" onclick="location.href='/admin/audience-import'">
        Audience Import
      </button>
      <button class="secondary" onclick="location.href='/admin/audiences'">Audience Builder</button>
      <button class="secondary" onclick="location.href='/admin/campaigns'">Campaign Manager</button>
      <button class="secondary" onclick="location.href='/docs'">Docs</button>
    </div>
  </header>
  <main>
    <div class="body" style="padding:0">
      <section>
        <div class="section-head">
          <h2>Workflow</h2>
          <button id="runAll">Run All</button>
        </div>
        <div class="body">
          <div class="grid">
            <label>Contact email
              <input id="contactEmail" />
            </label>
            <label>First name
              <input id="firstName" value="Smoke" />
            </label>
          </div>
          <label>Template HTML
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
</ul>
<p>Custom note: {{ note }}</p></textarea>
          </label>
          <label>Email data JSON
            <textarea id="variablesJson">{
  "first_name": "Smoke",
  "plan": "trial",
  "note": "Sent from the API tester",
  "recommendations": ["Map data", "Build audience", "Launch campaign"]
}</textarea>
          </label>
          <div class="actions">
            <button class="secondary" data-action="health">Health</button>
            <button class="secondary" data-action="ready">Ready</button>
            <button class="secondary" data-action="validateTemplate">Validate Template</button>
            <button class="secondary" data-action="previewTemplate">Preview Template</button>
            <button class="secondary" data-action="createTemplate">Create Template</button>
            <button class="secondary" data-action="upsertContact">Upsert Contact</button>
            <button class="secondary" data-action="createCampaign">Create Campaign</button>
            <button class="secondary" data-action="launchCampaign">Launch Campaign</button>
            <button class="secondary" data-action="processDelivery">Process Delivery</button>
            <button class="secondary" data-action="recordEvent">Record Event</button>
            <button class="secondary" data-action="unsubscribeToken">Unsubscribe Token</button>
            <button class="secondary" data-action="sendEmail">Send Email</button>
            <button class="secondary" data-action="sendTestEmail">Send Test Email</button>
          </div>
        </div>
      </section>

      <section>
        <div class="section-head">
          <h2>Lists</h2>
          <button class="secondary" data-action="listAll">Refresh Lists</button>
        </div>
        <div class="body">
          <div class="actions">
            <button class="secondary" data-action="listTemplates">Templates</button>
            <button class="secondary" data-action="listContacts">Contacts</button>
            <button class="secondary" data-action="listCampaigns">Campaigns</button>
            <button class="secondary" data-action="listSendJobs">Send Jobs</button>
            <button class="secondary" data-action="listSendRecords">Send Records</button>
            <button class="secondary" data-action="listSuppressions">Suppressions</button>
            <button class="secondary" data-action="listEvents">Events</button>
            <button class="secondary" data-action="openDocs">Open /docs</button>
          </div>
        </div>
      </section>

      <section>
        <div class="section-head"><h2>Current IDs</h2></div>
        <div class="body state">
          <span>templateId</span><strong id="templateId">-</strong>
          <span>contactId</span><strong id="contactId">-</strong>
          <span>campaignId</span><strong id="campaignId">-</strong>
          <span>sendJobId</span><strong id="sendJobId">-</strong>
          <span>eventId</span><strong id="eventId">-</strong>
          <span>token</span><strong id="unsubscribeToken">-</strong>
        </div>
      </section>

      <section>
        <div class="section-head"><h2>Data And Audience</h2></div>
        <div class="body">
          <label>Audience rule JSON
            <textarea id="audienceRuleJson">{
  "field": "source",
  "comparator": "eq",
  "value": "api_tester"
}</textarea>
          </label>
          <div class="actions">
            <button class="secondary" data-action="createDataSource">Create Data Source</button>
            <button class="secondary" data-action="createMapping">Create Mapping</button>
            <button class="secondary" data-action="previewAudience">Preview Audience</button>
            <button class="secondary" data-action="createAudience">Create Audience</button>
            <button class="secondary" data-action="simulateBounce">Simulate Bounce</button>
          </div>
        </div>
      </section>
    </div>

    <section>
      <div class="section-head">
        <h2>Response Log</h2>
        <button class="secondary" id="clearLog">Clear</button>
      </div>
      <pre id="log"></pre>
    </section>
  </main>

  <script>
    const state = {
      templateId: "",
      contactId: "",
      campaignId: "",
      dataSourceId: "",
      eventId: "",
      mappingId: "",
      sendJobId: "",
      unsubscribeToken: "",
    };

    const stamp = Date.now();
    document.getElementById("contactEmail").value = `api-tester-${stamp}@example.com`;

    function setState(key, value) {
      state[key] = value || "";
      document.getElementById(key).textContent = value || "-";
    }

    function log(title, data, ok = true) {
      const out = document.getElementById("log");
      const prefix = ok ? "OK" : "ERROR";
      out.textContent =
        `[${new Date().toISOString()}] ${prefix}: ${title}\n` +
        JSON.stringify(data, null, 2) +
        "\n\n" +
        out.textContent;
    }

    async function request(title, path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
      });
      const text = await response.text();
      let data;
      try { data = text ? JSON.parse(text) : null; } catch { data = text; }
      log(`${options.method || "GET"} ${path}`, data, response.ok);
      if (!response.ok) {
        throw new Error(`${title} failed: ${response.status}`);
      }
      return data;
    }

    function readVariables() {
      try {
        const variables = JSON.parse(document.getElementById("variablesJson").value || "{}");
        variables.first_name = variables.first_name || document.getElementById("firstName").value;
        return variables;
      } catch (error) {
        log("email data JSON", { message: error.message }, false);
        throw error;
      }
    }

    function readAudienceRule() {
      try {
        return JSON.parse(document.getElementById("audienceRuleJson").value || "{}");
      } catch (error) {
        log("audience rule JSON", { message: error.message }, false);
        throw error;
      }
    }

    const actions = {
      health: () => request("health", "/health"),
      ready: () => request("ready", "/ready"),
      async validateTemplate() {
        await request("validate template", "/api/v1/templates/validate", {
          method: "POST",
          body: JSON.stringify({
            subject: "Hello {{ first_name }}",
            html_body: document.getElementById("htmlBody").value,
            css_body: "body { font-family: Arial, sans-serif; }",
            text_body: "Hello {{ first_name }}. Your plan is {{ plan }}.",
            variables: readVariables(),
          }),
        });
      },
      async previewTemplate() {
        await request("preview template", "/api/v1/templates/preview", {
          method: "POST",
          body: JSON.stringify({
            subject: "Hello {{ first_name }}",
            html_body: document.getElementById("htmlBody").value,
            css_body: "body { font-family: Arial, sans-serif; }",
            text_body: "Hello {{ first_name }}. Your plan is {{ plan }}.",
            variables: readVariables(),
          }),
        });
      },
      async createTemplate() {
        const template = await request("create template", "/api/v1/templates", {
          method: "POST",
          body: JSON.stringify({
            name: `api-tester-${Date.now()}`,
            subject: "Hello {{ first_name }}",
            html_body: document.getElementById("htmlBody").value,
            css_body: "body { font-family: Arial, sans-serif; }",
            text_body: "Hello {{ first_name }}. Your plan is {{ plan }}.",
          }),
        });
        setState("templateId", template.id);
      },
      async upsertContact() {
        const contact = await request("upsert contact", "/api/v1/audiences/contacts", {
          method: "POST",
          body: JSON.stringify({
            email: document.getElementById("contactEmail").value,
            first_name: document.getElementById("firstName").value,
            last_name: "Tester",
            source: "api_tester",
            attributes: { manual_test: true, ...readVariables() },
          }),
        });
        setState("contactId", contact.id);
      },
      async createCampaign() {
        if (!state.templateId) await actions.createTemplate();
        const campaign = await request("create campaign", "/api/v1/campaigns", {
          method: "POST",
          body: JSON.stringify({
            name: `API Tester ${Date.now()}`,
            template_id: state.templateId,
            audience_query: readAudienceRule(),
          }),
        });
        setState("campaignId", campaign.id);
      },
      async launchCampaign() {
        if (!state.campaignId) await actions.createCampaign();
        const launch = await request(
          "launch campaign",
          `/api/v1/campaigns/${state.campaignId}/launch`,
          {
            method: "POST",
            body: JSON.stringify({ variables: readVariables() }),
          },
        );
        setState("sendJobId", launch.job_id);
      },
      async processDelivery() {
        if (!state.sendJobId) await actions.launchCampaign();
        await request(
          "process delivery",
          `/api/v1/delivery/process-queued?limit=5&send_job_id=${state.sendJobId}`,
          { method: "POST" },
        );
      },
      async recordEvent() {
        if (!state.contactId) await actions.upsertContact();
        if (!state.campaignId) await actions.createCampaign();
        const event = await request("record event", "/api/v1/events", {
          method: "POST",
          body: JSON.stringify({
            contact_id: state.contactId,
            campaign_id: state.campaignId,
            event_type: "opened",
            provider_message_id: `manual-${Date.now()}`,
            metadata_json: { source: "api_tester" },
          }),
        });
        setState("eventId", event.id);
      },
      async unsubscribeToken() {
        if (!state.contactId) await actions.upsertContact();
        const token = await request(
          "unsubscribe token",
          `/api/v1/audiences/contacts/${state.contactId}/unsubscribe-token`,
          { method: "POST" },
        );
        setState("unsubscribeToken", token.token);
      },
      async sendTestEmail() {
        if (!state.templateId) await actions.createTemplate();
        await request("send test email", "/api/v1/tests/send-email", {
          method: "POST",
          body: JSON.stringify({
            template_id: state.templateId,
            to_email: document.getElementById("contactEmail").value,
            variables: readVariables(),
          }),
        });
      },
      async sendEmail() {
        if (!state.templateId) await actions.createTemplate();
        if (!state.contactId) await actions.upsertContact();
        await request("send email", "/api/v1/emails/send", {
          method: "POST",
          body: JSON.stringify({
            template_id: state.templateId,
            contact_id: state.contactId,
            campaign_id: state.campaignId || null,
            variables: readVariables(),
          }),
        });
      },
      async createDataSource() {
        const source = await request("create data source", "/api/v1/data-sources", {
          method: "POST",
          body: JSON.stringify({
            name: `api-tester-source-${Date.now()}`,
            source_type: "manual",
            config: { created_from: "tester" },
          }),
        });
        state.dataSourceId = source.id;
      },
      async createMapping() {
        if (!state.dataSourceId) await actions.createDataSource();
        const mapping = await request("create mapping", "/api/v1/data-source-mappings", {
          method: "POST",
          body: JSON.stringify({
            data_source_id: state.dataSourceId,
            name: `api-tester-map-${Date.now()}`,
            object_type: "contact",
            mapping: { email: "email", plan: "attributes.plan" },
            extraction_plan: { mode: "manual" },
          }),
        });
        state.mappingId = mapping.id;
      },
      async previewAudience() {
        await request("preview audience", "/api/v1/audiences/preview", {
          method: "POST",
          body: JSON.stringify({ rule_tree: readAudienceRule(), limit: 10 }),
        });
      },
      async createAudience() {
        await request("create audience", "/api/v1/audiences", {
          method: "POST",
          body: JSON.stringify({
            name: `api-tester-audience-${Date.now()}`,
            description: "Created from tester",
            rule_tree: readAudienceRule(),
          }),
        });
      },
      async simulateBounce() {
        await request("simulate bounce", "/api/v1/provider-webhooks/sendgrid", {
          method: "POST",
          body: JSON.stringify([{
            email: document.getElementById("contactEmail").value,
            event: "bounce",
            sg_message_id: `tester-${Date.now()}.filter`,
            reason: "Simulated from tester",
            timestamp: Math.floor(Date.now() / 1000),
          }]),
        });
      },
      listTemplates: () => request("list templates", "/api/v1/templates"),
      listContacts: () => request("list contacts", "/api/v1/audiences/contacts"),
      listCampaigns: () => request("list campaigns", "/api/v1/campaigns"),
      listSendJobs: () => request("list send jobs", "/api/v1/campaign-send-jobs/list"),
      listSendRecords: () => request("list send records", "/api/v1/email-send-records/list"),
      listSuppressions: () => request("list suppressions", "/api/v1/suppressions"),
      listEvents: () => request("list events", "/api/v1/events"),
      async listAll() {
        await actions.listTemplates();
        await actions.listContacts();
        await actions.listCampaigns();
        await actions.listSendJobs();
        await actions.listSendRecords();
        await actions.listSuppressions();
        await actions.listEvents();
      },
      openDocs() {
        window.open("/docs", "_blank", "noopener,noreferrer");
      },
      async runAll() {
        await actions.health();
        await actions.ready();
        await actions.validateTemplate();
        await actions.createTemplate();
        await actions.previewTemplate();
        await actions.upsertContact();
        await actions.createCampaign();
        await actions.launchCampaign();
        await actions.recordEvent();
        await actions.unsubscribeToken();
        await actions.sendEmail();
        await actions.sendTestEmail();
        await actions.listAll();
      },
    };

    document.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", async () => {
        button.disabled = true;
        try {
          await actions[button.dataset.action]();
        } catch (error) {
          log(button.dataset.action, { message: error.message }, false);
        } finally {
          button.disabled = false;
        }
      });
    });

    document.getElementById("runAll").addEventListener("click", async (event) => {
      event.currentTarget.disabled = true;
      try {
        await actions.runAll();
      } catch (error) {
        log("run all", { message: error.message }, false);
      } finally {
        event.currentTarget.disabled = false;
      }
    });

    document.getElementById("clearLog").addEventListener("click", () => {
      document.getElementById("log").textContent = "";
    });
  </script>
</body>
</html>"""
