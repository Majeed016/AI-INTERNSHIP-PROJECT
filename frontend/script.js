/* PaperCraft frontend – vanilla JS. Sections: 1) API module  2) helpers  3) form  4) rendering  5) actions */
'use strict';

/* ============ 1. API MODULE (the only code that talks to the backend) ============
 * Expected contracts (adjust here if the backend differs):
 * GET  /health          -> 200 { status: "ok" }
 * POST /generate-paper  body { subject, total_marks, difficulty:{easy,medium,hard},
 *                              question_types:{mcq,short_answer,long_answer}, topics:[{name,weight}] }
 *   -> { title, instructions:[str], total_marks, duration?,
 *        sections:[{ title, questions:[{ id, text, marks, topic, difficulty, type, options?:[str] }] }],
 *        distribution:{ difficulty:{easy:{requested,actual}}, topics:{Name:{requested,actual}},
 *                       question_types:{mcq:{requested,actual}} },   // percentages of total marks
 *        warnings?:[str | {message, suggestion?}] }
 * POST /swap-question   body { subject, question_id, config, paper }
 *   -> full updated paper (same shape as above) OR { question, distribution?, warnings? }
 * Errors: FastAPI style { detail: "msg" | [{msg}] | {message, warnings:[...]} }                         */
const API = (() => {
  const BASE = 'http://localhost:8000';
  class ApiError extends Error { constructor(msg, warnings = []) { super(msg); this.warnings = warnings; } }

  async function request(path, { method = 'GET', body, timeout = 30000 } = {}) {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), timeout);
    let res;
    try {
      res = await fetch(BASE + path, {
        method, signal: ctl.signal,
        headers: body ? { 'Content-Type': 'application/json', Accept: 'application/json' } : { Accept: 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (e) {
      throw new ApiError(e.name === 'AbortError'
        ? 'The backend took too long to respond. Try again.'
        : 'Cannot reach the backend at ' + BASE + '. Start the FastAPI server and make sure CORS allows this page.');
    } finally { clearTimeout(timer); }

    let data = null;
    try { data = await res.json(); } catch { /* handled below */ }
    if (!res.ok) {
      const d = data && data.detail !== undefined ? data.detail : data;
      let msg = `Request failed (HTTP ${res.status}).`, warnings = [];
      if (typeof d === 'string') msg = d;
      else if (Array.isArray(d)) msg = d.map(x => x.msg || JSON.stringify(x)).join('; ');
      else if (d && typeof d === 'object') { msg = d.message || d.error || msg; warnings = d.warnings || d.explanations || []; }
      throw new ApiError(msg, warnings);
    }
    if (data === null || typeof data !== 'object') throw new ApiError('The backend returned an invalid (non-JSON) response.');
    return data;
  }

  const validPaper = p => p && Array.isArray(p.sections) && p.sections.every(s => Array.isArray(s.questions));
  const need = p => { if (!validPaper(p)) throw new ApiError('The backend response is missing a valid "sections" list.'); return p; };

  return {
    BASE,
    health: () => request('/health', { timeout: 4000 }),
    generatePaper: async cfg => need(await request('/generate-paper', { method: 'POST', body: cfg })),
    swapQuestion: async payload => {
      const r = await request('/swap-question', { method: 'POST', body: payload });
      if (!validPaper(r) && !(r.question && r.question.text)) throw new ApiError('The backend returned an unrecognised swap response.');
      return r;
    },
  };
})();

/* ============ 2. HELPERS ============ */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
function h(tag, props = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'class') e.className = v; else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v);
  }
  kids.flat().forEach(c => c != null && e.append(c.nodeType ? c : document.createTextNode(c)));
  return e;
}
const num = v => (v === '' || v == null ? NaN : Number(v));
const pretty = k => String(k).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
const TYPE_LABEL = { mcq: 'MCQ', short_answer: 'Short answer', long_answer: 'Long answer' };

