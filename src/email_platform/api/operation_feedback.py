OPERATION_FEEDBACK_SNIPPET = r"""
<script>
(() => {
  if (window.__emailEngineOperationFeedbackInstalled) return;
  window.__emailEngineOperationFeedbackInstalled = true;

  const style = document.createElement("style");
  style.textContent = `
    .ee-operation-feedback {
      position: sticky;
      top: 0;
      z-index: 9999;
      display: none;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 8px 18px;
      border-bottom: 1px solid #d8dee6;
      background: #f8fafc;
      color: #17202a;
      font: 12px Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      box-shadow: 0 1px 2px rgba(23, 32, 42, 0.05);
    }
    .ee-operation-feedback.visible { display: flex; }
    .ee-operation-feedback.active { background: #eff6ff; border-bottom-color: #bfdbfe; }
    .ee-operation-feedback.success { background: #f0fdf4; border-bottom-color: #bbf7d0; }
    .ee-operation-feedback.warning { background: #fffbeb; border-bottom-color: #fde68a; }
    .ee-operation-feedback.error { background: #fef2f2; border-bottom-color: #fecaca; }
    .ee-operation-feedback-copy,
    .ee-operation-feedback-meta {
      display: flex;
      align-items: center;
      min-width: 0;
      gap: 8px;
    }
    .ee-operation-feedback-copy strong { color: #17202a; white-space: nowrap; }
    .ee-operation-feedback-copy span:not(.ee-operation-feedback-dot) {
      overflow: hidden;
      color: #5b6673;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .ee-operation-feedback-meta { flex-shrink: 0; color: #5b6673; }
    .ee-operation-feedback-meta button {
      border: 1px solid #d8dee6;
      border-radius: 5px;
      background: #fff;
      color: #17202a;
      cursor: pointer;
      font: inherit;
      padding: 3px 7px;
    }
    .ee-operation-feedback-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #2563eb;
      animation: ee-operation-feedback-pulse 1.2s infinite;
    }
    @keyframes ee-operation-feedback-pulse {
      0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, .45); }
      70% { box-shadow: 0 0 0 7px rgba(37, 99, 235, 0); }
      100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
    }
  `;
  document.head.appendChild(style);

  const bar = document.createElement("div");
  bar.className = "ee-operation-feedback";
  bar.innerHTML = `
    <div class="ee-operation-feedback-copy">
      <span class="ee-operation-feedback-dot" aria-hidden="true"></span>
      <strong>Working</strong>
      <span></span>
    </div>
    <div class="ee-operation-feedback-meta">
      <span></span>
      <button type="button" aria-label="Dismiss operation message">Dismiss</button>
    </div>
  `;
  document.body.prepend(bar);

  const titleEl = bar.querySelector("strong");
  const detailEl = bar.querySelector(".ee-operation-feedback-copy span:last-child");
  const metaEl = bar.querySelector(".ee-operation-feedback-meta span");
  const dismissButton = bar.querySelector("button");
  let activeCount = 0;
  let activeStartedAt = 0;
  let timer = 0;

  function operationFor(input, init) {
    const raw = typeof input === "string" ? input : input && input.url ? input.url : "API request";
    const method = (init && init.method) || (input && input.method) || "GET";
    try {
      const url = new URL(raw, window.location.origin);
      return describeOperation(String(method).toUpperCase(), url.pathname, url.search);
    } catch {
      const detail = String(raw || "API request");
      return {
        label: "API operation running",
        successLabel: "API operation complete",
        errorLabel: "API operation failed",
        detail
      };
    }
  }

  function describeOperation(method, pathname, search) {
    const detail = `${method} ${pathname}${search ? " " + search : ""}`;
    const rules = [
      [/^\/api\/v1\/ai\/templates\/edit$/, "AI template edit"],
      [/^\/api\/v1\/ai\/templates\/recommend$/, "AI template recommendation"],
      [/^\/api\/v1\/ai\/templates\/draft$/, "AI template draft"],
      [/^\/api\/v1\/templates\/samples$/, "Sample templates reset"],
      [/^\/api\/v1\/templates\/preview$/, "Template preview"],
      [/^\/api\/v1\/templates\/document\/render$/, "Design render"],
      [/^\/api\/v1\/templates\/(?:variables|document\/variables)$/, "Template variables"],
      [/^\/api\/v1\/templates\/(?:validate|document\/validate)$/, "Template validation"],
      [/^\/api\/v1\/templates(?:\/[^/]+)?(?:\/document)?$/, "Template"],
      [/^\/api\/v1\/campaigns\/[^/]+\/launch$/, "Campaign launch"],
      [/^\/api\/v1\/campaigns\/[^/]+\/send-test$/, "Campaign test send"],
      [/^\/api\/v1\/campaigns\/[^/]+\/workflow-status$/, "Workflow readiness"],
      [/^\/api\/v1\/campaigns\/[^/]+\/analytics(?:\/timeline)?$/, "Campaign analytics"],
      [/^\/api\/v1\/campaigns(?:\/[^/]+)?$/, "Campaign"],
      [/^\/api\/v1\/campaign-send-jobs\/[^/]+\/progress$/, "Delivery progress"],
      [/^\/api\/v1\/campaign-send-jobs\/list$/, "Delivery jobs"],
      [/^\/api\/v1\/email-send-records\/[^/]+\/(?:requeue|skip)$/, "Send record update"],
      [/^\/api\/v1\/email-send-records\/list$/, "Send records"],
      [/^\/api\/v1\/delivery\/process-queued$/, "Delivery processing"],
      [/^\/api\/v1\/tracking\/(?:open|click)\//, "Tracking event"],
      [/^\/api\/v1\/events(?:\/list|\/timeline)?$/, "Event analytics"],
      [/^\/api\/v1\/analytics\//, "Analytics report"],
      [/^\/api\/v1\/audiences\/import-csv\/preview$/, "Audience import preview"],
      [/^\/api\/v1\/audiences\/import-csv$/, "Audience import"],
      [/^\/api\/v1\/audiences\/[^/]+\/(?:preview|snapshots)$/, "Audience preview"],
      [/^\/api\/v1\/audience-snapshots\/list$/, "Audience snapshots"],
      [/^\/api\/v1\/audiences(?:\/[^/]+)?$/, "Audience"],
      [/^\/api\/v1\/contacts(?:\/[^/]+)?$/, "Contact"],
      [/^\/api\/v1\/journeys\/process$/, "Journey processing"],
      [/^\/api\/v1\/journeys(?:\/[^/]+)?$/, "Journey"],
      [/^\/api\/v1\/journey-steps(?:\/[^/]+)?$/, "Journey step"],
      [/^\/api\/v1\/journey-enrollments(?:\/[^/]+|\/list)?$/, "Journey enrollment"],
      [/^\/api\/v1\/data-sources\/[^/]+\/(?:validate|schema|ingest)$/, "Data source operation"],
      [/^\/api\/v1\/data-source-import-jobs\/list$/, "Import jobs"],
      [/^\/api\/v1\/data-sources(?:\/[^/]+)?$/, "Data source"],
      [/^\/api\/v1\/suppressions(?:\/[^/]+|\/list)?$/, "Suppression"],
      [/^\/api\/v1\/tests\/send-email$/, "Test email send"],
      [/^\/api\/v1\/tests\//, "Test operation"],
      [/^\/api\/auth\/(?:login|logout|me)$/, "Authentication"],
    ];
    const match = rules.find(([pattern]) => pattern.test(pathname));
    const name = match ? match[1] : "API operation";
    return {
      label: `${name} running`,
      successLabel: `${name} complete`,
      errorLabel: `${name} failed`,
      detail
    };
  }

  function setState(tone, title, detail, meta, active) {
    bar.className = `ee-operation-feedback visible ${tone}${active ? " active" : ""}`;
    titleEl.textContent = title;
    detailEl.textContent = detail || "";
    metaEl.textContent = meta || "";
    dismissButton.style.display = active ? "none" : "";
  }

  function startTimer() {
    window.clearInterval(timer);
    timer = window.setInterval(() => {
      if (!activeStartedAt) return;
      const seconds = Math.floor((performance.now() - activeStartedAt) / 1000);
      metaEl.textContent = `${activeCount} operation${activeCount === 1 ? "" : "s"} · ${seconds}s`;
    }, 1000);
  }

  function begin(operation) {
    activeCount += 1;
    if (!activeStartedAt) activeStartedAt = performance.now();
    setState("info", operation.label, operation.detail, `${activeCount} operation${activeCount === 1 ? "" : "s"} · 0s`, true);
    startTimer();
    return performance.now();
  }

  function complete(startedAt, ok, operation, detail) {
    activeCount = Math.max(0, activeCount - 1);
    if (activeCount > 0) return;
    window.clearInterval(timer);
    const elapsed = ((performance.now() - startedAt) / 1000).toFixed(1);
    activeStartedAt = 0;
    setState(ok ? "success" : "error", ok ? operation.successLabel : operation.errorLabel, detail, `${elapsed}s`, false);
  }

  dismissButton.addEventListener("click", () => {
    if (activeCount === 0) bar.className = "ee-operation-feedback";
  });

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const operation = operationFor(input, init);
    const startedAt = begin(operation);
    try {
      const response = await originalFetch(input, init);
      complete(startedAt, response.ok, operation, `${response.status} ${operation.detail}`);
      return response;
    } catch (error) {
      complete(startedAt, false, operation, `${operation.detail}: ${error && error.message ? error.message : error}`);
      throw error;
    }
  };
})();
</script>
"""


def with_operation_feedback(html: str) -> str:
    close_body_index = html.lower().rfind('</body>')
    if close_body_index == -1:
        return html + OPERATION_FEEDBACK_SNIPPET
    return (
        html[:close_body_index]
        + OPERATION_FEEDBACK_SNIPPET
        + '\n'
        + html[close_body_index:]
    )
