/* ============================================================
   하베스터 OX 학습 — exam.js (vanilla JS, no build)
   Ported from Claude Design handoff (React/JSX → vanilla DOM).
   Architecture: Option C (Pragmatic Balance, single-file with sections)
   Source data: ../data/exam/*.json (exported by export_quiz_json.py --exam)
   ============================================================ */
'use strict';

/* ============================================================
   1) CONSTANTS · STATE · STORAGE
   ============================================================ */

const DATA_BASE = '../data/exam';

const TWEAK_DEFAULTS = {
  fontScale: 1,
  autoOpenSheet: true,
  feedbackStyle: 'flash',     // 'badge' | 'flash' | 'shake'
  oxPalette: ['#29b6f6', '#ef5350'],
};

const OX_PALETTES = [
  { name: '기본', value: ['#29b6f6', '#ef5350'] },
  { name: '교재', value: ['#1f8a5b', '#d04a3b'] },
  { name: '짙은청적', value: ['#3b6dd1', '#c0392b'] },
  { name: '딥', value: ['#0d8a8a', '#a83232'] },
  { name: '모노', value: ['#222222', '#888888'] },
];

const SUBJECT_COLORS = {
  '재정학': '#5B7B9A',
  '회계학개론': '#7B6B5B',
  '회계학': '#7B6B5B',
  '세법학개론': '#8A6B5B',
  '세법학': '#8A6B5B',
  '민법': '#6B5B7B',
  '상법': '#5B6B7B',
  '행정소송법': '#7B5B6B',
  '경제학': '#5B7B6B',
  '기본상식': '#7B7B5B',
};

const LS_KEYS = {
  tweaks: 'oxquiz.exam.tweaks',
  lastSession: 'oxquiz.exam.lastSession',
  daily: 'oxquiz.exam.daily',
  wrongNotes: 'oxquiz.exam.wrongNotes',
  bookmarks: 'oxquiz.exam.bookmarks',
  solvedLog: 'oxquiz.exam.solvedLog',
};
const SOLVED_LOG_MAX = 2000;  // LocalStorage 용량 관리

// 런타임 state
const state = {
  tweaks: { ...TWEAK_DEFAULTS },
  catalog: [],           // flat list of categories
  currentCategory: null, // full category JSON {category, questions, _meta}
  idx: 0,
  userAnswer: null,      // 'O' | 'X' | null
  history: [],           // [{id, statement, topic, userAnswer, correct}]
  sheetOpen: false,
  tagFilterPending: null,
};

function storeLoad(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch (e) {
    return fallback;
  }
}

function storeSave(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
}

function todayKey() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/* ============================================================
   2) UTILS · DOM HELPERS · GA4
   ============================================================ */

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return Array.from(document.querySelectorAll(sel)); }

function setText(sel, text) {
  const el = typeof sel === 'string' ? $(sel) : sel;
  if (el) el.textContent = text == null ? '' : String(text);
}

function setHidden(sel, hidden) {
  const el = typeof sel === 'string' ? $(sel) : sel;
  if (el) el.hidden = !!hidden;
}

function clear(el) {
  while (el && el.firstChild) el.removeChild(el.firstChild);
}

