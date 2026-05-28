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

  const designPreviewCheck = await cdp.send('Runtime.evaluate', {
    expression: `(async () => {
      const buttonByText = (text) => Array.from(document.querySelectorAll('button'))
        .find((button) => (button.textContent || '').trim().toLowerCase() === text.toLowerCase());
      const includesButton = (text) => Array.from(document.querySelectorAll('button'))
        .find((button) => (button.textContent || '').toLowerCase().includes(text.toLowerCase()));
      const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      let design = buttonByText('Design');
      if (!design) {
        window.location.hash = '#templates/new';
        for (let index = 0; index < 30 && !design; index += 1) {
          await wait(150);
          design = buttonByText('Design');
        }
      }
      if (!design) return { ok: false, reason: 'Design button not found' };
      design.click();
      await wait(400);
      if (!document.querySelector('.design-block-card')) {
        const heading = buttonByText('heading');
        if (!heading) return { ok: false, reason: 'Heading design block button not found' };
        heading.click();
        await wait(400);
      }
      const firstCard = document.querySelector('.design-block-card');
      firstCard?.click();
      await wait(250);
      const marker = 'Smoke headline ' + Date.now();
      const inspector = document.querySelector('.design-inspector-panel');
      if (!inspector) return { ok: false, reason: 'Selected block inspector not found' };
      const textInput = Array.from(inspector.querySelectorAll('label')).find((label) => (label.textContent || '').trim().startsWith('Text'))?.querySelector('input, textarea');
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
  await removeTempDir(userDataDir);
}
