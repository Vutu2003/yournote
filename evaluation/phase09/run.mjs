import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { once } from 'node:events';
import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { platform, release, arch } from 'node:os';
import { createInterface } from 'node:readline';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const project = resolve(directory, '../..');
const args = process.argv.slice(2);
const serveOnly = args.includes('--serve-only');
const outputArgument = args.find((arg) => arg !== '--serve-only');
const output = outputArgument ? resolve(outputArgument) : await mkdtemp('/tmp/yournote-phase09-replay-');
const temp = await mkdtemp('/tmp/yournote-phase09-');
const root = join(temp, 'isolated');
await mkdir(root);
await mkdir(output, { recursive: true });
const modelCalls = [];
const browserErrors = [];
const scenarios = JSON.parse(await readFile(join(directory, 'scenarios.json'), 'utf8'));
const sha256 = async (path) => createHash('sha256').update(await readFile(path)).digest('hex');

async function studyDesignSha256() {
  const workspaceReport = join(project, '../results/phase_09_reading_evaluation.md');
  const report = existsSync(workspaceReport)
    ? workspaceReport
    : join(project, 'results/phase_09_reading_evaluation.md');
  const markdown = await readFile(report, 'utf8');
  const section = markdown.match(/^<!-- phase09-study:start -->\r?\n([\s\S]+?)^<!-- phase09-study:end -->$/m);
  if (!section) throw new Error('Missing Phase 09 study design in the evaluation report.');
  return createHash('sha256').update(section[1]).digest('hex');
}

let server;
let chrome;
let sequence = 0;
const pending = new Map();
const responses = [];

function cdp(method, params = {}, sessionId) {
  return new Promise((complete, fail) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); fail(new Error('Timed out: ' + method)); }, 12000);
    pending.set(id, { complete, fail, timer });
    chrome.stdio[3].write(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }) + '\0');
  });
}

function connectBrowser() {
  chrome = spawn(process.env.PHASE09_CHROME || '/usr/bin/google-chrome', [
    '--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
    '--disable-background-networking', '--disable-extensions', '--no-first-run',
    '--no-default-browser-check', '--remote-debugging-pipe', '--user-data-dir=' + join(temp, 'chrome'),
  ], { stdio: ['ignore', 'ignore', 'pipe', 'pipe', 'pipe'] });
  chrome.stderr.resume();
  let buffer = '';
  chrome.stdio[4].setEncoding('utf8');
  chrome.stdio[4].on('data', (data) => {
    buffer += data;
    let separator;
    while ((separator = buffer.indexOf('\0')) >= 0) {
      const raw = buffer.slice(0, separator);
      buffer = buffer.slice(separator + 1);
      if (!raw) continue;
      const message = JSON.parse(raw);
      const waiter = pending.get(message.id);
      if (waiter) {
        clearTimeout(waiter.timer);
        pending.delete(message.id);
        if (message.error) waiter.fail(new Error(message.error.message));
        else waiter.complete(message.result);
      }
      if (message.method === 'Runtime.exceptionThrown') {
        const detail = message.params.exceptionDetails;
        browserErrors.push(detail.exception?.description || detail.text);
      }
      if (message.method === 'Network.requestWillBeSent' && message.params.request.url.endsWith('/api/ai/tasks')
          && message.params.request.method === 'POST') modelCalls.push(message.params.request.url);
      if (message.method === 'Network.responseReceived') {
        const { url, status } = message.params.response;
        responses.push({ session: message.sessionId, url, status });
      }
    }
  });
}

async function waitFor(read, description, ms = 10000) {
  const expires = performance.now() + ms;
  while (performance.now() < expires) {
    if (await read()) return;
    await delay(25);
  }
  throw new Error('Timed out: ' + description);
}

async function tab(url, viewport = scenarios.desktop) {
  const { targetId } = await cdp('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp('Target.attachToTarget', { targetId, flatten: true });
  await cdp('Page.enable', {}, sessionId);
  await cdp('Runtime.enable', {}, sessionId);
  await cdp('Network.enable', {}, sessionId);
  await cdp('Network.setCacheDisabled', { cacheDisabled: true }, sessionId);
  await cdp('Emulation.setDeviceMetricsOverride', {
    ...viewport, deviceScaleFactor: 1, mobile: viewport.width < 500,
  }, sessionId);
  await cdp('Page.navigate', { url }, sessionId);
  return { targetId, sessionId };
}

async function evaluate(page, fn, ...args) {
  const expression = '(' + fn + ')(...(' + JSON.stringify(args) + '))';
  const result = await cdp('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }, page.sessionId);
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  return result.result.value;
}

async function click(page, selector) {
  await evaluate(page, (query) => {
    const control = document.querySelector(query);
    if (!control || control.disabled || !control.checkVisibility()) throw new Error('Control unavailable: ' + query);
    control.click();
  }, selector);
}

async function field(page, selector, value) {
  await evaluate(page, (query, next) => {
    const element = document.querySelector(query);
    if (!element || element.disabled || !element.checkVisibility()) throw new Error('Field unavailable: ' + query);
    Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), 'value').set.call(element, next);
    const event = element instanceof HTMLSelectElement ? 'change' : 'input';
    element.dispatchEvent(new Event(event, { bubbles: true }));
  }, selector, value);
}

