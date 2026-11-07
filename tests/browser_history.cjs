/* Run against an isolated synthetic preview. Requires Playwright and Chrome.
   TL_UI_URL sets the origin; PLAYWRIGHT_MODULE can point to a local installation.
   All model responses below are synthetic fixtures, with no provider calls. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const origin = process.env.TL_UI_URL || 'http://127.0.0.1:8013';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage(), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let calls = 0, delay = 50, fail = false;
    const fixture = index => {
      const content = `Synthetic reference ${index}. <img src=x onerror=alert(1)> ` + 'The parser deadline moved after the review. '.repeat(20);
      const sources = [{ id: `source-${index}`, title: `Synthetic session ${index}`, content, timestamp: '00:10', speakers: ['Speaker A'], session_date: '2026-11-01' }];
      return { generated: true, mode: 'keyword', sources, models: { generation: 'synthetic-fixture' }, timings_ms: { total: 20 }, answer: {
        status: 'answered', points: [1, 2, 3].map(n => ({ text: `Point ${n}, response ${index}. ` + 'This is a synthetic answer for the history regression check. '.repeat(12), citations: [{ id: sources[0].id, quote: 'The parser deadline moved after the review.' }] })), actions: [],
      } };
    };
    await page.route('**/api/status', route => route.fulfill({ json: { configured: true, generation_model: 'synthetic-fixture', documents: [{ id: 'synthetic', title: 'Synthetic session', chunks: 1, embedded: 1, session_date: '2026-11-01' }] } }));
    await page.route('**/api/ask', async route => {
      const index = ++calls, payload = route.request().postDataJSON();
      await new Promise(resolve => setTimeout(resolve, delay));
      if (fail) { await route.fulfill({ status: 503, json: { error: 'Synthetic temporary failure.' } }).catch(() => {}); return; }
      const result = fixture(index);
      if (!payload.generate) { result.generated = false; result.answer = null; }
      await route.fulfill({ json: result }).catch(() => {});
    });
    const ready = () => page.waitForFunction(() => !document.querySelector('#question').disabled);
    const saved = async predicate => {
      const deadline = Date.now() + 10000;
      while (Date.now() < deadline) {
        if (await page.evaluate(predicate)) return;
        await new Promise(resolve => setTimeout(resolve, 30));
      }
      throw new Error('Expected browser storage state was not saved.');
    };
    const load = async () => { await page.goto(origin); await ready(); };
    const reload = async () => { await page.reload(); await ready(); };
    const submit = async question => { await page.locator('#question').fill(question); await page.locator('#question').press('Enter'); };
    await load();
    await page.locator('#model-choice').selectOption('configured');
    await page.locator('#sample-question').click();
    await page.waitForSelector('[data-revealing=true]');
    assert.equal(calls, 1, 'sample runs directly');
    assert.ok((await page.locator('.answer-point').first().textContent()).length < fixture(1).answer.points[0].text.length, 'answer reveals progressively');
    assert.equal(await page.evaluate(async () => (await TranscriptLensStore.load()).turns[0].status), 'complete', 'full result saved before reveal');
    await reload();
    assert.equal(calls, 1, 'reload never repeats completed requests');
    assert.equal(await page.locator('.answer-point').first().evaluate(el => el.firstChild.textContent), fixture(1).answer.points[0].text + ' ');
    assert.equal(await page.locator('[data-revealing]').count(), 0, 'restored responses skip animation');
    await page.locator('.citation-link').first().click();
    assert.equal(await page.locator('#source-1 pre').textContent(), fixture(1).sources[0].content);
    assert.equal(await page.locator('#sources img').count(), 0, 'untrusted source stays literal');
    await page.keyboard.press('Escape');
    await page.locator('.document').nth(1).click();
    await page.locator('#settings-button').click(); await page.locator('#top-k').selectOption('6');
    await page.keyboard.press('Escape');
    await page.locator('#question').fill('An unfinished draft');
    await saved(async () => (await TranscriptLensStore.load()).workspace.draft === 'An unfinished draft');
    await reload();
    assert.equal(await page.locator('#question').inputValue(), 'An unfinished draft');
    assert.equal(await page.locator('#top-k').inputValue(), '6');
    assert.equal(await page.locator('#model-choice').inputValue(), 'configured');
    assert.equal(await page.locator('#scope-label').textContent(), 'Synthetic session');
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await submit('A second independent question'); await ready();
    assert.equal(await page.locator('.answer-turn').count(), 2);
    await reload();
    await page.locator('.answer-turn').first().locator('.citation-link').first().click();
    assert.equal(await page.locator('#source-1 pre').textContent(), fixture(1).sources[0].content, 'old citations keep their original snapshot');
    await page.keyboard.press('Escape');
    await page.locator('#conversation-scroll').evaluate(el => { el.scrollTop = 20; });
    await saved(async () => (await TranscriptLensStore.load()).workspace.scrollTop === 20);
    await reload();
    assert.equal(await page.locator('#conversation-scroll').evaluate(el => el.scrollTop), 20, 'reading position restores');

    delay = 1500;
    const beforeInterrupted = calls;
    const interruptedRequest = page.waitForRequest(request => request.url().endsWith('/api/ask'));
    await submit('Interrupted request');
    await interruptedRequest;
    await saved(async () => (await TranscriptLensStore.load()).turns.some(turn => turn.status === 'pending'));
    const beforeReload = beforeInterrupted + 1;
    await reload();
    assert.equal(calls, beforeReload, 'interrupted request does not auto replay');
    assert.match(await page.locator('.answer-turn').last().textContent(), /interrupted/);
    delay = 10;
    await page.locator('.retry-turn').click(); await ready();
    assert.equal(calls, beforeReload + 1);
    assert.equal(await page.locator('.answer-turn').count(), 3, 'retry replaces original pending turn');

    fail = true;
    await submit('Failed request'); await ready();
    await reload(); assert.equal(await page.locator('.retry-turn').count(), 1);
    fail = false;
    await page.locator('.retry-turn').click(); await ready();
    assert.equal(await page.locator('.answer-turn').count(), 4);
    await page.locator('#model-choice').selectOption('sources');
    await submit('Sources only'); await ready(); await reload();
    assert.equal(await page.locator('.answer-turn').last().locator('.passage-card').count(), 1);

    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 800 }); await reload();
      assert.equal(await page.locator('.answer-turn').count(), 5);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `no overflow at ${width}`);
      const dock = await page.locator('.composer-dock').boundingBox();
      assert.ok(Math.abs(dock.y + dock.height - 800) < 2, `composer pinned at ${width}`);
    }
    await page.locator('#settings-button').click();
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#clear-history').click();
    await page.waitForFunction(() => document.querySelector('#welcome-state').hidden === false);
    await reload();
    assert.equal(await page.locator('.answer-turn').count(), 0);
    assert.equal(await page.locator('#document-count').textContent(), '1', 'clearing conversation keeps sessions');
    await page.route('**/static/workspace-store.js', route => route.fulfill({ contentType: 'application/javascript', body: `
      const unavailable = () => Promise.reject(new Error('Synthetic storage failure'));
      window.TranscriptLensStore = { load: unavailable, saveTurn: unavailable, saveWorkspace: unavailable, clear: unavailable };
    ` }));
    await reload();
    assert.match(await page.locator('#history-status').textContent(), /not being saved/);
    await submit('Storage unavailable'); await ready();
    assert.equal(await page.locator('.answer-turn').count(), 1, 'storage failure does not block answering');
    assert.deepEqual(errors, []);
    console.log('PASS: progressive reveal, refresh during reveal/loading, persistent drafts/preferences/citations, explicit retry, safe text, clear history, responsive composer.');
    await context.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