function elem(tag, attrs, children) {
  const e = document.createElement(tag);
  if (attrs) {
    for (const k in attrs) {
      if (k === 'class') e.className = attrs[k];
      else if (k === 'dataset') Object.assign(e.dataset, attrs[k]);
      else if (k === 'on') {
        for (const ev in attrs.on) e.addEventListener(ev, attrs.on[ev]);
      } else if (k === 'style' && typeof attrs[k] === 'object') {
        Object.assign(e.style, attrs[k]);
      } else if (k.startsWith('aria-') || k === 'role' || k === 'type' || k === 'href' || k === 'target' || k === 'rel') {
        e.setAttribute(k, attrs[k]);
      } else {
        e[k] = attrs[k];
      }
    }
  }
  if (children) {
    (Array.isArray(children) ? children : [children]).forEach((c) => {
      if (c == null || c === false) return;
      e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
  }
  return e;
}

function gaEvent(name, params) {
  try { if (window.gtag) window.gtag('event', name, params || {}); } catch (e) {}
}

function showToast(msg, ms = 1800) {
  const t = $('#toast');
  if (!t) return;
  t.textContent = msg;
  t.hidden = false;
  // force reflow then add open
  void t.offsetWidth;
  t.classList.add('is-open');
  clearTimeout(showToast._tm);
  showToast._tm = setTimeout(() => {
    t.classList.remove('is-open');
    setTimeout(() => { t.hidden = true; }, 240);
  }, ms);
}

/* ============================================================
   3) DATA LOADING — _index.json → flat catalog
   ============================================================ */

async function loadCatalog() {
  const res = await fetch(`${DATA_BASE}/_index.json`, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`_index.json fetch failed: ${res.status}`);
  const data = await res.json();
  const flat = [];
  for (const exam of (data.tree || [])) {
    for (const rd of (exam.rounds || [])) {
      for (const cat of (rd.categories || [])) {
        flat.push({
          slug: cat.slug,
          name: cat.name,
          subject: cat.subject,
          phase: cat.phase,
          exam_group: `${exam.exam} · ${rd.year}년 제${rd.round}회`,
          exam_year: rd.year,
          exam_round: rd.round,
          total: cat.total,
          with_full_meta: cat.with_full_meta || 0,
          color: SUBJECT_COLORS[cat.subject] || SUBJECT_COLORS[cat.name] || '#7B6B5B',
        });
      }
    }
  }
  return { flat, meta: data._meta || {} };
}

async function loadCategory(slug) {
  const res = await fetch(`${DATA_BASE}/${slug}.json`, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`${slug}.json fetch failed: ${res.status}`);
  return await res.json();
}

/* ============================================================
   4) DAILY STATS
   ============================================================ */

function loadDailyStats() {
  const today = todayKey();
  let d = storeLoad(LS_KEYS.daily, null);
  if (!d || d.date !== today) {
    // streak 계산: 어제도 풀이 있었으면 +1, 아니면 1
    const yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1);
    const yKey = `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`;
    const wasYesterday = d && d.date === yKey && d.solved > 0;
    d = {
      date: today,
      solved: 0, correct: 0,
      streak: wasYesterday ? (d.streak || 1) + 1 : 1,
    };
    storeSave(LS_KEYS.daily, d);
  }
  return d;
}

function recordDaily(correct) {
  const d = loadDailyStats();
  d.solved += 1;
  if (correct) d.correct += 1;
  storeSave(LS_KEYS.daily, d);
}

function dailyDisplay() {
  const d = loadDailyStats();
  const acc = d.solved ? Math.round(100 * d.correct / d.solved) : 0;
  return { solved: d.solved, accuracy: acc, streak: d.streak };
}

/* ============================================================
   5b) WRONG-NOTE STORE — LocalStorage 오답노트 (Plan FR-10, Design Component E)
   ============================================================ */

// 데이터 형식: { [categorySlug]: { qids: [123,456], updatedAt: ISO } }
function wrongStoreLoad() {
  return storeLoad(LS_KEYS.wrongNotes, {}) || {};
}
function wrongStoreSave(data) { storeSave(LS_KEYS.wrongNotes, data); }

function wrongAdd(catSlug, qid) {
  const all = wrongStoreLoad();
  const bucket = all[catSlug] || { qids: [], updatedAt: null };
  if (!bucket.qids.includes(qid)) {
    bucket.qids.push(qid);
    bucket.updatedAt = new Date().toISOString();
    all[catSlug] = bucket;
    wrongStoreSave(all);
    gaEvent('exam_wrong_added', { slug: catSlug, qid, total: bucket.qids.length });
  }
}
function wrongRemove(catSlug, qid) {
  const all = wrongStoreLoad();
  if (!all[catSlug]) return;
  all[catSlug].qids = all[catSlug].qids.filter((x) => x !== qid);
  all[catSlug].updatedAt = new Date().toISOString();
  if (all[catSlug].qids.length === 0) delete all[catSlug];
  wrongStoreSave(all);
}
function wrongList(catSlug) {
  return (wrongStoreLoad()[catSlug] || { qids: [] }).qids;
}
function wrongHas(catSlug, qid) {
  return wrongList(catSlug).includes(qid);
}
function wrongTotal() {
  const all = wrongStoreLoad();
  return Object.values(all).reduce((sum, b) => sum + (b.qids?.length || 0), 0);
}
function wrongTotalByCategory() {
  const all = wrongStoreLoad();
  const out = {};
  for (const slug in all) out[slug] = (all[slug].qids || []).length;
  return out;
}

// 가상 카테고리 slug — "오답만 풀기" 진입
const WRONG_VIRTUAL_SLUG = '__wrong_notes__';
const BOOKMARK_VIRTUAL_SLUG = '__bookmarks__';
const TAG_VIRTUAL_PREFIX = '__tag__:';
const SEARCH_VIRTUAL_PREFIX = '__search__:';

/* ============================================================
   5c) BOOKMARK STORE — 즐겨찾기 (Plan FR 확장)
   ============================================================ */
// 데이터 형식: { [categorySlug]: { qids: [123,456], updatedAt: ISO } }
function bookmarkStoreLoad() { return storeLoad(LS_KEYS.bookmarks, {}) || {}; }
function bookmarkStoreSave(d) { storeSave(LS_KEYS.bookmarks, d); }

function bookmarkAdd(catSlug, qid) {
  const all = bookmarkStoreLoad();
  const b = all[catSlug] || { qids: [], updatedAt: null };
  if (!b.qids.includes(qid)) {
    b.qids.push(qid);
    b.updatedAt = new Date().toISOString();
    all[catSlug] = b;
    bookmarkStoreSave(all);
    gaEvent('exam_bookmark_added', { slug: catSlug, qid });
  }
}
function bookmarkRemove(catSlug, qid) {
  const all = bookmarkStoreLoad();
  if (!all[catSlug]) return;
  all[catSlug].qids = all[catSlug].qids.filter((x) => x !== qid);
  all[catSlug].updatedAt = new Date().toISOString();
  if (all[catSlug].qids.length === 0) delete all[catSlug];
  bookmarkStoreSave(all);
}
function bookmarkHas(catSlug, qid) {
  return (bookmarkStoreLoad()[catSlug]?.qids || []).includes(qid);
}
function bookmarkTotal() {
  const all = bookmarkStoreLoad();
  return Object.values(all).reduce((sum, b) => sum + (b.qids?.length || 0), 0);
}

/* ============================================================
   5d) SOLVED LOG — 누적 풀이 기록 (통계용)
   ============================================================ */
function logSolved(qid, slug, topic, correct) {
  let log;
  try { log = storeLoad(LS_KEYS.solvedLog, []) || []; } catch (e) { log = []; }
  log.push({
    date: new Date().toISOString(),
    qid, slug, topic: topic || null, correct: !!correct,
  });
  // 용량 한도 — 오래된 것부터 제거
  while (log.length > SOLVED_LOG_MAX) log.shift();
  storeSave(LS_KEYS.solvedLog, log);
}

/* ============================================================
   5e) STATS — 통계 분석 (일주 정답률 추이 + 약한 topic Top 5)
   ============================================================ */
function statsAnalyze() {
  const log = storeLoad(LS_KEYS.solvedLog, []) || [];
  if (!log.length) {
    return { totalSolved: 0, overallAccuracy: 0, last7Days: [], weakTopics: [], strongTopics: [] };
  }
  // 일자별
  const byDay = {};
  log.forEach((e) => {
    const day = (e.date || '').slice(0, 10);
    if (!day) return;
    if (!byDay[day]) byDay[day] = { solved: 0, correct: 0 };
    byDay[day].solved += 1;
    if (e.correct) byDay[day].correct += 1;
  });
  // 최근 7일 (오늘 포함 역순)
  const today = new Date();
  const last7Days = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today); d.setDate(today.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const s = byDay[key] || { solved: 0, correct: 0 };
    last7Days.push({
      date: key,
      label: `${d.getMonth() + 1}/${d.getDate()}`,
      solved: s.solved,
      correct: s.correct,
      accuracy: s.solved ? s.correct / s.solved : null,
    });
  }
  // Topic별
  const byTopic = {};
  log.forEach((e) => {
    if (!e.topic) return;
    if (!byTopic[e.topic]) byTopic[e.topic] = { solved: 0, correct: 0 };
    byTopic[e.topic].solved += 1;
    if (e.correct) byTopic[e.topic].correct += 1;
  });
  const ranked = Object.entries(byTopic)
    .filter(([_, s]) => s.solved >= 3)  // 최소 3회 푼 것만 의미 있음
    .map(([t, s]) => ({
      topic: t, solved: s.solved, correct: s.correct,
      accuracy: s.correct / s.solved,
    }));
  const weakTopics = ranked.slice().sort((a, b) => a.accuracy - b.accuracy).slice(0, 5);
  const strongTopics = ranked.slice().sort((a, b) => b.accuracy - a.accuracy).slice(0, 5);
  const totalCorrect = log.filter((e) => e.correct).length;
  return {
    totalSolved: log.length,
    overallAccuracy: totalCorrect / log.length,
    last7Days,
    weakTopics,
    strongTopics,
  };
}

/* ============================================================
   5f) SEARCH — 키워드 · 태그 · 이론 매칭
   ============================================================ */