function exists(page, select) {
  return evaluate(page, (query) => Boolean(document.querySelector(query)?.checkVisibility()), select);
}

async function reload(page) {
  const before = await evaluate(page, () => performance.timeOrigin);
  await cdp('Page.reload', {}, page.sessionId);
  await waitFor(async () => (await evaluate(page, () => performance.timeOrigin)) !== before, 'document reload');
}

async function openNotebook(page, name) {
  await waitFor(() => exists(page, '.notebook-open'), 'notebook list');
  await evaluate(page, (title) => {
    const entry = [...document.querySelectorAll('.notebook-open')].find((button) =>
      button.querySelector('.notebook-row-title')?.textContent === title);
    if (!entry) throw new Error('Synthetic notebook missing');
    entry.click();
  }, name);
  await waitFor(() => exists(page, '.generation-info'), 'history and generation metadata');
}

async function inspectPage(page, expected) {
  const number = await evaluate(page, () => Number(document.querySelector('[aria-label="Trang PDF"]')?.value));
  assert.equal(number, expected);
  return evaluate(page, () => {
    const scroll = document.querySelector('.pdf-scroll');
    const pane = document.querySelector('.pdf-page');
    const area = scroll.getBoundingClientRect();
    const sheet = pane.getBoundingClientRect();
    return {
      document_scroll_fits: document.documentElement.scrollWidth <= innerWidth + 1,
      page_fits_panel: sheet.left >= area.left - 1 && sheet.right <= area.right + 1
        && sheet.top >= area.top - 1 && sheet.bottom <= area.bottom + 1,
      scroll_top: scroll.scrollTop,
      vertical_scroll_excess_px: Math.max(0, scroll.scrollHeight - scroll.clientHeight),
      default_fit_label: document.querySelector('.pdf-fit-button').textContent.trim(),
    };
  });
}

async function shot(page, name) {
  const result = await cdp('Page.captureScreenshot', { format: 'png' }, page.sessionId);
  await writeFile(join(output, name), Buffer.from(result.data, 'base64'), { flag: 'wx' });
}

const viewURL = (origin, run, pdf = false) =>
  origin + '/phase09/compare?trial=' + encodeURIComponent(run.trial_id) + (pdf ? '&view=pdf' : '');

