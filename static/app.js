/* Transcript and model text is untrusted: render it through text nodes only. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const desktop = matchMedia('(min-width: 1024px)');
  const state = { documents: [], selected: '', configured: false, generationModel: '', useAI: false, busy: false, loading: true, filter: '', lastResult: null, retry: null, turns: new Map(), storageFailed: false };
  let workspaceSaveTimer, pendingWorkspace, modelReturnFocus;
  $('library-panel').open = desktop.matches;
  desktop.addEventListener('change', event => { $('library-panel').open = event.matches; });
  const node = (tag, text, className) => {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    return el;
  };
  function scrollToLatest() {
    $('conversation-scroll').scrollTo({ top: $('conversation-scroll').scrollHeight, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }
  function workspaceSnapshot() {
    const viewport = $('conversation-scroll');
    return { version: 1, selected: state.selected, draft: $('question').value, mode: $('mode').value, topK: $('top-k').value,
      useAI: state.useAI, generationModel: state.generationModel, scrollTop: viewport.scrollTop,
      followLatest: viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 72 };
  }
  function storageFailure() {
    $('history-status').textContent = 'History is not being saved in this browser.';
    if (!state.storageFailed) message('Conversation could not be saved in this browser.', true);
    state.storageFailed = true;
  }
  async function persistTurn(record) {
    try { await window.TranscriptLensStore.saveTurn(record, workspaceSnapshot()); }
    catch { storageFailure(); }
  }
  function scheduleWorkspaceSave() {
    if (state.loading) return;
    clearTimeout(workspaceSaveTimer);
    pendingWorkspace = workspaceSnapshot();
    workspaceSaveTimer = setTimeout(() => {
      const snapshot = pendingWorkspace; pendingWorkspace = null;
      window.TranscriptLensStore.saveWorkspace(snapshot).catch(storageFailure);
    }, 150);
  }
  function saveWorkspaceNow() {
    if (state.loading) return;
    clearTimeout(workspaceSaveTimer); pendingWorkspace = null;
    window.TranscriptLensStore.saveWorkspace(workspaceSnapshot()).catch(storageFailure);
  }
  function validStoredTurn(record) {
    if (record?.version !== 1 || typeof record.id !== 'string' || !/^turn-[a-f0-9-]+$/.test(record.id) || !Number.isFinite(record.createdAt)) return false;
    if (!['pending', 'failed', 'complete'].includes(record.status) || typeof record.heading !== 'string') return false;
    if (!record.context || !['question', 'notes'].includes(record.context.type) || !['question', 'scopeLabel', 'sessionId'].every(k => typeof record.context[k] === 'string')) return false;
    if (!record.request || !['ask', 'notes'].includes(record.request.kind) || !record.request.payload || typeof record.request.payload !== 'object') return false;
    if (record.status !== 'complete') return true;
    const result = record.result;
    if (!result || !Array.isArray(result.sources) || !result.models || !result.timings_ms) return false;
    if (!result.sources.every(s => s && ['id', 'title', 'content', 'timestamp'].every(k => typeof s[k] === 'string') && Array.isArray(s.speakers))) return false;
    if (!result.answer) return true;
    const answer = result.answer, ids = new Set(result.sources.map(s => s.id));
    return ['answered', 'insufficient'].includes(answer.status) && Array.isArray(answer.points) && Array.isArray(answer.actions) &&
      [...answer.points, ...answer.actions].every(entry => entry && typeof (entry.text ?? entry.task) === 'string' && Array.isArray(entry.citations) && entry.citations.every(c => c && ids.has(c.id) && typeof c.quote === 'string'));
  }

  function openSettings() {
    if (!$('settings-dialog').open) $('settings-dialog').showModal();
    $('settings-feedback').hidden = true;
  }

  function openModelSetup(reason = '') {
    if (!$('model-dialog').open) modelReturnFocus = $('settings-dialog').open ? $('settings-button') : $('model-choice');
    if ($('settings-dialog').open) $('settings-dialog').close();
    $('model-feedback').textContent = reason;
    $('model-feedback').hidden = !reason;
    if (!$('model-dialog').open) $('model-dialog').showModal();
    $('model-dialog').querySelector('.settings-body').scrollTop = 0;
  }

  function message(text, error = false) {
    $('notice').hidden = true; $('error').hidden = true;
    const feedback = $('model-dialog').open ? $('model-feedback') : $('settings-dialog').open ? $('settings-feedback') : null;
    if (feedback) {
      feedback.textContent = text;
      feedback.hidden = !text;
      return;
    }
    if (!text) return;
    if (error) {
      $('error-message').textContent = text;
      $('retry-button').hidden = !state.retry;
      $('error').hidden = false;
    } else { $('notice').textContent = text; $('notice').hidden = false; }
  }

  function controls() {
    const locked = state.busy || state.loading;
    const generate = state.useAI && state.configured;
    $('search-button-label').textContent = state.busy ? 'Working…' : 'Send';
    $('question-form').setAttribute('aria-busy', String(locked));
    $('search-button').disabled = locked;
    $('notes-button').hidden = !state.selected;
    $('notes-button').disabled = locked;
    $('model-choice').disabled = locked;
    $('model-refresh').disabled = locked;
    $('model-choice').value = generate ? 'configured' : 'sources';
    $('transcript-file').disabled = locked;
    $('library-import').disabled = locked;
    $('clear-history').disabled = locked || !state.turns.size;
    if ($('index-button')) $('index-button').disabled = locked;
    for (const id of ['mode', 'top-k', 'question', 'library-search']) $(id).disabled = locked;
    document.querySelectorAll('.document, [data-question], .retry-turn').forEach(el => { el.disabled = locked; });
    const doc = state.documents.find(d => d.id === state.selected);
    $('scope-label').textContent = doc ? doc.title : 'All sessions';
    $('notes-hint').textContent = !state.selected ? 'Select a session to make notes.' : !state.configured ? 'Connect a model to make notes.' : 'Uses Gemini; sends the selected transcript.';
    const cloudHint = generate ? 'Uses cloud AI · sends your question and selected passages.' : state.configured && $('mode').value !== 'keyword' ? 'Cloud search sends your question to Gemini.' : '';
    $('ai-disclosure').textContent = cloudHint;
    $('ai-disclosure').hidden = !cloudHint;
    $('options-summary').textContent = `${$('mode').selectedOptions[0].textContent.replace(' search', '')} · ${$('top-k').value} passages`;
  }

  async function request(url, payload) {
    const token = document.cookie.split('; ').find(c => c.startsWith('csrftoken='))?.split('=')[1];
    const isForm = payload instanceof FormData;
    const response = await fetch(url, { method: 'POST', credentials: 'same-origin',
      headers: { 'X-CSRFToken': token || '', ...(isForm ? {} : { 'Content-Type': 'application/json' }) },
      body: isForm ? payload : JSON.stringify(payload) });
    let data;
    try { data = await response.json(); } catch { throw new Error('Could not read the response. Try again.'); }
    if (!response.ok) throw new Error(data.error || 'The request failed.');
    return data;
  }

  async function operation(work, label = 'Searching…', showStatus = true) {
    if (state.busy || state.loading) return;
    const previousFocus = document.activeElement;
    state.busy = true; state.retry = null; message(''); controls();
    $('operation-status').textContent = label; $('operation-status').hidden = !showStatus;
    scrollToLatest();
    if ($('settings-dialog').open || $('model-dialog').open) message(label);
    try { await work(); }
    catch (error) { state.retry = () => operation(work, label, showStatus); message(error.message || 'The request failed.', true); }
    finally {
      state.busy = false; controls(); $('operation-status').hidden = true;
      if (document.activeElement === document.body && previousFocus?.isConnected && !previousFocus.disabled) previousFocus.focus({ preventScroll: true });
    }
  }

  function renderLibrary() {
    const list = $('documents'); list.replaceChildren();
    function entry(title, id, doc) {
      const button = node('button', undefined, `document${id === state.selected ? ' selected' : ''}${id ? '' : ' all-sessions'}`);
      button.type = 'button'; button.setAttribute('aria-pressed', String(id === state.selected));
      button.append(node('strong', title));
      if (doc) button.append(node('span', doc.session_date || 'Undated', 'doc-meta'));
      button.addEventListener('click', event => {
        if (state.busy || state.loading) return;
        state.selected = id; renderLibrary(); controls();
        if (!desktop.matches) { $('library-panel').open = false; $('question').focus({ preventScroll: true }); }
        else if (event.detail === 0) list.querySelector('.selected').focus({ preventScroll: true });
        if (!state.retry) message('');
        saveWorkspaceNow();
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
    if (!response.ok) throw new Error('Could not load your sessions.');
    const data = await response.json();
    state.documents = data.documents; state.configured = data.configured; state.generationModel = data.generation_model;
    const modelOption = $('model-choice').querySelector('[value="configured"]');
    modelOption.disabled = !data.configured;
    modelOption.textContent = data.configured ? `Gemini · ${data.generation_model}` : 'Gemini · not connected';
    $('setup-banner').hidden = data.configured;
    $('configured-model').hidden = !data.configured;
    $('generation-model-name').textContent = data.generation_model;
    $('connection').textContent = data.configured ? 'API key configured' : 'No API key configured';
    $('model-status-hint').textContent = data.configured ? 'Choose Gemini in the composer to use AI answers.' : 'Add a key to use AI answers. Sources only is ready to use.';
    const total = data.documents.reduce((n, d) => n + d.chunks, 0);
    const indexed = data.documents.reduce((n, d) => n + (d.embedded || 0), 0);
    $('index-controls').hidden = !data.configured;
    $('index-summary').textContent = `${indexed} of ${total} passages indexed.`;
    if (!$('index-button') && data.configured) {
      const button = node('button', 'Build semantic index', 'quiet-button'); button.id = 'index-button'; button.type = 'button';
      button.addEventListener('click', () => operation(async () => {
        const result = await request('/api/index', {}); await refresh();
        message(result.remaining ? `${result.saved} passages indexed. ${result.remaining} remain; build again to continue.` : 'Semantic index ready.');
      }, 'Indexing…'));
      $('index-actions').append(button);
    }
    for (const option of $('mode').options) option.disabled = option.value !== 'keyword' && (!data.configured || indexed < total);
    if ($('mode').selectedOptions[0].disabled) $('mode').value = 'keyword';
    renderLibrary(); controls();
  }

  function renderSources(sources) {
    const target = $('sources'); target.replaceChildren();
    sources.forEach((source, index) => {
      const article = node('article', undefined, 'source'); article.id = `source-${index + 1}`; article.tabIndex = -1; article.hidden = true;
      article.setAttribute('aria-label', `Source ${index + 1}: ${source.title}`);
      article.append(node('h3', source.title));
      article.append(node('p', `${source.timestamp} · ${source.session_date || 'Undated'} · ${source.speakers.join(', ') || 'Speaker not stated'}`, 'source-meta'));
      article.append(node('pre', source.content)); target.append(article);
    });
  }

  function openSource(index, turnId) {
    const turn = state.turns.get(turnId);
    if (!turn) return;
    renderSources(turn.result.sources);
    const article = $(`source-${index}`);
    if (!article) return;
    $('sources').querySelectorAll('.source').forEach(item => { item.hidden = item !== article; });
    $('source-count').textContent = `Reference ${index} of ${$('sources').children.length}`;
    if (!$('source-dialog').open) $('source-dialog').showModal();
    article.focus({ preventScroll: true }); $('sources').scrollTop = 0;
  }

  function sourceLink(label, index, className, turnId) {
    const link = node('a', label, className); link.href = `#${turnId}-source-${index}`;
    link.addEventListener('click', event => { event.preventDefault(); openSource(index, turnId); });
    return link;
  }

  function citations(parent, items, sources, turnId) {
    const indexes = new Map(sources.map((s, i) => [s.id, i + 1]));
    for (const citation of items) {
      const index = indexes.get(citation.id);
      const link = sourceLink(`[${index}]`, index, 'citation-link', turnId);
      link.setAttribute('aria-label', `Open source ${index}: ${sources[index - 1].title}`);
      link.title = citation.quote; parent.append(link);
    }
  }

  function renderTrace(result) {
    const el = $('trace-content'); el.replaceChildren();
    const grid = node('div', undefined, 'trace-grid');
    const descriptions = [
      ['Question', state.lastResult.question || 'Session notes'], ['Scope', state.lastResult.scopeLabel],
      ['Retrieval', `${result.mode} · ${result.sources.length} passages`],
      ['Models', Object.entries(result.models).filter(([, v]) => v).map(([k, v]) => `${k}: ${v}`).join(' · ') || 'No model called.'],
      ['Timing', Object.entries(result.timings_ms).map(([k, v]) => `${k}: ${v} ms`).join(' · ')],
    ];
    descriptions.forEach(([name, value]) => { const box = node('div'); box.append(node('strong', name), node('span', value)); grid.append(box); });
    el.append(grid);
    if (result.usage && Object.keys(result.usage).length) el.append(node('p', `Provider-reported generation tokens: input ${result.usage.promptTokenCount ?? 'not reported'} · output ${result.usage.candidatesTokenCount ?? 'not reported'}.`));
    const ranking = node('ol', undefined, 'trace-list');
    result.sources.forEach(s => ranking.append(node('li', `${s.id} · score ${s.score ?? 'not ranked'} · keyword rank ${s.keyword_rank ?? '—'} · semantic rank ${s.semantic_rank ?? '—'}`)));
    el.append(ranking);
  }

  function turnShell(record) {
    const { id, heading, context } = record;
    document.querySelector('.results-layout').hidden = false;
    $('welcome-state').hidden = true;
    const wrapper = node('article', undefined, 'answer-turn'); wrapper.id = id;
    wrapper.append(node('p', context.question || 'Make notes for this session', 'user-question'));
    const header = node('div', undefined, 'turn-header');
    header.append(node('h3', heading), node('span', context.scopeLabel, 'turn-label'));
    wrapper.append(header);
    if ($(id)) $(id).replaceWith(wrapper); else $('answer-content').append(wrapper);
    return wrapper;
  }

  function renderIncomplete(record, active = false) {
    const wrapper = turnShell(record);
    wrapper.append(node('p', active ? 'Preparing your response…' : record.status === 'failed' ? 'The response could not be completed.' : 'This request was interrupted by a page reload.', 'reply-status'));
    wrapper.setAttribute('aria-busy', String(active));
    if (!active) {
      const retry = node('button', 'Retry question', 'quiet-button retry-turn'); retry.type = 'button';
      retry.addEventListener('click', () => runTurn(record)); wrapper.append(retry);
    }
  }

  // Presentation only: the complete server response is saved before revealing words.
  async function revealResponse(wrapper, target) {
    const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches || document.hidden;
    if (reduced()) return;
    const parts = [...target.children];
    const texts = parts.map(part => {
      const paragraph = part.matches('.answer-point, .no-answer') ? part : part.querySelector('.passage-excerpt');
      return paragraph?.firstChild?.nodeType === Node.TEXT_NODE ? paragraph.firstChild : null;
    });
    const originals = texts.map(text => text?.textContent || '');
    const total = originals.reduce((count, text) => count + (text.match(/\S+\s*/g) || []).length, 0);
    const batch = Math.max(1, Math.ceil(total / 42));
    const viewport = $('conversation-scroll');
    const update = work => {
      const follow = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 72;
      work();
      if (follow) viewport.scrollTop = viewport.scrollHeight;
    };
    wrapper.dataset.revealing = 'true'; wrapper.setAttribute('aria-busy', 'true');
    parts.forEach(part => { part.hidden = true; });
    try {
      for (let i = 0; i < parts.length; i++) {
        if (reduced()) break;
        const part = parts[i], text = texts[i], tokens = originals[i].match(/\S+\s*/g) || [];
        const refs = [...part.querySelectorAll('.citation-link')];
        update(() => { if (text) text.textContent = ''; part.hidden = false; refs.forEach(ref => { ref.hidden = true; }); });
        if (text) {
          text.parentElement.classList.add('is-revealing');
          for (let end = batch; end < tokens.length + batch; end += batch) {
            if (reduced()) break;
            update(() => { text.textContent = tokens.slice(0, end).join(''); });
            await new Promise(resolve => setTimeout(resolve, 30));
          }
          update(() => { text.textContent = originals[i]; text.parentElement.classList.remove('is-revealing'); });
        } else await new Promise(resolve => setTimeout(resolve, 80));
        update(() => refs.forEach(ref => { ref.hidden = false; }));
      }
    } finally {
      update(() => parts.forEach((part, index) => {
        part.hidden = false;
        if (texts[index]) { texts[index].textContent = originals[index]; texts[index].parentElement.classList.remove('is-revealing'); }
        part.querySelectorAll('.citation-link').forEach(ref => { ref.hidden = false; });
      }));
      delete wrapper.dataset.revealing; wrapper.setAttribute('aria-busy', 'false');
    }
  }

  async function renderResult(record, reveal = false) {
    const { result, heading, context, id: turnId } = record;
    const viewport = $('conversation-scroll');
    const follow = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 72;
    state.lastResult = context;
    const wrapper = turnShell(record);
    if (result.generated) wrapper.append(node('p', 'AI draft · review sources', 'turn-label'));
    const target = node('div', undefined, 'turn-body'); wrapper.append(target);
    const answer = result.answer;
    if (!answer) {
      if (!result.sources.length) target.append(node('p', 'No matches. Try another phrase or session.', 'no-answer'));
      result.sources.forEach((source, index) => {
        const card = node('article', undefined, 'passage-card');
        const link = sourceLink(undefined, index + 1, 'passage-link', turnId);
        link.setAttribute('aria-label', `Open source ${index + 1}: ${source.title}`);
        link.append(node('span', source.title), node('span', '↗', 'passage-arrow'));
        card.append(link, node('p', `${source.timestamp} · ${source.session_date || 'Undated'}`, 'passage-meta'));
        const shortened = source.content.length > 240;
        const excerpt = shortened ? source.content.slice(0, 240).replace(/\s+\S*$/, '') + '…' : source.content;
        card.append(node('p', excerpt, 'passage-excerpt')); target.append(card);
      });
    } else if (answer.status === 'insufficient') target.append(node('p', 'These transcripts do not contain enough information to answer.', 'no-answer'));
    else {
      let more;
      answer.points.forEach((point, index) => {
        const p = node('p', point.text + ' ', 'answer-point'); citations(p, point.citations, result.sources, turnId);
        if (index < 2) target.append(p);
        else {
          if (!more) { more = node('details', undefined, 'answer-more'); more.append(node('summary', 'More detail')); target.append(more); }
          more.append(p);
        }
      });
      if (answer.actions.length) {
        const actions = node('details', undefined, 'answer-more'); actions.append(node('summary', `Action items (${answer.actions.length})`));
        answer.actions.forEach(action => {
          const box = node('div', undefined, 'action-item'); box.append(node('strong', action.task));
          box.append(node('p', `Owner: ${action.owner || 'Not stated'} · Due: ${action.due_date || 'Not stated'}`));
          citations(box, action.citations, result.sources, turnId); actions.append(box);
        });
        target.append(actions);
      }
    }
    renderTrace(result);
    if (reveal && follow) viewport.scrollTop = viewport.scrollHeight;
    if (reveal) await revealResponse(wrapper, target);
  }

  function newTurn(kind, payload, context, heading) {
    return { version: 1, id: `turn-${crypto.randomUUID()}`, createdAt: Date.now(), status: 'pending', heading, context, request: { kind, payload } };
  }

  function runTurn(record) {
    if (record.request.kind === 'notes' || record.request.payload.generate) {
      if (!state.configured) { openModelSetup('Add a Gemini API key to retry this request.'); return; }
    }
    return operation(async () => {
      if (record.status === 'complete') { await renderResult(record); return; }
      record.status = 'pending'; state.turns.set(record.id, record);
      if (record.context.type === 'question' && $('question').value.trim() === record.context.question) {
        $('question').value = ''; $('question').style.height = '';
      }
      renderIncomplete(record, true); scrollToLatest();
      await persistTurn(record);
      try {
        record.result = await request(`/api/${record.request.kind}`, record.request.payload);
        record.status = 'complete';
        await persistTurn(record);
        await renderResult(record, true);
        scheduleWorkspaceSave();
      } catch (error) {
        if (record.status !== 'complete') {
          record.status = 'failed'; await persistTurn(record); renderIncomplete(record);
        }
        throw error;
      }
    }, 'Preparing your response…', false);
  }

  async function initialize() {
    state.loading = true; controls();
    try {
      const [, saved] = await Promise.all([refresh(), window.TranscriptLensStore.load().catch(() => { storageFailure(); return { turns: [], workspace: null }; })]);
      const workspace = saved.workspace;
      if (workspace?.version === 1) {
        state.selected = state.documents.some(doc => doc.id === workspace.selected) ? workspace.selected : '';
        if ([...$('mode').options].some(option => option.value === workspace.mode && !option.disabled)) $('mode').value = workspace.mode;
        if (['2', '4', '6'].includes(workspace.topK)) $('top-k').value = workspace.topK;
        state.useAI = workspace.useAI === true && state.configured && workspace.generationModel === state.generationModel;
        if (typeof workspace.draft === 'string') $('question').value = workspace.draft.slice(0, 1000);
      }
      $('answer-content').setAttribute('aria-live', 'off');
      const turns = saved.turns.filter(validStoredTurn).sort((a, b) => a.createdAt - b.createdAt || a.id.localeCompare(b.id));
      for (const record of turns) {
        state.turns.set(record.id, record);
        if (record.status === 'complete') await renderResult(record); else renderIncomplete(record);
      }
      if (turns.length !== saved.turns.length) message('Some saved responses could not be restored.', true);
      renderLibrary();
      await document.fonts.ready;
      const viewport = $('conversation-scroll');
      viewport.scrollTop = workspace?.followLatest !== false ? viewport.scrollHeight : Math.max(0, Number(workspace.scrollTop) || 0);
      $('question').style.height = `${Math.min($('question').scrollHeight, 144)}px`;
    } catch (error) {
      state.retry = initialize; message(error.message || 'Could not restore your workspace.', true);
    } finally {
      state.loading = false; controls();
      $('answer-content').setAttribute('aria-live', 'polite');
    }
  }

  $('settings-button').addEventListener('click', () => openSettings());
  $('privacy-button').addEventListener('click', () => {
    $('privacy-dialog').showModal();
    $('privacy-dialog').querySelector('.settings-body').scrollTop = 0;
  });
  $('open-model-setup').addEventListener('click', () => openModelSetup());
  $('model-dialog').addEventListener('close', () => {
    if (modelReturnFocus?.isConnected && !modelReturnFocus.disabled) modelReturnFocus.focus({ preventScroll: true });
  });
  $('model-refresh').addEventListener('click', () => operation(async () => {
    await refresh();
    message(state.configured ? 'API key found. You can now choose Gemini in the composer.' : 'No API key found. Save your key in .env and restart the app, then check again.');
  }, 'Checking local configuration…'));
  document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => $(button.dataset.close).close()));
  for (const dialog of [$('settings-dialog'), $('model-dialog'), $('privacy-dialog')]) {
    let backdropPress = false;
    const outside = event => {
      const rect = dialog.getBoundingClientRect();
      return event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom);
    };
    dialog.addEventListener('pointerdown', event => { backdropPress = event.isPrimary && event.button === 0 && outside(event); });
    dialog.addEventListener('click', event => {
      const dismiss = backdropPress && outside(event); backdropPress = false;
      if (dismiss) dialog.close();
    });
    dialog.addEventListener('pointercancel', () => { backdropPress = false; });
    dialog.addEventListener('close', () => { backdropPress = false; });
  }
  $('model-choice').addEventListener('change', () => {
    if ($('model-choice').value === 'setup') { openModelSetup(); controls(); return; }
    state.useAI = $('model-choice').value === 'configured'; controls(); saveWorkspaceNow();
  });
  for (const id of ['mode', 'top-k']) $(id).addEventListener('change', () => { controls(); saveWorkspaceNow(); });
  $('question').addEventListener('input', () => { $('question').style.height = 'auto'; $('question').style.height = `${Math.min($('question').scrollHeight, 144)}px`; controls(); saveWorkspaceNow(); });
  $('question').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); $('question-form').requestSubmit(); }
  });
  $('library-import').addEventListener('click', () => $('transcript-file').click());
  document.addEventListener('pointerdown', event => {
    if (!desktop.matches && !event.target.closest('.library')) $('library-panel').open = false;
  });
  $('retry-button').addEventListener('click', () => { if (state.retry) state.retry(); });
  $('library-search').addEventListener('input', event => { state.filter = event.target.value.trim().toLocaleLowerCase(); renderLibrary(); controls(); });
  $('question-form').addEventListener('submit', event => {
    event.preventDefault();
    if (state.busy || state.loading || !$('question').value.trim()) return;
    const payload = { question: $('question').value.trim(), mode: $('mode').value, top_k: Number($('top-k').value), document_id: state.selected, generate: state.useAI && state.configured };
    const context = { sessionId: state.selected, scopeLabel: state.documents.find(d => d.id === state.selected)?.title || 'All sessions', question: payload.question, type: 'question' };
    runTurn(newTurn('ask', payload, context, payload.generate ? 'Answer' : 'Results'));
  });
  $('notes-button').addEventListener('click', () => {
    if (!state.configured) { openModelSetup('Add a Gemini API key to make session notes.'); return; }
    $('settings-dialog').close();
    const selected = state.selected;
    const context = { sessionId: selected, scopeLabel: state.documents.find(d => d.id === selected)?.title || 'Selected session', question: '', type: 'notes' };
    runTurn(newTurn('notes', { document_id: selected }, context, 'Session notes'));
  });
  $('sample-question').addEventListener('click', () => { $('question').value = $('sample-question').dataset.question; controls(); $('question-form').requestSubmit(); });
  $('transcript-file').addEventListener('change', () => operation(async () => {
    const file = $('transcript-file').files[0]; if (!file) return;
    if (file.size > 2_000_000) throw new Error('Use a transcript smaller than 2 MB.');
    const data = new FormData(); data.append('file', file);
    const result = await request('/api/upload', data); state.selected = result.id;
    await refresh(); $('transcript-file').value = '';
    scheduleWorkspaceSave();
    message(result.created ? 'Transcript imported.' : 'Already imported. Selected the existing session.');
  }, 'Importing…'));
  $('conversation-scroll').addEventListener('scroll', scheduleWorkspaceSave, { passive: true });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && !state.loading && pendingWorkspace) {
      clearTimeout(workspaceSaveTimer);
      const snapshot = pendingWorkspace; pendingWorkspace = null;
      window.TranscriptLensStore.saveWorkspace(snapshot).catch(storageFailure);
    }
  });
  $('clear-history').addEventListener('click', async () => {
    if (state.busy || state.loading || !confirm('Clear saved questions and responses from this browser? Imported transcripts will stay.')) return;
    clearTimeout(workspaceSaveTimer);
    pendingWorkspace = null;
    state.busy = true; controls();
    try {
      await window.TranscriptLensStore.clear({ ...workspaceSnapshot(), draft: '', scrollTop: 0, followLatest: true });
      state.turns.clear(); state.lastResult = null; state.retry = null;
      $('answer-content').replaceChildren(); $('trace-content').replaceChildren(); $('sources').replaceChildren();
      $('question').value = ''; $('question').style.height = '';
      document.querySelector('.results-layout').hidden = true; $('welcome-state').hidden = false;
      message('Conversation cleared. Your transcripts are still available.');
    } catch { storageFailure(); }
    finally { state.busy = false; controls(); }
  });
  initialize();
})();