async function searchQuestions(query, opts = {}) {
  const q = (query || '').trim().toLowerCase();
  if (q.length < 2) return [];
  const limit = opts.limit || 50;
  const out = [];
  for (const cat of state.catalog) {
    let data;
    try { data = await loadCategory(cat.slug); }
    catch (e) { continue; }
    for (const question of data.questions) {
      const tags = (question.tags || []).join(' ');
      const hay = [
        question.statement, question.topic, question.theory, tags,
        question.explanation_o, question.explanation_x, question.explanation,
      ].filter(Boolean).join(' ').toLowerCase();
      if (hay.includes(q)) {
        out.push({
          ...question,
          __sourceSlug: cat.slug,
          __sourceCatName: cat.name,
        });
        if (out.length >= limit) return out;
      }
    }
  }
  return out;
}

/* ============================================================
   5g) BUILD VIRTUAL CATEGORY — 즐겨찾기 · 태그 · 검색 결과
   ============================================================ */
async function buildVirtualBookmarkCategory() {
  const all = bookmarkStoreLoad();
  const items = [];
  for (const sourceSlug in all) {
    const qids = all[sourceSlug].qids || [];
    if (!qids.length) continue;
    let catData;
    try { catData = await loadCategory(sourceSlug); }
    catch (e) { continue; }
    const found = catData.questions.filter((q) => qids.includes(q.id));
    found.forEach((q) => {
      q.__sourceSlug = sourceSlug;
      q.__sourceCatName = catData.category.name;
    });
    items.push(...found);
  }
  return {
    category: {
      slug: BOOKMARK_VIRTUAL_SLUG,
      name: `즐겨찾기 ${items.length}건`,
      exam_group: '북마크',
      subject: '복습',
      phase: '',
    },
    questions: items,
    _meta: { total: items.length, source: 'localStorage' },
  };
}

async function buildVirtualTagCategory(tag) {
  const items = [];
  for (const cat of state.catalog) {
    let data;
    try { data = await loadCategory(cat.slug); }
    catch (e) { continue; }
    data.questions.forEach((q) => {
      if ((q.tags || []).includes(tag)) {
        items.push({ ...q, __sourceSlug: cat.slug, __sourceCatName: cat.name });
      }
    });
  }
  return {
    category: {
      slug: TAG_VIRTUAL_PREFIX + tag,
      name: `#${tag} · ${items.length}건`,
      exam_group: '태그 모음',
      subject: tag,
      phase: '',
    },
    questions: items,
    _meta: { total: items.length, source: 'tag-filter' },
  };
}

async function buildVirtualSearchCategory(query, results) {
  return {
    category: {
      slug: SEARCH_VIRTUAL_PREFIX + query,
      name: `"${query}" · ${results.length}건`,
      exam_group: '검색 결과',
      subject: query,
      phase: '',
    },
    questions: results,
    _meta: { total: results.length, source: 'search' },
  };
}

/* ============================================================
   5) TWEAKS
   ============================================================ */

function applyTweaks() {
  const t = state.tweaks;
  const root = document.documentElement;
  root.style.setProperty('--type-scale', t.fontScale);
  root.style.setProperty('--ox-o', t.oxPalette[0]);
  root.style.setProperty('--ox-x', t.oxPalette[1]);
  // derive soft/ink
  root.style.setProperty('--ox-o-soft', colorMix(t.oxPalette[0], '#ffffff', 0.82));
  root.style.setProperty('--ox-x-soft', colorMix(t.oxPalette[1], '#ffffff', 0.82));
  root.style.setProperty('--ox-o-ink', colorMix(t.oxPalette[0], '#000000', 0.55));
  root.style.setProperty('--ox-x-ink', colorMix(t.oxPalette[1], '#000000', 0.55));
}

function setTweak(key, value) {
  state.tweaks[key] = value;
  storeSave(LS_KEYS.tweaks, state.tweaks);
  applyTweaks();
  if (key === 'fontScale') setText('#tweak-fontscale-value', value.toFixed(2) + 'x');
  if (key === 'feedbackStyle') updateFeedbackActive(value);
  if (key === 'oxPalette') updatePaletteActive(value);
  gaEvent('exam_tweak_change', { key, value: JSON.stringify(value) });
}