async function measure(run, env) {
  const { origin, docs } = env;
  const row = {
    mode: run.mode, set: run.set, trial_id: run.trial_id, sequence: run.sequence, order: run.order,
    page_expected: run.page, page_observed: null, scope_correct: false, evidence_confirmed: false,
    notes_reopened: false, tab_switches: 0, requested_help: null, subjective_focus: null,
    position_open_seconds: null, evidence_seconds: null, note_reopened_seconds: null,
    model_label: null, status: 'technical_error', started: false,
  };
  const tabs = [];
  let stage = 'prepare';
  let start;
  let photo;
  let captureMs = 0;
  async function capture(page) {
    const began = performance.now();
    photo = await cdp('Page.captureScreenshot', { format: 'png' }, page.sessionId);
    captureMs += performance.now() - began;
  }
  try {
    let text;
    let pdf;
    if (run.mode === 'yournote') {
      text = await tab(origin);
      tabs.push(text);
      await openNotebook(text, run.notebook_title);
      await waitFor(() => exists(text, '.source-row input[type=checkbox]'), 'source checkboxes');
    } else {
      pdf = await tab(viewURL(origin, run, true));
      tabs.push(pdf);
      await waitFor(() => exists(pdf, 'canvas[data-page="1"]'), 'initial separate PDF page');
      text = await tab(viewURL(origin, run));
      tabs.push(text);
      await waitFor(() => exists(text, '#content[aria-busy="false"]'), 'separate saved answer');
      row.verified_version = await evaluate(pdf, async (expected) => {
        const raw = await (await fetch('/phase09/original.pdf')).arrayBuffer();
        const hash = await crypto.subtle.digest('SHA-256', raw);
        return [...new Uint8Array(hash)].map((n) => n.toString(16).padStart(2, '0')).join('') === expected;
      }, run.citation.document_version);
      assert(row.verified_version);
    }
    const elapsed = () => Number(((performance.now() - start - captureMs) / 1000).toFixed(3));
    const twoTexts = run.verify_text;
    row.started = true;
    start = performance.now();
    stage = 'scope';
    if (run.mode === 'yournote') {
      await click(text, 'input[aria-label="Dùng nguồn ' + run.distractor_title + ' cho chat và Studio"]');
      await field(text, '#page-filter', String(run.page));
      row.scope_correct = await evaluate(text, (value) => {
        const selected = [...document.querySelectorAll('.source-row input:checked')];
        return selected.length === 1 && selected[0].getAttribute('aria-label').includes('.pdf')
          && document.querySelector('#page-filter').value === String(value);
      }, run.page);
      assert(row.scope_correct);
      row.model_label = await evaluate(text, () => document.querySelector('.generation-info').textContent);
      assert(row.model_label.includes(run.model));
      stage = 'citation';
      await click(text, '.conversation .inline-citation');
      await waitFor(() => exists(text, 'canvas[aria-label="PDF nguyên bản, trang ' + run.page + '"]')
        .then(async (present) => present && await evaluate(text, () =>
          document.querySelector('.pdf-scroll').getAttribute('aria-busy') === 'false')), 'render cited PDF');
      row.page_observed = await evaluate(text, () => Number(document.querySelector('[aria-label="Trang PDF"]').value));
      assert.equal(row.page_observed, run.page);
      const found = responses.filter((response) => response.session === text.sessionId && response.status < 400);
      row.citation_resolve_accepted = found.some((response) => response.url.includes('/citations/resolve'));
      row.verified_version = found.some((response) => response.url.includes('/pdf?version=' + run.citation.document_version));
      assert(row.citation_resolve_accepted && row.verified_version, 'Citation should fetch the original version from the real API');
      row.position_open_seconds = elapsed();
      row.evidence_confirmed = await evaluate(text, (needles) =>
        needles.every((needle) => document.querySelector('.pdf-text-layer').textContent.includes(needle)), twoTexts);
      assert(row.evidence_confirmed);
      row.evidence_seconds = elapsed();
      row.fit = await inspectPage(text, run.page);
      row.pdf_next_to_chat = await evaluate(text, () => {
        const pdfBounds = document.querySelector('#notebook-pdf-panel').getBoundingClientRect();
        const chatBounds = document.querySelector('.chat-panel').getBoundingClientRect();
        return pdfBounds.width > 0 && chatBounds.width > 0 && pdfBounds.right <= chatBounds.left + 1;
      });
      row.confirmed_scope_in_storage = await fetch(origin + '/api/notebooks/' + run.notebook_id)
        .then((r) => r.json()).then((book) => book.state.selected.length === 1
          && book.state.selected[0] === docs[scenarios.pdf].filename && book.state.page === String(run.page));
      assert(row.confirmed_scope_in_storage && row.pdf_next_to_chat);
      if (run.trial_id === 'I01-1') {
        await capture(text);
      }

      stage = 'note';
      await click(text, '.workspace-header-actions button.subtle');
      await click(text, '.notes-tool');
      await click(text, '.notes-heading button');
      await field(text, '.user-note-title', run.title);
      await field(text, '.user-note-content', run.note);
      await waitFor(async () => {
        const response = await fetch(origin + '/api/notebooks/' + run.notebook_id);
        const book = await response.json();
        return book.state.notes.some((note) => note.title === run.title && note.content === run.note);
      }, 'persisted notebook note');
      await reload(text);
      await openNotebook(text, run.notebook_title);
      await click(text, '.notes-tool');
      await waitFor(() => exists(text, '.user-note-open'), 'reopened note');
      await click(text, '.user-note-open');
      row.notes_reopened = await evaluate(text, (title, value) =>
        document.querySelector('.user-note-title').value === title && document.querySelector('.user-note-content').value === value,
      run.title, run.note);
    } else {
      await click(text, '#distractor');
      await field(text, '#scope-page', String(run.page));
      row.scope_correct = await evaluate(text, (value) => document.querySelector('#target').checked
        && !document.querySelector('#distractor').checked && document.querySelector('#scope-page').value === String(value), run.page);
      assert(row.scope_correct);
      row.model_label = await evaluate(text, () => document.querySelector('#model').textContent);
      assert.equal(row.model_label, run.model);
      stage = 'citation';
      const citedPage = await evaluate(text, () => Number(document.querySelector('#citation').textContent.match(/trang (\d+)$/)[1]));
      await cdp('Target.activateTarget', { targetId: pdf.targetId });
      row.tab_switches += 1;
      await field(pdf, '#page-number', String(citedPage));
      await click(pdf, '#page-form button');
      await waitFor(() => exists(pdf, 'canvas[data-page="' + run.page + '"]'), 'manually opened PDF page');
      row.page_observed = await evaluate(pdf, () => Number(document.querySelector('canvas').dataset.page));
      assert.equal(row.page_observed, run.page);
      row.position_open_seconds = elapsed();
      row.evidence_confirmed = await evaluate(pdf, (needles) =>
        needles.every((needle) => document.querySelector('canvas').dataset.text.includes(needle)), twoTexts);
      assert(row.evidence_confirmed);
      row.evidence_seconds = elapsed();
      if (run.trial_id === 'I02-1') await capture(pdf);
      stage = 'note';
      await cdp('Target.activateTarget', { targetId: text.targetId });
      row.tab_switches += 1;
      await field(text, '#note', run.note);
      await click(text, '#note-form button');
      await waitFor(() => evaluate(text, () => document.querySelector('#saved').textContent === 'Đã lưu'), 'saved separate note');
      await reload(text);
      await waitFor(() => exists(text, '#content[aria-busy="false"]'), 'reopened separate note');
      row.notes_reopened = await evaluate(text, (value) => document.querySelector('#note').value === value, run.note);
    }
    assert(row.notes_reopened);
    row.note_reopened_seconds = elapsed();
    row.status = 'completed';
    if (photo) await writeFile(join(output, run.mode + '.png'), Buffer.from(photo.data, 'base64'), { flag: 'wx' });
  } catch (error) {
    row.failure = { step: stage, detail: error.message };
  } finally {
    for (const page of tabs) await cdp('Target.closeTarget', { targetId: page.targetId });
  }
  console.log(row.trial_id + ' ' + row.mode + ' ' + row.set + ' ' + row.status);
  if (row.failure) console.log(row.failure);
  return row;
}