const DEFAULT_TOPICS = {
  maths: [['Algebra', 30], ['Geometry', 25], ['Trigonometry', 20], ['Statistics', 25]],
  science: [['Physics', 35], ['Chemistry', 35], ['Biology', 30]],
};
const state = { paper: null, config: null };

/* ============ 3. FORM ============ */
function addTopic(name = '', weight = '') {
  const row = h('div', { class: 'topic-row' },
    h('input', { type: 'text', 'aria-label': 'Topic name', placeholder: 'Topic name', value: name, maxlength: 60 }),
    h('input', { type: 'number', 'aria-label': 'Topic percentage', min: 0, max: 100, value: weight, placeholder: '%' }),
    h('button', { type: 'button', class: 'btn btn-ghost btn-icon', 'aria-label': 'Remove topic', onclick: () => { row.remove(); updateSums(); } }, '×'));
  $('#topics').append(row);
  updateSums();
}
function loadTopics(subject) {
  $('#topics').replaceChildren();
  DEFAULT_TOPICS[subject].forEach(([n, w]) => addTopic(n, w));
}
const sumOf = els => els.reduce((a, i) => a + (num(i.value) || 0), 0);
function groupInputs(g) { return g === 'topics' ? $$('.topic-row input[type=number]') : $$(`[data-group=${g}] input`); }

function updateSums() {
  $$('fieldset.group').forEach(fs => {
    const t = sumOf(groupInputs(fs.dataset.group));
    const el = $('.sum', fs);
    el.textContent = `Total: ${t}% ${t === 100 ? '✓' : '(must equal 100%)'}`;
    el.className = 'sum ' + (t === 100 ? 'ok' : 'bad');
  });
}

function readConfig() {
  const errors = {};
  const total = num($('#totalMarks').value);
  if (!Number.isInteger(total) || total < 1 || total > 500) errors.total = 'Enter a whole number of marks between 1 and 500.';

  const pcts = ids => Object.fromEntries(ids.map(([k, id]) => [k, num($('#' + id).value)]));
  const difficulty = pcts([['easy', 'd-easy'], ['medium', 'd-medium'], ['hard', 'd-hard']]);
  const question_types = pcts([['mcq', 't-mcq'], ['short_answer', 't-short'], ['long_answer', 't-long']]);
  const check = (obj, key) => {
    const v = Object.values(obj);
    if (v.some(x => Number.isNaN(x) || x < 0 || x > 100)) errors[key] = 'Each percentage must be a number from 0 to 100.';
    else if (v.reduce((a, b) => a + b, 0) !== 100) errors[key] = 'Percentages must add up to exactly 100%.';
  };
  check(difficulty, 'difficulty'); check(question_types, 'types');

  const topics = $$('.topic-row').map(r => { const [n, w] = $$('input', r); return { name: n.value.trim(), weight: num(w.value) }; });
  if (!topics.length) errors.topics = 'Add at least one topic.';
  else if (topics.some(t => !t.name)) errors.topics = 'Every topic needs a name.';
  else if (new Set(topics.map(t => t.name.toLowerCase())).size !== topics.length) errors.topics = 'Topic names must be unique.';
  else if (topics.some(t => Number.isNaN(t.weight) || t.weight < 0 || t.weight > 100)) errors.topics = 'Each topic percentage must be 0–100.';
  else if (topics.reduce((a, t) => a + t.weight, 0) !== 100) errors.topics = 'Topic percentages must add up to exactly 100%.';

  return { errors, config: { subject: $('#subject').value, total_marks: total, difficulty, question_types, topics } };
}

function showErrors(errors) {
  $('#err-total').textContent = errors.total || '';
  $('#totalMarks').setAttribute('aria-invalid', !!errors.total);
  $$('fieldset.group').forEach(fs => {
    const msg = errors[fs.dataset.group] || '';
    $('.err', fs).textContent = msg;
    $('.err', fs).setAttribute('role', msg ? 'alert' : 'none');
    $$('input', fs).forEach(i => i.setAttribute('aria-invalid', !!msg));
  });
  const first = $('[aria-invalid=true]');
  if (first) first.focus();
}