function colorMix(a, b, t) {
  const pa = parseHex(a), pb = parseHex(b);
  const r = Math.round(pa[0] * (1 - t) + pb[0] * t);
  const g = Math.round(pa[1] * (1 - t) + pb[1] * t);
  const bl = Math.round(pa[2] * (1 - t) + pb[2] * t);
  return `rgb(${r}, ${g}, ${bl})`;
}
function parseHex(h) {
  h = h.replace('#', '');
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function renderTweakColor() {
  const wrap = $('#tweak-color');
  clear(wrap);
  OX_PALETTES.forEach((p) => {
    const isActive = p.value[0] === state.tweaks.oxPalette[0] && p.value[1] === state.tweaks.oxPalette[1];
    const btn = elem('button', {
      type: 'button',
      class: 'tweak-color__opt' + (isActive ? ' is-active' : ''),
      dataset: { palette: p.value.join(',') },
      on: { click: () => setTweak('oxPalette', p.value) },
    }, [
      elem('span', { class: 'tweak-color__opt-swatch' }, [
        elem('span', { style: { background: p.value[0] } }),
        elem('span', { style: { background: p.value[1] } }),
      ]),
      elem('span', { class: 'tweak-color__opt-label' }, p.name),
    ]);
    wrap.appendChild(btn);
  });
}

function updatePaletteActive(value) {
  $$('#tweak-color .tweak-color__opt').forEach((b) => {
    const v = (b.dataset.palette || '').split(',');
    b.classList.toggle('is-active', v[0] === value[0] && v[1] === value[1]);
  });
}

function updateFeedbackActive(value) {
  $$('#tweak-feedback button').forEach((b) => {
    b.classList.toggle('is-active', b.dataset.val === value);
  });
}

function initTweaksUI() {
  const stored = storeLoad(LS_KEYS.tweaks, null);
  if (stored) state.tweaks = { ...TWEAK_DEFAULTS, ...stored };
  applyTweaks();

  // fontScale
  const fs = $('#tweak-fontscale');
  fs.value = state.tweaks.fontScale;
  setText('#tweak-fontscale-value', state.tweaks.fontScale.toFixed(2) + 'x');
  fs.addEventListener('input', (e) => setTweak('fontScale', parseFloat(e.target.value)));

  // autoOpen
  const ao = $('#tweak-autoopen');
  ao.checked = state.tweaks.autoOpenSheet;
  ao.addEventListener('change', (e) => setTweak('autoOpenSheet', e.target.checked));

  // feedback
  $$('#tweak-feedback button').forEach((b) => {
    b.addEventListener('click', () => setTweak('feedbackStyle', b.dataset.val));
  });
  updateFeedbackActive(state.tweaks.feedbackStyle);

  // color
  renderTweakColor();

  // FAB toggle
  const panel = $('#tweaks-panel');
  $('#tweaks-fab').addEventListener('click', () => {
    panel.hidden = !panel.hidden;
  });
  $('#tweaks-close').addEventListener('click', () => panel.hidden = true);
  $('#open-tweaks').addEventListener('click', () => panel.hidden = !panel.hidden);
}

/* ============================================================
   6) ROUTING — switch between screens
   ============================================================ */

function showScreen(name) {
  const app = $('#app');
  app.dataset.screen = name;
  $$('.screen').forEach((s) => {
    s.hidden = (s.dataset.screenName !== name);
  });
  // footer only on home
  setHidden('#footer', name !== 'home');
  // close overlays
  closeSheet();
  closeTagModal();
  window.scrollTo({ top: 0 });
  gaEvent('exam_screen_view', { screen: name });
}

/* ============================================================
   7) HOME SCREEN
   ============================================================ */

function renderHome() {
  // today label
  const today = new Date();
  const fmt = today.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' });
  setText('#today-label', fmt);

  // daily stats
  const d = dailyDisplay();
  setText('#stat-solved', d.solved);
  setText('#stat-accuracy', d.accuracy);
  setText('#stat-streak', d.streak);

  // continue card
  const last = storeLoad(LS_KEYS.lastSession, null);
  const cc = $('#continue-card');
  if (last && last.categorySlug && last.categorySlug !== WRONG_VIRTUAL_SLUG) {
    const cat = state.catalog.find((c) => c.slug === last.categorySlug);
    if (cat && last.resumeIndex < last.total) {
      cc.hidden = false;
      setText('#continue-cat', cat.name);
      setText('#continue-meta', `${last.resumeIndex + 1}번 문제부터 · ${last.total - last.resumeIndex}문제 남음`);
      $('#continue-progress-fill').style.width = `${(last.resumeIndex / last.total) * 100}%`;
      cc.onclick = () => handleSelectCategory(last.categorySlug, last.resumeIndex);
    } else {
      cc.hidden = true;
    }
  } else {
    cc.hidden = true;
  }

  // 도구 카드 — 오답노트
  const wrongN = wrongTotal();
  const wb = $('#wrongnote-btn');
  if (wb) {
    if (wrongN > 0) {
      wb.hidden = false;
      setText('#wrongnote-count', String(wrongN));
      wb.onclick = () => handleSelectCategory(WRONG_VIRTUAL_SLUG, 0);
    } else { wb.hidden = true; }
  }

  // 도구 카드 — 즐겨찾기
  const bookmarkN = bookmarkTotal();
  const bb = $('#bookmark-btn');
  if (bb) {
    if (bookmarkN > 0) {
      bb.hidden = false;
      setText('#bookmark-count', String(bookmarkN));
      bb.onclick = () => handleSelectCategory(BOOKMARK_VIRTUAL_SLUG, 0);
    } else { bb.hidden = true; }
  }

  // 도구 카드 — 학습 통계 (항상 표시)
  const sb = $('#stats-btn');
  if (sb) {
    const totalSolved = (storeLoad(LS_KEYS.solvedLog, []) || []).length;
    setText('#stats-mini', totalSolved > 0 ? `${totalSolved}건 풀이` : '시작하기');
    sb.onclick = () => { showScreen('stats'); renderStats(); };
  }

  // categories
  const list = $('#cat-list');
  clear(list);
  if (!state.catalog.length) {
    setHidden('#cat-empty', false);
    setText('#cat-count', '');
    return;
  }
  setHidden('#cat-empty', true);
  setText('#cat-count', `${state.catalog.length}개 과목`);

  const wrongByCat = wrongTotalByCategory();
  state.catalog.forEach((cat) => {
    const ratioOfMeta = cat.total ? (cat.with_full_meta / cat.total) : 0;
    const wrongN = wrongByCat[cat.slug] || 0;
    const metaText = `${cat.exam_group} · ${cat.total}문항 · 학습완성 ${cat.with_full_meta}` + (wrongN ? ` · 오답 ${wrongN}` : '');
    const btn = elem('button', {
      type: 'button', class: 'cat', style: { '--cat-color': cat.color },
      on: { click: () => handleSelectCategory(cat.slug, 0) },
    }, [
      elem('div', { class: 'cat__mark' }, [ elem('span', null, cat.name.slice(0, 1)) ]),
      elem('div', { class: 'cat__body' }, [
        elem('div', { class: 'cat__name' }, cat.name),
        elem('div', { class: 'cat__meta' }, metaText),
        elem('div', { class: 'cat__progress' }, [
          elem('div', { style: { width: `${(ratioOfMeta * 100).toFixed(0)}%` } }),
        ]),
      ]),
      svgIcon('chevron-right', { class: 'cat__chev', size: 20 }),
    ]);
    list.appendChild(btn);
  });
}

function svgIcon(name, { size = 20, color = 'currentColor' } = {}) {
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('width', size); svg.setAttribute('height', size);
  svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', color); svg.setAttribute('stroke-width', 2);
  svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  let inner = '';
  switch (name) {
    case 'chevron-right': inner = '<polyline points="9 6 15 12 9 18"/>'; break;
    case 'chevron-down': inner = '<polyline points="6 9 12 15 18 9"/>'; break;
    case 'play': inner = '<polygon points="6 4 20 12 6 20 6 4"/>'; break;
    case 'book': inner = '<path d="M4 5a2 2 0 0 1 2-2h14v17H6a2 2 0 0 0-2 2V5z"/><path d="M4 20a2 2 0 0 1 2-2h14"/>'; break;
    case 'video': inner = '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2"/>'; break;
  }
  svg.innerHTML = inner;
  return svg;
}

/* ============================================================
   8) CATEGORY ENTRY → QUIZ SCREEN
   ============================================================ */

async function handleSelectCategory(slug, startIdx = 0, opts = {}) {
  try {
    let data;
    if (slug === WRONG_VIRTUAL_SLUG) {
      data = await buildVirtualWrongCategory();
      if (!data || !data.questions.length) {
        showToast('오답이 없어요. 카테고리를 골라 풀어보세요.');
        return;
      }
    } else if (slug === BOOKMARK_VIRTUAL_SLUG) {
      data = await buildVirtualBookmarkCategory();
      if (!data || !data.questions.length) {
        showToast('즐겨찾기가 비어있어요. 풀이 중 ⭐을 눌러 추가하세요.');
        return;
      }
    } else if (slug.startsWith(TAG_VIRTUAL_PREFIX)) {
      const tag = slug.slice(TAG_VIRTUAL_PREFIX.length);
      data = await buildVirtualTagCategory(tag);
      if (!data || !data.questions.length) {
        showToast(`#${tag} 태그 문항이 없어요.`);
        return;
      }
    } else if (slug.startsWith(SEARCH_VIRTUAL_PREFIX)) {
      const query = slug.slice(SEARCH_VIRTUAL_PREFIX.length);
      const results = opts.searchResults || (await searchQuestions(query));
      if (!results.length) {
        showToast(`"${query}" 검색 결과 없음`);
        return;
      }
      data = await buildVirtualSearchCategory(query, results);
    } else {
      data = await loadCategory(slug);
    }
    state.currentCategory = data;
    state.idx = startIdx;
    state.userAnswer = null;
    state.history = [];
    state.sheetOpen = false;
    showScreen('quiz');
    renderQuizCardHeader();
    renderQuizQuestion();
    gaEvent('exam_category_start', { slug, start_index: startIdx });
  } catch (e) {
    showToast(`카테고리 로드 실패: ${e.message}`);
  }
}

async function buildVirtualWrongCategory() {
  const all = wrongStoreLoad();
  const wrongQuestions = [];
  for (const sourceSlug in all) {
    const qids = all[sourceSlug].qids || [];
    if (!qids.length) continue;
    let catData;
    try {
      catData = await loadCategory(sourceSlug);
    } catch (e) {
      console.warn(`오답노트: ${sourceSlug} 로드 실패 — 스킵`, e);
      continue;
    }
    const found = catData.questions.filter((q) => qids.includes(q.id));
    found.forEach((q) => { q.__sourceSlug = sourceSlug; q.__sourceCatName = catData.category.name; });
    wrongQuestions.push(...found);
  }
  return {
    category: {
      slug: WRONG_VIRTUAL_SLUG,
      name: `내 오답 ${wrongQuestions.length}건`,
      exam_group: '오답노트',
      subject: '복습',
      phase: '',
      exam_year: null,
      exam_round: null,
    },
    questions: wrongQuestions,
    _meta: { total: wrongQuestions.length, source: 'localStorage' },
  };
}

function renderQuizCardHeader() {
  const cat = state.currentCategory.category;
  setText('#quiz-cat-group', cat.exam_group);
  setText('#quiz-cat-name', cat.name);
  setText('#result-cat-name', cat.name);
}

function renderQuizQuestion() {
  const cat = state.currentCategory;
  const total = cat.questions.length;
  const q = cat.questions[state.idx];

  // progress
  const ratio = ((state.idx + (state.userAnswer ? 1 : 0)) / total) * 100;
  $('#progress-fill').style.width = `${ratio}%`;
  setText('#progress-count', `${String(state.idx + 1).padStart(2, '0')} / ${String(total).padStart(2, '0')}`);

  // q meta
  setText('#q-no', `Q.${q.id}`);
  if (q.topic) {
    const tp = $('#q-topic');
    tp.textContent = q.topic;
    tp.hidden = false;
  } else {
    setHidden('#q-topic', true);
  }
  if (q.tags && q.tags.length) {
    const tg = $('#q-tag');
    tg.textContent = `#${q.tags[0]}`;
    tg.hidden = false;
  } else {
    setHidden('#q-tag', true);
  }

  // statement
  setText('#q-statement', q.statement);
  setText('#q-hint', '좌우로 스와이프하거나 아래 버튼을 누르세요');

  // reset card visuals
  const card = $('#q-card');
  card.classList.remove('flash-o', 'flash-x', 'shake');
  card.style.transform = '';
  $('#btn-o').disabled = false;
  $('#btn-x').disabled = false;
  $('#btn-o').classList.remove('is-pressed');
  $('#btn-x').classList.remove('is-pressed');
  $('#swipe-hint-o').style.opacity = '0';
  $('#swipe-hint-x').style.opacity = '0';
  setHidden('#manual-open', true);

  state.userAnswer = null;
  state.sheetOpen = false;

  // 이어풀기 저장 (아직 풀이 시작 안 한 idx)
  storeSave(LS_KEYS.lastSession, {
    categorySlug: cat.category.slug,
    categoryName: cat.category.name,
    resumeIndex: state.idx,
    total: total,
  });
}

/* ============================================================
   9) ANSWER · FEEDBACK · NEXT
   ============================================================ */

function handleAnswer(choice) {
  if (state.userAnswer) return;
  const cat = state.currentCategory;
  const q = cat.questions[state.idx];
  const correct = choice === q.answer;

  state.userAnswer = choice;
  state.history.push({
    id: q.id,
    statement: q.statement,
    topic: q.topic,
    userAnswer: choice,
    correct,
    sourceSlug: q.__sourceSlug || cat.category.slug,  // 가상 모드에서도 원본 카테고리 추적
  });

  recordDaily(correct);

  // 가상 모드에서는 원본 slug 사용
  const noteSlug = q.__sourceSlug || cat.category.slug;

  // 누적 풀이 로그 (통계용)
  logSolved(q.id, noteSlug, q.topic, correct);

  // 오답노트 자동 적재 / 정답 시 제거
  if (!correct) {
    wrongAdd(noteSlug, q.id);
  } else if (wrongHas(noteSlug, q.id)) {
    wrongRemove(noteSlug, q.id);
  }

  // visual feedback
  const card = $('#q-card');
  const btn = choice === 'O' ? $('#btn-o') : $('#btn-x');
  btn.classList.add('is-pressed');

  const fb = state.tweaks.feedbackStyle;
  if (fb === 'flash') {
    card.classList.add(`flash-${choice === 'O' ? 'o' : 'x'}`);
    if (!correct) setTimeout(() => card.classList.add('shake'), 60);
    setTimeout(() => card.classList.remove('flash-o', 'flash-x', 'shake'), 700);
  } else if (fb === 'shake') {
    if (!correct) card.classList.add('shake');
    setTimeout(() => card.classList.remove('shake'), 360);
  } else { // badge
    if (!correct) card.classList.add('shake');
    setTimeout(() => card.classList.remove('shake'), 360);
  }

  // haptic
  if (navigator.vibrate) navigator.vibrate(correct ? 18 : [10, 40, 10]);

  // disable further
  $('#btn-o').disabled = true;
  $('#btn-x').disabled = true;
  setText('#q-hint', state.tweaks.autoOpenSheet ? '해설을 확인하세요' : '해설 보기 버튼을 누르세요');

  // GA
  gaEvent('exam_quiz_answer', {
    qid: q.id,
    correct: correct ? 1 : 0,
    category: cat.category.slug,
  });

  // auto-open sheet
  if (state.tweaks.autoOpenSheet) {
    setTimeout(() => openSheet(), 360);
  } else {
    setHidden('#manual-open', false);
  }
}

function handleNext() {
  const total = state.currentCategory.questions.length;
  if (state.idx >= total - 1) {
    // finish
    showResult();
    storeSave(LS_KEYS.lastSession, null); // 완료 시 이어풀기 초기화
    return;
  }
  state.idx += 1;
  renderQuizQuestion();
}

/* ============================================================
   10) EXPLANATION SHEET
   ============================================================ */

function pickExplanation(q, userAnswer) {
  // 정답에 맞는 explanation_o/_x 우선, 없으면 explanation(PDF), 없으면 placeholder
  if (q.answer === 'O' && q.explanation_o) return q.explanation_o;
  if (q.answer === 'X' && q.explanation_x) return q.explanation_x;
  if (q.explanation) return q.explanation;
  // 사용자 답 기준 fallback
  if (userAnswer === 'O' && q.explanation_o) return q.explanation_o;
  if (userAnswer === 'X' && q.explanation_x) return q.explanation_x;
  return '해설이 준비 중입니다. 메타데이터 보강 후 다시 보여드릴게요.';
}

function openSheet() {
  if (!state.currentCategory) return;
  const q = state.currentCategory.questions[state.idx];
  const ua = state.userAnswer;
  if (!q || !ua) return;

  const correct = ua === q.answer;
  setText('#sheet-verdict', q.answer);
  $('#sheet-verdict').classList.remove('sheet__verdict--o', 'sheet__verdict--x');
  $('#sheet-verdict').classList.add(`sheet__verdict--${correct ? 'o' : 'x'}`);
  setText('#sheet-verdict-label', correct ? '정답입니다' : '오답입니다');
  setText('#sheet-answer-line', correct
    ? `정답 ${q.answer} · 잘 짚었어요`
    : `정답은 ${q.answer} · 당신의 답: ${ua}`);

  // 문제
  setText('#sheet-statement', q.statement);

  // 해설
  setText('#sheet-explanation', pickExplanation(q, ua));

  // 관련 이론
  const theoryWrap = $('#sheet-theory-wrap');
  if (q.theory) {
    theoryWrap.hidden = false;
    setText('#sheet-theory-label', `관련 이론${q.topic ? ' · ' + q.topic : ''}`);
    setText('#sheet-theory', q.theory);
  } else {
    theoryWrap.hidden = false;
    setText('#sheet-theory-label', '관련 이론');
    setText('#sheet-theory', q.topic ? `(${q.topic} — 이론 정리 준비 중)` : '관련 이론이 준비 중입니다.');
  }

  // 태그
  const tagsWrap = $('#sheet-tags-wrap');
  const tagsBox = $('#sheet-tags');
  clear(tagsBox);
  if (q.tags && q.tags.length) {
    tagsWrap.hidden = false;
    q.tags.forEach((t) => {
      const chip = elem('button', {
        type: 'button', class: 'chip',
        on: { click: () => openTagModal(t) },
      }, `#${t}`);
      tagsBox.appendChild(chip);
    });
  } else {
    tagsWrap.hidden = true;
  }

  // 관련 영상 · 교과서
  const rel = $('#sheet-related');
  clear(rel);
  // 영상 슬롯 (MVP는 비어있음)
  const videoTitle = q.topic ? `${q.topic} 강의` : '관련 강의';
  rel.appendChild(elem('div', { class: 'related-item', style: { cursor: 'default' } }, [
    elem('div', { class: 'related-item__icon' }, [svgIcon('video', { size: 18 })]),
    elem('div', { style: { flex: 1 } }, [
      elem('div', { class: 'related-item__title' }, videoTitle),
      elem('div', { class: 'related-item__meta' }, '관련 영상 매칭 준비 중'),
    ]),
    elem('span', { class: 'related-item__badge' }, '준비 중'),
  ]));
  // 교과서
  if (q.topic) {
    const [book, chapter] = q.topic.split(' §');
    rel.appendChild(elem('button', { type: 'button', class: 'related-item' }, [
      elem('div', { class: 'related-item__icon' }, [svgIcon('book', { size: 18 })]),
      elem('div', { style: { flex: 1 } }, [
        elem('div', { class: 'related-item__title' }, `교과서 — ${book || q.topic}`),
        elem('div', { class: 'related-item__meta' }, chapter ? `${chapter} 로 이동` : '관련 챕터'),
      ]),
      svgIcon('chevron-right', { size: 18, color: 'var(--ink-soft)' }),
    ]));
  }

  // 출처
  setText('#sheet-source-pdf', `출처: ${q.source_pdf || '준비 중'}`);
  setText('#sheet-meta-quality', q.meta_quality || 0);

  // ⭐ 북마크 토글 동기화
  const bmBtn = $('#sheet-bookmark');
  if (bmBtn) {
    const noteSlug = q.__sourceSlug || state.currentCategory.category.slug;
    const isBm = bookmarkHas(noteSlug, q.id);
    bmBtn.dataset.bookmarked = isBm ? '1' : '0';
    bmBtn.setAttribute('aria-pressed', String(isBm));
    bmBtn.title = isBm ? '즐겨찾기 해제' : '즐겨찾기 추가';
  }

  // CTA label
  const isLast = state.idx >= state.currentCategory.questions.length - 1;
  setText('#sheet-next-label', isLast ? '결과 보기' : '다음 문제');

  // open
  state.sheetOpen = true;
  $('#sheet').hidden = false;
  $('#sheet-backdrop').hidden = false;
  // force reflow for transition
  void $('#sheet').offsetWidth;
  $('#sheet').classList.add('is-open');
  $('#sheet-backdrop').classList.add('is-open');
  document.body.classList.add('is-sheet-open');
  gaEvent('exam_learn_expand', { qid: q.id });
}

function closeSheet() {
  state.sheetOpen = false;
  const sheet = $('#sheet'); const bd = $('#sheet-backdrop');
  if (!sheet) return;
  sheet.classList.remove('is-open');
  bd.classList.remove('is-open');
  setTimeout(() => { sheet.hidden = true; bd.hidden = true; }, 320);
  document.body.classList.remove('is-sheet-open');
}

/* ============================================================
   11) TAG FILTER MODAL (MVP: 확인까지)
   ============================================================ */

function openTagModal(tag) {
  state.tagFilterPending = tag;
  const total = state.currentCategory.questions.filter(
    (q) => (q.tags || []).includes(tag)
  ).length;
  setText('#tag-modal-name', `#${tag}`);
  setText('#tag-modal-count', `· ${total}문제`);
  const ov = $('#tag-modal-overlay');
  ov.hidden = false;
  void ov.offsetWidth;
  ov.classList.add('is-open');
  document.body.classList.add('is-modal-open');
}

function closeTagModal() {
  const ov = $('#tag-modal-overlay');
  if (!ov) return;
  state.tagFilterPending = null;
  ov.classList.remove('is-open');
  setTimeout(() => { ov.hidden = true; }, 280);
  document.body.classList.remove('is-modal-open');
}

/* ============================================================
   12) RESULT SCREEN
   ============================================================ */

function showResult() {
  showScreen('result');
  const cat = state.currentCategory.category;
  const h = state.history;
  const correctCount = h.filter((x) => x.correct).length;
  const total = h.length;
  const pct = total ? Math.round(100 * correctCount / total) : 0;

  let kicker = '잘 풀었어요';
  if (pct >= 90) kicker = '거의 만점이에요';
  else if (pct >= 70) kicker = '안정권입니다';
  else if (pct >= 50) kicker = '조금만 더';
  else kicker = '다시 풀어볼까요';

  setText('#result-cat-name', cat.name);
  setText('#result-correct', correctCount);
  setText('#result-total', total);
  setText('#result-pct', pct);
  setText('#result-kicker', kicker);

  const wrong = h.filter((x) => !x.correct);
  setText('#result-wrong-count', `${wrong.length}개 오답`);

  const list = $('#review-list');
  const empty = $('#review-empty');
  clear(list);
  if (!wrong.length) {
    empty.hidden = false;
    list.hidden = true;
  } else {
    empty.hidden = true;
    list.hidden = false;
    wrong.forEach((x) => {
      list.appendChild(elem('div', { class: 'review-item' }, [
        elem('div', { class: 'review-item__mark review-item__mark--ng' }, 'X'),
        elem('div', { style: { flex: 1 } }, [
          elem('div', { class: 'review-item__text' }, x.statement),
          elem('div', { class: 'review-item__topic' }, `${x.topic || ''} · 내 답 ${x.userAnswer}`),
        ]),
      ]));
    });
  }

  const grid = $('#result-grid');
  clear(grid);
  h.forEach((x) => {
    grid.appendChild(elem('div', {
      class: 'result-grid__cell ' + (x.correct ? 'result-grid__cell--ok' : 'result-grid__cell--ng'),
    }, x.userAnswer));
  });

  gaEvent('exam_category_complete', {
    slug: cat.slug,
    pct: pct,
    correct: correctCount,
    total: total,
  });
}

/* ============================================================
   13) QUIZ INTERACTIONS — swipe, keyboard, manual open
   ============================================================ */

function attachQuizInteractions() {
  // O/X buttons
  $('#btn-o').addEventListener('click', () => handleAnswer('O'));
  $('#btn-x').addEventListener('click', () => handleAnswer('X'));

  // Exit
  $('#quiz-exit').addEventListener('click', () => {
    showScreen('home');
    renderHome();
  });

  // Manual open
  $('#manual-open').addEventListener('click', () => openSheet());

  // Sheet
  $('#sheet-close').addEventListener('click', closeSheet);
  $('#sheet-backdrop').addEventListener('click', closeSheet);
  $('#sheet-next').addEventListener('click', () => {
    closeSheet();
    setTimeout(() => handleNext(), 100);
  });

  // Tag modal
  $('#tag-modal-cancel').addEventListener('click', closeTagModal);
  $('#tag-modal-overlay').addEventListener('click', (e) => {
    if (e.target === $('#tag-modal-overlay')) closeTagModal();
  });
  $('#tag-modal-confirm').addEventListener('click', () => {
    const tag = state.tagFilterPending;
    closeTagModal();
    if (tag) {
      setTimeout(() => handleSelectCategory(TAG_VIRTUAL_PREFIX + tag, 0), 200);
    }
  });

  // 시트 ⭐ 북마크 토글
  const bmBtn = $('#sheet-bookmark');
  if (bmBtn) {
    bmBtn.addEventListener('click', () => {
      if (!state.currentCategory) return;
      const q = state.currentCategory.questions[state.idx];
      if (!q) return;
      const noteSlug = q.__sourceSlug || state.currentCategory.category.slug;
      if (bookmarkHas(noteSlug, q.id)) {
        bookmarkRemove(noteSlug, q.id);
        bmBtn.dataset.bookmarked = '0';
        bmBtn.setAttribute('aria-pressed', 'false');
        showToast('즐겨찾기에서 제거됨');
      } else {
        bookmarkAdd(noteSlug, q.id);
        bmBtn.dataset.bookmarked = '1';
        bmBtn.setAttribute('aria-pressed', 'true');
        showToast('⭐ 즐겨찾기 추가');
      }
    });
  }

  // Swipe (touch + mouse)
  const card = $('#q-card');
  const touch = { x: 0, y: 0, active: false };
  let swipeDx = 0;

  function onStart(clientX, clientY) {
    if (state.userAnswer) return;
    touch.x = clientX; touch.y = clientY; touch.active = true;
    card.style.transition = 'none';
  }
  function onMove(clientX, clientY) {
    if (!touch.active) return;
    const dx = clientX - touch.x;
    const dy = clientY - touch.y;
    if (Math.abs(dx) > Math.abs(dy)) {
      swipeDx = dx;
      card.style.transform = `translateX(${dx * 0.5}px) rotate(${dx * 0.03}deg)`;
      $('#swipe-hint-o').style.opacity = String(Math.max(0, Math.min(1, dx / 100)));
      $('#swipe-hint-x').style.opacity = String(Math.max(0, Math.min(1, -dx / 100)));
    }
  }
  function onEnd() {
    if (!touch.active) return;
    touch.active = false;
    card.style.transition = '';
    if (Math.abs(swipeDx) > 80) {
      handleAnswer(swipeDx > 0 ? 'O' : 'X');
    } else {
      card.style.transform = '';
      $('#swipe-hint-o').style.opacity = '0';
      $('#swipe-hint-x').style.opacity = '0';
    }
    swipeDx = 0;
  }

  card.addEventListener('touchstart', (e) => {
    const t = e.touches[0]; onStart(t.clientX, t.clientY);
  }, { passive: true });
  card.addEventListener('touchmove', (e) => {
    const t = e.touches[0]; onMove(t.clientX, t.clientY);
  }, { passive: true });
  card.addEventListener('touchend', onEnd);
  card.addEventListener('mousedown', (e) => onStart(e.clientX, e.clientY));
  card.addEventListener('mousemove', (e) => onMove(e.clientX, e.clientY));
  card.addEventListener('mouseup', onEnd);
  card.addEventListener('mouseleave', onEnd);

  // Keyboard
  window.addEventListener('keydown', (e) => {
    if ($('#app').dataset.screen !== 'quiz') return;
    if (state.sheetOpen) {
      if (e.key === 'Enter' || e.key === 'ArrowRight') { closeSheet(); setTimeout(handleNext, 100); }
      if (e.key === 'Escape') closeSheet();
      return;
    }
    if (!state.userAnswer) {
      if (e.key === 'o' || e.key === 'O' || e.key === 'ArrowRight') handleAnswer('O');
      if (e.key === 'x' || e.key === 'X' || e.key === 'ArrowLeft') handleAnswer('X');
    } else if (!state.tweaks.autoOpenSheet) {
      if (e.key === ' ' || e.key === 'Enter') openSheet();
      if (e.key === 'ArrowRight') handleNext();
    }
  });
}

/* ============================================================
   13b) STATS SCREEN
   ============================================================ */

function renderStats() {
  const s = statsAnalyze();
  setText('#stats-total', s.totalSolved);
  setText('#stats-acc', Math.round((s.overallAccuracy || 0) * 100));

  // 최근 7일 막대
  const week = $('#stats-week');
  clear(week);
  const maxSolved = Math.max(1, ...s.last7Days.map((d) => d.solved));
  s.last7Days.forEach((d) => {
    const heightRatio = d.solved / maxSolved;
    const cell = elem('div', { class: 'stats-week__cell' }, [
      elem('div', { class: 'stats-week__bar-wrap' }, [
        elem('div', {
          class: 'stats-week__bar' + (d.solved === 0 ? ' is-empty' : ''),
          style: { height: `${heightRatio * 100}%` },
          title: d.solved ? `${d.solved}건 · ${Math.round((d.accuracy || 0) * 100)}%` : '풀이 없음',
        }),
      ]),
      elem('div', { class: 'stats-week__label' }, d.label),
      elem('div', { class: 'stats-week__num' }, String(d.solved)),
    ]);
    week.appendChild(cell);
  });

  // 약한 topic
  const weakWrap = $('#stats-weak');
  const weakEmpty = $('#stats-weak-empty');
  clear(weakWrap);
  if (!s.weakTopics.length) {
    weakEmpty.hidden = false;
  } else {
    weakEmpty.hidden = true;
    s.weakTopics.forEach((t) => weakWrap.appendChild(renderTopicRow(t, 'weak')));
  }

  // 잘 푸는 topic
  const strongWrap = $('#stats-strong');
  clear(strongWrap);
  s.strongTopics.forEach((t) => strongWrap.appendChild(renderTopicRow(t, 'strong')));
}

function renderTopicRow(t, kind) {
  const pct = Math.round((t.accuracy || 0) * 100);
  return elem('div', { class: 'topic-row topic-row--' + kind }, [
    elem('div', { class: 'topic-row__name' }, t.topic),
    elem('div', { class: 'topic-row__meta' }, `${t.correct}/${t.solved} · ${pct}%`),
    elem('div', { class: 'topic-row__bar-wrap' }, [
      elem('div', { class: 'topic-row__bar', style: { width: `${pct}%` } }),
    ]),
  ]);
}

/* ============================================================
   13c) SEARCH SCREEN
   ============================================================ */

let _searchInProgress = false;

async function handleSearch(query) {
  query = (query || '').trim();
  if (query.length < 2) { showToast('2자 이상 입력해주세요'); return; }
  if (_searchInProgress) return;
  _searchInProgress = true;
  showToast(`"${query}" 검색 중...`, 1200);
  try {
    const results = await searchQuestions(query);
    state.searchResults = results;
    state.searchQuery = query;
    showScreen('search');
    renderSearchResults(query, results);
  } finally {
    _searchInProgress = false;
  }
}

function renderSearchResults(query, results) {
  setText('#search-query-label', `"${query}"`);
  setText('#search-count-label', `${results.length}건`);
  const list = $('#search-list');
  const empty = $('#search-empty');
  const playAll = $('#search-play-all');
  clear(list);
  if (!results.length) {
    empty.hidden = false;
    playAll.hidden = true;
    return;
  }
  empty.hidden = true;
  playAll.hidden = false;
  results.slice(0, 30).forEach((q) => {
    const card = elem('button', {
      type: 'button',
      class: 'search-card',
      on: { click: () => handleSelectCategory(SEARCH_VIRTUAL_PREFIX + query, results.indexOf(q), { searchResults: results }) },
    }, [
      elem('div', { class: 'search-card__head' }, [
        elem('span', { class: 'search-card__cat' }, q.__sourceCatName || ''),
        elem('span', { class: 'search-card__ans search-card__ans--' + (q.answer === 'O' ? 'o' : 'x') }, q.answer),
      ]),
      elem('div', { class: 'search-card__stmt' }, q.statement || ''),
      q.topic ? elem('div', { class: 'search-card__topic' }, q.topic) : null,
    ]);
    list.appendChild(card);
  });
  if (playAll) {
    playAll.onclick = () => handleSelectCategory(SEARCH_VIRTUAL_PREFIX + query, 0, { searchResults: results });
  }
}

/* ============================================================
   14) RESULT SCREEN INTERACTIONS
   ============================================================ */

function attachResultInteractions() {
  $('#result-home').addEventListener('click', () => {
    showScreen('home'); renderHome();
  });
  $('#result-back').addEventListener('click', () => {
    showScreen('home'); renderHome();
  });
  $('#result-restart').addEventListener('click', () => {
    const slug = state.currentCategory.category.slug;
    handleSelectCategory(slug, 0);
  });
}

function attachStatsSearchInteractions() {
  // 검색 인풋
  const inp = $('#search-input');
  const go = $('#search-go');
  if (inp) {
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); handleSearch(inp.value); }
    });
  }
  if (go) {
    go.addEventListener('click', () => handleSearch(inp?.value || ''));
  }
  // 통계 화면 홈 버튼
  const sh = $('#stats-home');
  if (sh) sh.addEventListener('click', () => { showScreen('home'); renderHome(); });
  // 검색 화면 홈 버튼
  const sch = $('#search-home');
  if (sch) sch.addEventListener('click', () => { showScreen('home'); renderHome(); });
}

/* ============================================================
   15) BOOTSTRAP
   ============================================================ */

async function boot() {
  initTweaksUI();
  attachQuizInteractions();
  attachResultInteractions();
  attachStatsSearchInteractions();

  try {
    const { flat, meta } = await loadCatalog();
    state.catalog = flat;
    showScreen('home');
    renderHome();
    if (meta && meta.total_questions != null) {
      console.log(`[exam] 카테고리 ${flat.length}개, 총 ${meta.total_questions}문항 로드`);
    }
  } catch (e) {
    console.error('Catalog load failed:', e);
    showScreen('home');
    setHidden('#cat-empty', false);
    setText('#cat-empty', `데이터를 불러오지 못했어요. (${e.message})\n잠시 후 다시 시도해주세요.`);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