async function supplementaryMobile(env) {
  const run = env.runs.flat().find((trial) => trial.mode === 'yournote');
  const page = await tab(env.origin, scenarios.mobile_check);
  const details = { viewport: scenarios.mobile_check };
  try {
    await openNotebook(page, run.notebook_title);
    await waitFor(() => evaluate(page, () => Boolean(document.querySelector('.source-row input[type=checkbox]'))),
      'mobile source list loaded');
    await click(page, '.conversation .inline-citation');
    await waitFor(() => evaluate(page, (needles) => {
      const reader = document.querySelector('.pdf-reader');
      const text = reader?.querySelector('.pdf-text-layer')?.textContent || '';
      return reader?.checkVisibility() && reader.querySelector('.pdf-scroll')?.getAttribute('aria-busy') === 'false'
        && needles.every((needle) => text.includes(needle));
    }, run.verify_text), 'mobile PDF text');
    details.initial_fit = await inspectPage(page, run.page);
    await click(page, '[aria-label="Phóng to PDF"]');
    await waitFor(() => evaluate(page, () => document.querySelector('.pdf-fit-button').textContent.includes('%')), 'zoom button');
    await waitFor(() => evaluate(page, () => document.querySelector('.pdf-scroll').getAttribute('aria-busy') === 'false'), 'zoomed render');
    details.zoom_in = await inspectPage(page, run.page);
    await click(page, '.pdf-fit-button');
    await waitFor(() => evaluate(page, () => document.querySelector('.pdf-fit-button').textContent.trim() === 'Vừa trang'), 'reset fit');
    await waitFor(() => evaluate(page, () => document.querySelector('.pdf-scroll').getAttribute('aria-busy') === 'false'), 'fit render');
    details.restored_fit = await inspectPage(page, run.page);
    await shot(page, 'mobile-pdf.png');
    await click(page, '[aria-label="Đóng chế độ đọc chuyên sâu"]');
    await evaluate(page, () => {
      const nav = document.querySelector('.mobile-workspace-nav');
      [...nav.querySelectorAll('button')].find((button) => button.textContent.includes('Nguồn')).click();
    });
    const tick = 'input[aria-label="Đã đọc: ' + run.source_title + '"]';
    details.read_after_open = await evaluate(page, (selector) => document.querySelector(selector).checked, tick);
    await click(page, tick);
    await waitFor(async () => {
      const book = await fetch(env.origin + '/api/notebooks/' + run.notebook_id).then((r) => r.json());
      return book.state.read_documents.includes(env.docs[scenarios.pdf].filename);
    }, 'saved explicit read tick');
    details.read_after_tick = await evaluate(page, (selector) => document.querySelector(selector).checked, tick);
  } catch (error) {
    details.failure = error.message;
    details.layout = await evaluate(page, () => {
      const workspace = document.querySelector('.workspace');
      const reader = document.querySelector('.pdf-reader');
      return { mobile_panel: workspace?.dataset.mobilePanel, has_pdf: Boolean(reader),
        reader_display: reader ? getComputedStyle(reader).display : null,
        scroll_size: reader && [reader.querySelector('.pdf-scroll')?.clientWidth, reader.querySelector('.pdf-scroll')?.clientHeight],
        canvas_size: reader?.querySelector('canvas')?.getAttribute('width'),
        text_length: reader?.querySelector('.pdf-text-layer')?.textContent.length || 0,
        notice: document.querySelector('.pdf-message, .app-toast')?.textContent || null };
    });
    await shot(page, 'mobile-diagnostic.png');
  } finally {
    await cdp('Target.closeTarget', { targetId: page.targetId });
  }
  return details;
}

