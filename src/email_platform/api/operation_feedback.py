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

  function labelFor(input) {
    const raw = typeof input === "string" ? input : input && input.url ? input.url : "API request";
    try {
      const url = new URL(raw, window.location.origin);
      return `${url.pathname}${url.search ? " " + url.search : ""}`;
    } catch {
      return String(raw || "API request");
    }
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

  function begin(detail) {
    activeCount += 1;
    if (!activeStartedAt) activeStartedAt = performance.now();
    setState("info", "API operation running", detail, `${activeCount} operation${activeCount === 1 ? "" : "s"} · 0s`, true);
    startTimer();
    return performance.now();
  }

  function complete(startedAt, ok, detail) {
    activeCount = Math.max(0, activeCount - 1);
    if (activeCount > 0) return;
    window.clearInterval(timer);
    const elapsed = ((performance.now() - startedAt) / 1000).toFixed(1);
    activeStartedAt = 0;
    setState(ok ? "success" : "error", ok ? "API operation complete" : "API operation failed", detail, `${elapsed}s`, false);
  }

  dismissButton.addEventListener("click", () => {
    if (activeCount === 0) bar.className = "ee-operation-feedback";
  });

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const detail = labelFor(input);
    const startedAt = begin(detail);
    try {
      const response = await originalFetch(input, init);
      complete(startedAt, response.ok, `${response.status} ${detail}`);
      return response;
    } catch (error) {
      complete(startedAt, false, `${detail}: ${error && error.message ? error.message : error}`);
      throw error;
    }
  };
})();
</script>
"""


def with_operation_feedback(html: str) -> str:
    if '</body>' not in html:
        return html + OPERATION_FEEDBACK_SNIPPET
    return html.replace('</body>', f'{OPERATION_FEEDBACK_SNIPPET}\n</body>', 1)
