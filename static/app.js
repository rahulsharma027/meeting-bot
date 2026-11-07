/* DOM text nodes are intentional: transcript/model text is never trusted HTML. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  let state = { documents: [], selected: '', configured: false, busy: false, filter: '' };
  const desktop = matchMedia('(min-width: 1024px)');
  $('library-panel').open = desktop.matches;
  desktop.addEventListener('change', event => { $('library-panel').open = event.matches; });
  const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  const icon = (name) => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'icon'); svg.setAttribute('aria-hidden', 'true');
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', `#icon-${name}`); svg.append(use);
    return svg;
  };
  function message(text, error = false) {
    $('notice').hidden = true;
    $('error').hidden = true;
    if (text) { const box = $(error ? 'error' : 'notice'); box.textContent = text; box.hidden = false; }
  }
  function controls() {
    const generate = $('generate').checked;
    $('search-button-label').textContent = state.busy ? 'Working…' : generate ? 'Generate answer' : 'Find passages';
    $('question-form').setAttribute('aria-busy', String(state.busy));
    $('search-button').disabled = state.busy;
    $('notes-button').disabled = state.busy || !state.selected || !state.configured;
    $('generate').disabled = !state.configured || state.busy;
    $('transcript-file').disabled = state.busy;
    if ($('index-button')) $('index-button').disabled = state.busy;
    for (const id of ['mode', 'top-k', 'question', 'library-search']) $(id).disabled = state.busy;
    document.querySelectorAll('.document, [data-question]').forEach(el => { el.disabled = state.busy; });
    const doc = state.documents.find(d => d.id === state.selected);
    $('scope-label').textContent = doc ? doc.title : 'Across all sessions';
  }
  async function request(url, payload) {
    const token = document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1];
    const isForm = payload instanceof FormData;
    const response = await fetch(url, { method: 'POST', credentials: 'same-origin',
      headers: { 'X-CSRFToken': token || '', ...(isForm ? {} : { 'Content-Type': 'application/json' }) },
      body: isForm ? payload : JSON.stringify(payload) });
    let data;
    try { data = await response.json(); } catch { throw new Error('The server returned an unreadable response. Reload and try again.'); }
    if (!response.ok) throw new Error(data.error || 'The request failed.');
    return data;
  }
  async function operation(work) {
    if (state.busy) return;
    state.busy = true; message(''); controls();
    try { await work(); }
    catch (error) { message(error.message || 'The request failed.', true); }
    finally { state.busy = false; controls(); }
  }
  function renderLibrary() {
    const list = $('documents'); list.replaceChildren();
    function entry(title, id, doc) {
      const button = node('button', undefined, `document${id === state.selected ? ' selected' : ''}${id ? '' : ' all-sessions'}`);
      button.type = 'button'; button.setAttribute('aria-pressed', String(id === state.selected));
      const glyph = node('span', undefined, 'document-icon'); glyph.append(icon(doc ? 'lines' : 'pages'));
      const copy = node('span', undefined, 'doc-copy'); copy.append(node('strong', title));
      if (doc) {
        const meta = node('span', undefined, 'doc-meta');
        meta.append(node('span', `${doc.kind === 'lecture' ? 'Lecture' : 'Meeting'} · ${doc.session_date || 'Undated'}`), node('span', `${doc.chunks} ${doc.chunks === 1 ? 'passage' : 'passages'}`));
        copy.append(meta);
      }
      button.append(glyph, copy);
      button.addEventListener('click', () => {
        if (state.busy) return;
        state.selected = id; renderLibrary(); controls();
        if (!desktop.matches) $('library-panel').open = false;
        message(id ? `Selected: ${title}. Your next question will search this session.` : 'Your next question will search all sessions.');
      });
      list.append(button);
    }
    entry('All sessions', '');
    const filtered = state.documents.filter(d => d.title.toLocaleLowerCase().includes(state.filter));
    filtered.forEach(d => entry(d.title, d.id, d));
    $('library-empty').hidden = filtered.length > 0 || !state.filter;
    $('document-count').textContent = state.documents.length;
  }
  async function refresh() {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error('Could not load the local workspace.');
    const data = await response.json();
    state.documents = data.documents; state.configured = data.configured;
    $('setup-banner').hidden = data.configured;
    const total = data.documents.reduce((n, d) => n + d.chunks, 0);
    const indexed = data.documents.reduce((n, d) => n + (d.embedded || 0), 0);
    $('connection').textContent = data.configured ? `AI key configured · ${indexed}/${total} indexed` : 'Keyword search ready';
    $('connection').classList.toggle('offline', !data.configured);
    if (!$('index-button') && data.configured) {
      const button = node('button', 'Build semantic index', 'notes-button'); button.id = 'index-button'; button.type = 'button';
      button.addEventListener('click', () => operation(async () => {
        button.disabled = true;
        try {
          const data = await request('/api/index', {});
          await refresh();
          message(`Indexed ${data.saved} passages. ${data.remaining ? `${data.remaining} remain; click again to continue.` : 'The semantic index is ready.'}`);
        } finally { button.disabled = false; }
      }));
      $('documents').after(button);
    }
    for (const option of $('mode').options) option.disabled = option.value !== 'keyword' && (!data.configured || indexed < total);
    renderLibrary(); controls();
  }
  function renderSources(sources) {
    const target = $('sources'); target.replaceChildren(); $('source-count').textContent = sources.length;
    if (!sources.length) { target.append(node('p', 'No matching passages were found.', 'sources-help')); return; }
    sources.forEach((source, index) => {
      const article = node('article', undefined, 'source'); article.id = `source-${index + 1}`;
      const heading = node('div', undefined, 'source-heading');
      heading.append(node('span', String(index + 1).padStart(2, '0'), 'source-number'), node('h3', source.title));
      const meta = node('p', undefined, 'source-meta');
      meta.append(node('span', source.timestamp, 'source-time'), node('span', `${source.session_date || 'Undated'} · ${source.speakers.join(', ') || 'Speaker not stated'}`));
      article.append(heading, meta);
      const details = node('details'); details.open = sources.length <= 4 || index === 0;
      details.append(node('summary', `Read source · turns ${source.first_turn}–${source.last_turn}`), node('pre', source.content));
      article.append(details); target.append(article);
    });
  }
  function citations(parent, items, sources) {
    const indexes = new Map(sources.map((s, i) => [s.id, i + 1]));
    for (const citation of items) {
      const index = indexes.get(citation.id);
      const link = node('a', `[${index}]`, 'citation-link'); link.href = `#source-${index}`;
      link.setAttribute('aria-label', `Source ${index}: ${sources[index - 1].title}`);
      link.title = citation.quote;
      link.addEventListener('click', () => { const details = $(`source-${index}`).querySelector('details'); if (details) details.open = true; });
      parent.append(link);
    }
  }
  function renderTrace(result) {
    const el = $('trace-content'); el.replaceChildren();
    const grid = node('div', undefined, 'trace-grid');
    const descriptions = [
      ['Retrieval', `${result.mode} · ${result.sources.length} passages. Scores are ranking signals, not answer confidence.`],
      ['Models', Object.entries(result.models).filter(([, v]) => v).map(([k, v]) => `${k}: ${v}`).join(' · ') || 'No model called.'],
      ['Timing', Object.entries(result.timings_ms).map(([k, v]) => `${k}: ${v} ms`).join(' · ')],
    ];
    descriptions.forEach(([name, value]) => { const box = node('div'); box.append(node('strong', name), node('span', value)); grid.append(box); });
    el.append(grid);
    const usage = result.usage;
    if (usage && Object.keys(usage).length) el.append(node('p', `Provider-reported generation tokens: input ${usage.promptTokenCount ?? 'not reported'} · output ${usage.candidatesTokenCount ?? 'not reported'} · thinking ${usage.thoughtsTokenCount ?? 'not reported'}. Monetary cost is not calculated.`));
    const ranking = node('ol', undefined, 'trace-list');
    result.sources.forEach(s => ranking.append(node('li', `${s.id} · score ${s.score ?? 'not ranked'} · keyword rank ${s.keyword_rank ?? '—'} · semantic rank ${s.semantic_rank ?? '—'}`)));
    el.append(ranking);
  }
  function renderResult(result, heading) {
    $('result-heading').textContent = heading;
    $('result-label').textContent = result.generated ? 'AI draft · review sources' : 'Source search · no generated answer';
    const target = $('answer-content'); target.replaceChildren();
    const answer = result.answer;
    if (!answer) target.append(node('p', `${result.sources.length} source passages retrieved. Read them alongside this panel, or connect AI to generate a cited answer.`, 'search-summary'));
    else if (answer.status === 'insufficient') target.append(node('p', 'The selected transcript passages do not contain enough information to answer this question. Try another session or a more specific question.', 'no-answer'));
    else {
      target.append(node('p', result.mode === 'whole-transcript notes' ? 'Session notes' : 'From your sessions', 'answer-kind'));
      answer.points.forEach(point => { const p = node('p', point.text + ' ', 'answer-point'); citations(p, point.citations, result.sources); target.append(p); });
      if (answer.actions.length) target.append(node('h3', 'Action items'));
      answer.actions.forEach(action => {
        const box = node('div', undefined, 'action-item'); box.append(node('strong', action.task));
        box.append(node('p', `Owner: ${action.owner || 'Not stated'} · Due: ${action.due_date || 'Not stated'}`));
        citations(box, action.citations, result.sources); target.append(box);
      });
      target.append(node('p', 'Source IDs and exact quotes were checked. Claim accuracy, ownership, and deadline interpretation still need your review.', 'answer-warning'));
    }
    renderSources(result.sources); renderTrace(result);
  }
  $('generate').addEventListener('change', controls);
  $('library-search').addEventListener('input', event => {
    state.filter = event.target.value.trim().toLocaleLowerCase(); renderLibrary(); controls();
  });
  document.querySelectorAll('a[href="#how-it-works"], a[href="#model-setup"]').forEach(link => {
    link.addEventListener('click', () => { $('how-it-works').open = true; });
  });
  document.querySelectorAll('.view-nav a').forEach(link => link.addEventListener('click', () => {
    document.querySelectorAll('.view-nav a').forEach(item => { item.classList.remove('active'); item.removeAttribute('aria-current'); });
    link.classList.add('active'); link.setAttribute('aria-current', 'location');
  }));
  $('question-form').addEventListener('submit', event => {
    event.preventDefault(); operation(async () => {
      const result = await request('/api/ask', { question: $('question').value.trim(), mode: $('mode').value,
        top_k: Number($('top-k').value), document_id: state.selected, generate: $('generate').checked });
      renderResult(result, $('generate').checked ? 'Your answer' : 'What the sources say');
      $('result-heading').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
    });
  });
  $('notes-button').addEventListener('click', () => operation(async () => {
    const result = await request('/api/notes', { document_id: state.selected });
    renderResult(result, 'Notes worth keeping');
  }));
  document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => {
    $('question').value = button.dataset.question; $('question').focus();
  }));
  $('transcript-file').addEventListener('change', () => operation(async () => {
    const file = $('transcript-file').files[0]; if (!file) return;
    if (file.size > 2_000_000) throw new Error('Use a transcript file smaller than 2 MB.');
    const data = new FormData(); data.append('file', file);
    const result = await request('/api/upload', data); state.selected = result.id;
    await refresh(); $('transcript-file').value = '';
    message(result.created ? 'Transcript added. Keyword search is ready. Build the semantic index to include it in semantic and hybrid search.' : 'This transcript is already in your library; the existing copy was selected.');
  }));
  refresh().catch(error => message(error.message, true));
})();