try {
  server = spawn(join(project, '.venv/bin/python'), ['-m', 'evaluation.phase09.serve', root], {
    cwd: project, stdio: ['ignore', 'pipe', 'inherit'],
  });
  const reader = createInterface({ input: server.stdout });
  const first = await Promise.race([
    once(reader, 'line').then(([line]) => line),
    once(server, 'exit').then(([code]) => { throw new Error('Temporary API exited: ' + code); }),
    delay(30000, null, { ref: false }).then(() => { throw new Error('Temporary API did not start'); }),
  ]);
  const env = JSON.parse(first);
  const nodeBin = join(project, '.tools/node/bin');
  execFileSync(join(nodeBin, 'node'), ['node_modules/vite/bin/vite.js', 'build', '--outDir', join(root, 'dist')], {
    cwd: join(project, 'frontend'), stdio: 'inherit', env: { ...process.env, VITE_API_BASE_URL: env.origin },
  });
  await waitFor(() => fetch(env.origin + '/api/health').then((r) => r.ok).catch(() => false), 'temporary API health');
  if (serveOnly) {
    console.log('YourNote: ' + env.origin);
    for (const run of env.runs.flat()) {
      console.log(run.notebook_id ? run.notebook_title : [run.trial_id, viewURL(env.origin, run), viewURL(env.origin, run, true)].join(' | '));
    }
    await new Promise((done) => { process.once('SIGINT', done); process.once('SIGTERM', done); });
  } else {
    connectBrowser();
    const browser = await cdp('Browser.getVersion');
    const rows = [];
    for (const run of env.runs.flat()) rows.push(await measure(run, env));
    const mobile = await supplementaryMobile(env);
    const data = {
      label: 'automated internal browser check', observed_utc: new Date().toISOString(), participants: 0,
      browser: browser.product, pdfjs: JSON.parse(await readFile(join(project, 'frontend/node_modules/pdfjs-dist/package.json'), 'utf8')).version,
      os: { platform: platform(), release: release(), architecture: arch() },
      app_commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: project, encoding: 'utf8' }).trim(),
      desktop: scenarios.desktop, task_limit_seconds: scenarios.task_limit_seconds,
      phase08_answers_sha256: env.phase08_answers_sha256, source_sha256: env.source_sha256,
      scenarios_sha256: await sha256(join(directory, 'scenarios.json')),
      study_design_sha256: await studyDesignSha256(),
      frontend_build_sha256: await sha256(join(root, 'dist/index.html')),
      backend_api: 'temporary real FastAPI, PDF originals and notebook SQLite',
      harness_sha256: Object.fromEntries(await Promise.all(['run.mjs', 'serve.py', 'comparison.html'].map(async (name) =>
        [name, await sha256(join(directory, name))]))),
      model_requested_calls: modelCalls.length, browser_errors: browserErrors, tasks: rows, mobile,
    };
    await writeFile(join(output, 'internal-check.json'), JSON.stringify(data, null, 2) + '\n', { flag: 'wx' });
    console.log('Saved internal check to ' + output);
    process.exitCode = rows.every((row) => row.status === 'completed') && !modelCalls.length && !browserErrors.length ? 0 : 1;
  }
} finally {
  if (chrome && chrome.exitCode === null) {
    chrome.kill();
    await Promise.race([once(chrome, 'exit'), delay(3000)]);
  }
  if (server && server.exitCode === null) {
    server.kill();
    await Promise.race([once(server, 'exit'), delay(3000)]);
  }
  await rm(temp, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
}