/* ============ 4. RENDERING ============ */
function showAlert(kind, title, items = []) {
  const box = h('div', { class: `alert ${kind}`, role: kind === 'error' ? 'alert' : 'status' },
    h('div', {}, h('strong', {}, title),
      items.length ? h('ul', {}, items.map(w => h('li', {}, typeof w === 'string' ? w : [w.message || JSON.stringify(w), w.suggestion ? ` Suggestion: ${w.suggestion}` : '']))) : null),
    h('button', { type: 'button', 'aria-label': 'Dismiss', onclick: () => box.remove() }, '×'));
  $('#alerts').append(box);
}
const clearAlerts = () => $('#alerts').replaceChildren();

function renderPaper() {
  const p = state.paper, c = state.config;
  $('#empty').hidden = true; $('#paperCard').hidden = false;
  let n = 0;
  const total = p.total_marks ?? p.sections.flatMap(s => s.questions).reduce((a, q) => a + (Number(q.marks) || 0), 0);
  const body = [
    h('h3', {}, p.title || `${pretty(c.subject)} Question Paper`),
    h('div', { class: 'paper-meta' }, h('span', {}, p.duration ? `Time: ${p.duration}` : pretty(c.subject)), h('span', {}, `Total marks: ${total}`)),
    p.instructions && p.instructions.length ? [h('strong', {}, 'Instructions'), h('ol', { class: 'instructions' }, p.instructions.map(i => h('li', {}, i)))] : null,
    p.sections.map(s => {
      const sm = s.questions.reduce((a, q) => a + (Number(q.marks) || 0), 0);
      return h('section', {}, h('h4', {}, h('span', {}, s.title || 'Section'), h('span', {}, `${sm} marks`)),
        s.questions.map(q => {
          n++;
          return h('div', { class: 'q', 'data-id': q.id },
            h('span', { class: 'q-num' }, n + '.'),
            h('div', {}, q.text, Array.isArray(q.options) && q.options.length ? h('ol', { class: 'opts' }, q.options.map(o => h('li', {}, o))) : null),
            h('span', { class: 'q-marks' }, `[${q.marks}]`),
            h('div', { class: 'q-meta no-print' },
              q.topic ? h('span', { class: 'tag' }, q.topic) : null,
              q.difficulty ? h('span', { class: 'tag' }, pretty(q.difficulty)) : null,
              q.type ? h('span', { class: 'tag' }, TYPE_LABEL[q.type] || pretty(q.type)) : null,
              h('button', { type: 'button', class: 'btn btn-ghost btn-sm', onclick: e => swapQuestion(q.id, e.currentTarget) },
                h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Replace question')));
        }));
    }),
  ];
  $('#paper').replaceChildren(...body.flat().filter(Boolean));
  renderReport(p.distribution);
}

function renderReport(dist) {
  const card = $('#reportCard'), box = $('#report');
  if (!dist || typeof dist !== 'object') {
    card.hidden = false;
    box.replaceChildren(h('p', { class: 'muted' }, 'The backend did not include a distribution report for this paper.'));
    return;
  }
  card.hidden = false;
  const groups = [['difficulty', 'Difficulty'], ['topics', 'Topics'], ['question_types', 'Question types']];
  box.replaceChildren(...groups.map(([key, title]) => {
    const data = dist[key] || (key === 'topics' ? dist.topic : null);
    if (!data) return null;
    const rows = Object.entries(data).map(([k, v]) => {
      const req = typeof v === 'object' ? Number(v.requested) : NaN, act = typeof v === 'object' ? Number(v.actual) : Number(v);
      const diff = act - req, abs = Math.abs(diff);
      const [cls, txt] = Number.isNaN(diff) ? ['warn', 'n/a'] : abs <= 0.5 ? ['ok', 'On target'] : abs <= 5 ? ['warn', 'Minor deviation'] : ['bad', 'Off target'];
      const f = x => (Number.isNaN(x) ? '–' : (+x.toFixed(1)) + '%');
      return h('tr', {}, h('td', {}, key === 'question_types' ? TYPE_LABEL[k] || pretty(k) : pretty(k)), h('td', {}, f(req)), h('td', {}, f(act)),
        h('td', {}, Number.isNaN(diff) ? '–' : (diff > 0 ? '+' : '') + (+diff.toFixed(1)) + ' pts'), h('td', {}, h('span', { class: 'badge ' + cls }, txt)));
    });
    return h('div', { class: 'rep-block' }, h('h3', {}, title),
      h('table', {}, h('thead', {}, h('tr', {}, ['Category', 'Requested', 'Actual', 'Difference', 'Status'].map(t => h('th', { scope: 'col' }, t)))), h('tbody', {}, rows)));
  }).filter(Boolean));
}

/* ============ 5. ACTIONS ============ */
function setLoading(btn, on, label) {
  btn.disabled = on; btn.classList.toggle('loading', on);
  const l = $('.label', btn); if (l && label) l.textContent = label;
}

function handleError(err, context) {
  showAlert('error', `${context}: ${err.message}`, err.warnings || []);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function generate(e) {
  e && e.preventDefault();

  const { errors, config } = readConfig();
  showErrors(errors);

  if (Object.keys(errors).length) return;

  clearAlerts();

  setLoading($('#generate'), true, 'Generating…');
  $('#regen').disabled = true;

  try {
    const paper = await API.generatePaper(config);

    state.paper = paper;
    state.config = config;

    renderPaper();

    $('#paperCard').scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });

  } catch (err) {
    handleError(err, 'Could not generate the paper');

  } finally {
    setLoading($('#generate'), false, 'Generate paper');
    $('#regen').disabled = false;
  }
}

async function swapQuestion(id, btn) {
  clearAlerts();
  const row = btn.closest('.q');
  btn.disabled = true; btn.classList.add('loading'); row.classList.add('swapping');
  try {
    const r = await API.swapQuestion({ subject: state.config.subject, question_id: id, config: state.config, paper: state.paper });
    if (r.sections) state.paper = r;
    else {
      state.paper.sections.forEach(s => { const i = s.questions.findIndex(q => q.id === id); if (i > -1) s.questions[i] = r.question; });
      if (r.distribution) state.paper.distribution = r.distribution;
    }
    renderPaper();
    if (r.warnings && r.warnings.length) showAlert('warn', 'Replacement notes from the backend', r.warnings);
  } catch (err) {
    btn.disabled = false; btn.classList.remove('loading'); row.classList.remove('swapping');
    handleError(err, 'Could not replace the question');
  }
}

async function checkHealth() {
  const chip = $('#health');
  try {
    const r = await API.health();
    chip.textContent = r.status && r.status !== 'ok' ? `Backend: ${r.status}` : 'Backend online';
    chip.className = 'chip ' + (!r.status || r.status === 'ok' ? 'chip-ok' : 'chip-bad');
  } catch (err) {
    chip.textContent = 'Backend offline'; chip.className = 'chip chip-bad'; chip.title = err.message;
  }
}

/* ============ INIT ============ */
document.addEventListener('DOMContentLoaded', () => {
  loadTopics($('#subject').value);
  $('#subject').addEventListener('change', e => { loadTopics(e.target.value); state.paper = null; });
  $('#addTopic').addEventListener('click', () => { addTopic(); $$('.topic-row input[type=text]').pop().focus(); });
  $('#config').addEventListener('input', updateSums);
  $('#config').addEventListener('submit', generate);
  $('#regen').addEventListener('click', generate);
  $('#print').addEventListener('click', () => window.print());
  updateSums(); checkHealth(); setInterval(checkHealth, 30000);
});