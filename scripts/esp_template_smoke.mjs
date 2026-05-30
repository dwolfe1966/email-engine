#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const baseUrl = (process.argv[2] || process.env.ESP_BASE_URL || 'https://email-engine.app').replace(/\/$/, '');
const targetUrl = `${baseUrl}/esp/templates`;
const chromePath = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const port = Number(process.env.CHROME_DEBUG_PORT || 9223);
const userDataDir = await mkdtemp(join(tmpdir(), 'ee-esp-smoke-'));
const errors = [];
let tempTemplateId = '';
let chrome;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchJson(url, attempts = 40) {
  let lastError;
  for (let index = 0; index < attempts; index += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return response.json();
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(150);
  }
  throw lastError || new Error(`Unable to fetch ${url}`);
}

async function apiJson(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new Error(`${options.method || 'GET'} ${path} failed: ${response.status} ${body}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

async function removeTempDir(path, attempts = 5) {
  let lastError;
  for (let index = 0; index < attempts; index += 1) {
    try {
      await rm(path, { recursive: true, force: true });
      return;
    } catch (error) {
      lastError = error;
      await sleep(250);
    }
  }
  if (lastError?.code !== 'ENOENT') throw lastError;
}

function connectToCdp(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let nextId = 1;
  const pending = new Map();
  const listeners = new Map();

  ws.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message || JSON.stringify(message.error)));
      else resolve(message.result || {});
      return;
    }
    const handlers = listeners.get(message.method) || [];
    handlers.forEach((handler) => handler(message.params || {}));
  });

  function send(method, params = {}) {
    const id = nextId;
    nextId += 1;
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  function on(method, handler) {
    listeners.set(method, [...(listeners.get(method) || []), handler]);
  }

  return new Promise((resolve, reject) => {
    ws.addEventListener('open', () => resolve({ ws, send, on }));
    ws.addEventListener('error', () => reject(new Error(`Unable to connect to Chrome CDP: ${wsUrl}`)));
  });
}

function failOnRuntimeSignal(params) {
  const text = params?.exceptionDetails?.text || params?.exceptionDetails?.exception?.description || '';
  if (text) errors.push(text);
}

function failOnConsoleError(params) {
  if (params.type !== 'error') return;
  const text = (params.args || [])
    .map((arg) => arg.value || arg.description || '')
    .filter(Boolean)
    .join(' ');
  errors.push(text || 'Console error emitted.');
}

function failOnLogError(params) {
  if (!['error', 'warning'].includes(params.level)) return;
  const text = params.text || '';
  if (/favicon|manifest|Failed to load resource/i.test(text)) return;
  errors.push(text || `Log ${params.level} emitted.`);
}

try {
  const smokeMarker = `Smoke saved design ${Date.now()}`;
  const tempTemplate = await apiJson('/api/v1/templates', {
    method: 'POST',
    body: JSON.stringify({
      name: smokeMarker,
      subject: 'Hello {{ first_name }}',
      html_body: `<div class="email-container">
  <div class="promo-section">
    <h1 class="email-title">${smokeMarker}</h1>
    <p class="email-copy">Hello {{ first_name }}, your {{ plan }} plan is ready.</p>
  </div>
</div>`,
      css_body: '.email-title { color: #2563eb; } .email-copy { color: #111827; }',
      text_body: null,
      document_json: {},
    }),
  });
  tempTemplateId = tempTemplate.id;

  chrome = spawn(chromePath, [
    '--headless=new',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ], { stdio: ['ignore', 'pipe', 'pipe'] });

  chrome.on('error', (error) => {
    errors.push(`Chrome launch failed: ${error.message}`);
  });

  const tabs = await fetchJson(`http://127.0.0.1:${port}/json`);
  const page = tabs.find((item) => item.type === 'page') || tabs[0];
  if (!page?.webSocketDebuggerUrl) throw new Error('Chrome did not expose a page websocket.');

  const cdp = await connectToCdp(page.webSocketDebuggerUrl);
  cdp.on('Runtime.exceptionThrown', failOnRuntimeSignal);
  cdp.on('Runtime.consoleAPICalled', failOnConsoleError);
  cdp.on('Log.entryAdded', ({ entry }) => failOnLogError(entry || {}));

  await cdp.send('Runtime.enable');
  await cdp.send('Page.enable');
  await cdp.send('Log.enable');

  let loaded = false;
  cdp.on('Page.loadEventFired', () => {
    loaded = true;
  });
  await cdp.send('Page.navigate', { url: targetUrl });
  for (let index = 0; index < 80 && !loaded; index += 1) await sleep(100);
  await sleep(1200);

  const renderCheck = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const root = document.querySelector('#root');
      const bodyText = document.body?.innerText || '';
      return {
        title: document.title,
        hasRoot: Boolean(root),
        rootChildCount: root ? root.childElementCount : 0,
        bodyText,
        bundleScripts: Array.from(document.scripts).map((script) => script.src).filter(Boolean),
      };
    })()`,
    returnByValue: true,
  });
  const value = renderCheck.result?.value || {};
  if (value.title !== 'Email Engine ESP') errors.push(`Unexpected title: ${value.title}`);
  if (!value.hasRoot || !value.rootChildCount) errors.push('React root did not render children.');
  if (!/Template|Content|Email Engine/i.test(value.bodyText || '')) {
    errors.push('Rendered page text did not include expected ESP template content.');
  }
  if (!value.bundleScripts?.some((src) => src.includes('/esp/assets/'))) {
    errors.push('ESP bundle script was not loaded from /esp/assets/.');
  }

  const existingDesignCheck = await cdp.send('Runtime.evaluate', {
    expression: `(async () => {
      const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const buttonByText = (text) => Array.from(document.querySelectorAll('button'))
        .find((button) => (button.textContent || '').trim().toLowerCase() === text.toLowerCase());
      const modeButtonByText = (text) => Array.from(document.querySelectorAll('.mode-switch button'))
        .find((button) => (button.textContent || '').trim().toLowerCase() === text.toLowerCase())
        || buttonByText(text);
      const savedState = () => (document.querySelector('.edit-state-pill')?.textContent || '').trim();
      const canvasBlockCount = () => document.querySelector('iframe.design-canvas-frame')?.contentDocument?.querySelectorAll('.ee-design-block')?.length || 0;
      const nestedTreeRowCount = () => document.querySelectorAll('.design-tree-row.nested, .design-tree-row[aria-level="2"], .design-tree-row[aria-level="3"]').length;
      const deepestTreeLevel = () => Math.max(0, ...Array.from(document.querySelectorAll('.design-tree-row'))
        .map((row) => Number(row.getAttribute('aria-level') || 0)));
      window.location.hash = '#templates/${tempTemplateId}';
      for (let index = 0; index < 50; index += 1) {
        await wait(150);
        if ((document.body?.innerText || '').includes(${JSON.stringify(smokeMarker)})) break;
      }
      const initialState = savedState();
      const design = modeButtonByText('Design');
      if (!design) return { ok: false, reason: 'Design button not found for existing template', initialState };
      design.click();
      for (let index = 0; index < 40; index += 1) {
        await wait(150);
        if (canvasBlockCount() >= 2 && document.querySelector('.design-inspector-panel')) break;
      }
      const designBlockCount = canvasBlockCount();
      const nestedRows = nestedTreeRowCount();
      const deepestLevel = deepestTreeLevel();
      if (designBlockCount < 2) {
        return { ok: false, reason: 'Nested wrapper did not reverse-engineer into editable blocks', initialState, designBlockCount };
      }
      if (nestedRows < 1) {
        return { ok: false, reason: 'Nested wrapper did not render visible hierarchy rows', initialState, designBlockCount, nestedRows };
      }
      if (deepestLevel < 3) {
        return { ok: false, reason: 'Template design hierarchy did not render multiple nesting levels', initialState, designBlockCount, nestedRows, deepestLevel };
      }
      const afterDesignState = savedState();
      if (!/saved/i.test(afterDesignState) || /unsaved/i.test(afterDesignState)) {
        return { ok: false, reason: 'Design mode marked existing template dirty', initialState, afterDesignState };
      }
      let preview = null;
      for (let index = 0; index < 60; index += 1) {
        preview = Array.from(document.querySelectorAll('.compact-design-toolbar button, .design-builder-shell button'))
          .find((button) => (button.textContent || '').trim().toLowerCase() === 'preview design' && !button.disabled)
          || Array.from(document.querySelectorAll('.mode-switch button'))
            .find((button) => (button.textContent || '').trim().toLowerCase() === 'preview' && !button.disabled);
        if (preview) break;
        await wait(150);
      }
      if (!preview) return { ok: false, reason: 'Preview button not found after design transition', afterDesignState };
      preview.click();
      for (let index = 0; index < 120; index += 1) {
        await wait(200);
        const iframe = document.querySelector('iframe.email-preview');
        const srcDoc = iframe?.getAttribute('srcdoc') || iframe?.srcdoc || iframe?.contentDocument?.documentElement?.outerHTML || '';
        if (iframe && srcDoc.includes(${JSON.stringify(smokeMarker)})) {
          const afterPreviewState = savedState();
          return {
            ok: /saved/i.test(afterPreviewState) && !/unsaved/i.test(afterPreviewState),
            initialState,
            afterDesignState,
            afterPreviewState,
            srcDocLength: srcDoc.length,
            designBlockCount,
            nestedRows,
            deepestLevel,
          };
        }
      }
      return {
        ok: false,
        reason: 'Existing template design preview did not render marker',
        initialState,
        afterDesignState,
        afterPreviewState: savedState(),
        designBlockCount,
        nestedRows,
        deepestLevel,
        srcDocSnippet: (document.querySelector('iframe.email-preview')?.getAttribute('srcdoc') || '').slice(0, 240),
        bodyText: document.body?.innerText || '',
      };
    })()`,
    awaitPromise: true,
    returnByValue: true,
  });
  const existingDesign = existingDesignCheck.result?.value || {};
  if (!existingDesign.ok) {
    errors.push(`Existing template design transition failed: ${existingDesign.reason || 'dirty state or preview failure'} (${JSON.stringify({
      initialState: existingDesign.initialState,
      afterDesignState: existingDesign.afterDesignState,
      afterPreviewState: existingDesign.afterPreviewState,
      designBlockCount: existingDesign.designBlockCount,
      nestedRows: existingDesign.nestedRows,
      deepestLevel: existingDesign.deepestLevel,
      srcDocLength: existingDesign.srcDocLength,
      srcDocSnippet: existingDesign.srcDocSnippet,
    })})`);
  }

  const designPreviewCheck = await cdp.send('Runtime.evaluate', {
    expression: `(async () => {
      const buttonByText = (text) => Array.from(document.querySelectorAll('button'))
        .find((button) => (button.textContent || '').trim().toLowerCase() === text.toLowerCase());
      const modeButtonByText = (text) => Array.from(document.querySelectorAll('.mode-switch button'))
        .find((button) => (button.textContent || '').trim().toLowerCase() === text.toLowerCase())
        || buttonByText(text);
      const includesButton = (text) => Array.from(document.querySelectorAll('button'))
        .find((button) => (button.textContent || '').toLowerCase().includes(text.toLowerCase()));
      const selectedTextControl = () => {
        const inspector = document.querySelector('.design-inspector-panel');
        if (!inspector) return null;
        return Array.from(inspector.querySelectorAll('label'))
          .find((label) => (label.textContent || '').trim().startsWith('Text'))
          ?.querySelector('input, textarea') || null;
      };
      const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      let design = modeButtonByText('Design');
      if (!design) {
        window.location.hash = '#templates/new';
        for (let index = 0; index < 30 && !design; index += 1) {
          await wait(150);
          design = modeButtonByText('Design');
        }
      }
      if (!design) return { ok: false, reason: 'Design button not found' };
      design.click();
      await wait(400);
      if (!selectedTextControl()) {
        const heading = buttonByText('heading');
        if (!heading) return { ok: false, reason: 'Heading design block button not found' };
        heading.click();
        await wait(400);
      }
      const styleButton = Array.from(document.querySelectorAll('.design-inspector-panel button, .design-canvas-selection button'))
        .find((button) => ['style', 'add class'].includes((button.textContent || '').trim().toLowerCase()) && !button.disabled);
      if (!styleButton) return { ok: false, reason: 'Design style/add-class action not found' };
      styleButton.click();
      let cssReady = false;
      for (let index = 0; index < 60; index += 1) {
        await wait(150);
        const activeEdit = document.querySelector('.mode-switch .edit-mode.active');
        const cssText = document.querySelector('.css-tool-actions')?.textContent || '';
        const cssEditor = document.querySelector('.css-editor-field textarea');
        if (activeEdit && cssEditor && /working on \\./i.test(cssText)) {
          cssReady = true;
          break;
        }
      }
      if (!cssReady) return { ok: false, reason: 'Design style action did not open focused CSS tools' };
      const backToDesign = Array.from(document.querySelectorAll('.css-tool-actions button'))
        .find((button) => (button.textContent || '').trim().toLowerCase() === 'back to design' && !button.disabled);
      if (!backToDesign) return { ok: false, reason: 'Back to Design action not available from CSS tools' };
      backToDesign.click();
      for (let index = 0; index < 40; index += 1) {
        await wait(150);
        if (document.querySelector('.mode-switch .design-mode.active') && selectedTextControl()) break;
      }
      if (!document.querySelector('.mode-switch .design-mode.active') || !selectedTextControl()) {
        return { ok: false, reason: 'Back to Design did not reselect editable block' };
      }
      const marker = 'Smoke headline ' + Date.now();
      const inspector = document.querySelector('.design-inspector-panel');
      if (!inspector) return { ok: false, reason: 'Selected block inspector not found' };
      const textInput = selectedTextControl();
      if (!textInput) return { ok: false, reason: 'Selected block text control not found' };
      const valueSetter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(textInput), 'value')?.set;
      valueSetter ? valueSetter.call(textInput, marker) : (textInput.value = marker);
      textInput.dispatchEvent(new Event('input', { bubbles: true }));
      textInput.dispatchEvent(new Event('change', { bubbles: true }));
      await wait(300);
      const preview = includesButton('Preview Design') || buttonByText('Preview');
      if (!preview) return { ok: false, reason: 'Preview Design button not found' };
      preview.click();
      for (let index = 0; index < 50; index += 1) {
        await wait(150);
        const iframe = document.querySelector('iframe.email-preview');
        const srcDoc = iframe?.getAttribute('srcdoc') || iframe?.srcdoc || iframe?.contentDocument?.documentElement?.outerHTML || '';
        if (iframe && srcDoc.trim().length > 80) {
          return {
            ok: true,
            srcDocLength: srcDoc.length,
            hasExpectedContent: srcDoc.includes(marker),
          };
        }
      }
      return {
        ok: false,
        reason: 'Preview iframe did not render non-empty srcdoc',
        modeText: document.body?.innerText || '',
      };
    })()`,
    awaitPromise: true,
    returnByValue: true,
  });
  const designPreview = designPreviewCheck.result?.value || {};
  if (!designPreview.ok) {
    errors.push(`Design preview failed: ${designPreview.reason || 'unknown failure'}`);
  } else if (!designPreview.hasExpectedContent) {
    errors.push(`Design preview rendered unexpected content (${designPreview.srcDocLength || 0} chars).`);
  }

  await cdp.ws.close();

  if (errors.length) {
    console.error(`ESP template smoke failed for ${targetUrl}`);
    errors.forEach((error) => console.error(`- ${error}`));
    process.exitCode = 1;
  } else {
    console.log(`ESP template smoke passed for ${targetUrl}`);
  }
} finally {
  if (chrome && !chrome.killed) chrome.kill();
  if (tempTemplateId) {
    await apiJson(`/api/v1/templates/${tempTemplateId}`, { method: 'DELETE' }).catch((error) => {
      console.error(`Unable to delete smoke template ${tempTemplateId}: ${error.message}`);
    });
  }
  await removeTempDir(userDataDir);
}
