/* =================================================================
   넌센스 OX 퀴즈 — script.js (v3: Grand Slam + 시각 보강)
   Architecture: Option C (Pragmatic Balance, single-file with sections)
   Reference: docs/02-design/features/survival-mode-v3.design.md
   저작권 자체 인증: 퀴즈스틱맨 자산 미사용. 컬러·메커니즘 컨셉만 차용.
   ================================================================= */
'use strict';

// === CONSTANTS ===
const ALIVE_INITIAL = 50;          // [v2] 1 player + 49 NPC
const NPC_COUNT = 49;              // [v2] 변경 (v1: 16)
const QUESTIONS_PER_THEME = 5;
const ROUND_THEMES = ['grass', 'ice', 'desert', 'cave', 'storm', 'final'];
const TOAST_DURATION_MS = 1500;
const TIMER_DURATION_SEC = 5;
const REVEAL_DELAY_MS = 1800;
const ROUND_BUFFER_SIZE = 30;       // 풀에서 한 번에 셔플해두는 라운드 수 (소진 시 재셔플)

// [v3] NPC 정답률 곡선 — v2 [0.35→0.72] 대비 완화. SC-V3-02(평균 라운드 4-7) 충족 목표
const NPC_ACCURACY_CURVE = [0.30, 0.42, 0.50, 0.55, 0.60, 0.62, 0.64, 0.65];

// [v2] NPC 메번직 타이밍
const NPC_DECIDE_MIN_MS = 600;
const NPC_DECIDE_MAX_MS = 2400;
const NPC_WAVER_PROBABILITY = 0.5;
const NPC_WAVER_DELAY_MIN_MS = 1000;
const NPC_WAVER_DELAY_MAX_MS = 2200;
const NPC_WAVER_CUTOFF_MS = 200;          // reveal 직전 N ms 내엔 결정 스킵

const SIDES = ['O', 'X'];
const OPPOSITE = { O: 'X', X: 'O' };

// [v2] 4종 탈락 이펙트
const EFFECT_TYPES = ['fall', 'poof', 'floor-crack', 'rocket'];
const EFFECT_DURATION_MS = { 'fall': 600, 'poof': 500, 'floor-crack': 800, 'rocket': 700 };

// [v2] arena 좌표 (% 단위)
const PLAYER_ID = 0;
const ZONE_O_CENTER_X = 25;
const ZONE_X_CENTER_X = 75;
const ZONE_NEUTRAL_X = 50;
const ZONE_JITTER_X_PCT = 8;        // ±8% 가로 분산
const SPRITE_Y_MIN_PCT = 12;
const SPRITE_Y_MAX_PCT = 88;

// === V3 CONSTANTS ===
// [v3 tuning] Bernoulli simulate(10000) 결과 — THRESHOLD=4 가 SC-V3-01 sweet spot:
//   50% 정답률: GS 2.06% (rare, casual)
//   65% 정답률: GS 6.80% ✓ within 5-15% target
//   75% 정답률: GS 15.53% ✓ skilled players
// 영상 원본의 "11라운드"는 고정 라운드 게임 의미 — 우리 무한 라운드 모델에선 4 = 적절한 도전
const GRAND_SLAM_THRESHOLD = 4;             // N라운드 무패 정답 + 최후의 1인 = Grand Slam
const SPAWN_LANE_PATTERN = 'column';        // 'random' (v2) | 'column' (v3 default)
const SPAWN_COLUMN_DURATION_MS = 1500;      // 위→중앙 등장 애니 시간

// [v3] 종료 결과 코드 — 6개 함수에서 사용. 오타로 인한 silent fallthrough 방지.
const RESULT = {
  WIN_GS:    'win-grand-slam',
  WIN:       'win',
  LOSE_SURV: 'lose-survivor',
  LOSE_RANK: 'lose-ranking',
};

// === V4 CONSTANTS ===
const QUIZ_INDEX_PATH = 'data/quiz/_index.json';   // 카테고리 카탈로그
const QUIZ_CATEGORY_DIR = 'data/quiz/';            // 개별 카테고리 JSON
const FALLBACK_CSV_PATH = 'data/questions_v1.csv'; // _index.json 미존재 시 폴백

const SPRITES_BASE = '_refs/sprites/';
const CHARACTER_POOL = [
  // 영웅
  'char-hero-superhero','char-hero-ninja','char-hero-knight',
  'char-hero-wizard','char-hero-pirate','char-hero-archer',
  // 몬스터
  'char-monster-zombie','char-monster-ghost','char-monster-vampire',
  'char-monster-skeleton','char-monster-mummy','char-monster-demon',
  // 동물
  'char-animal-cat','char-animal-dog','char-animal-fox',
  'char-animal-panda','char-animal-tiger','char-animal-dragon',
  // SF/직업
  'char-misc-robot','char-misc-alien','char-misc-scientist',
  'char-misc-chef','char-misc-clown','char-misc-fairy',
];
const CHARACTER_ME = 'char-me';
const GA_MEASUREMENT_ID = 'G-XXXXXXXXXX'; // TODO(GA4): 실제 측정 ID로 교체

const Game = {
  // ── STATE (single source of truth) ──
  state: {
    // 데이터 (v1 재사용)
    questionPool: [],
    currentRound: [],
    questionIndex: 0,                  // currentRound 내 인덱스 (소진 시 재셔플로 0 reset)
    score: 0,
    view: 'intro',
    utm: { source: null, medium: null, campaign: null },
    sessionStartedAt: null,
    loadError: null,

    // [v4] 카테고리 시스템
    categoryIndex: null,               // _index.json 캐시
    selectedSlug: null,                // 사용자가 선택한 카테고리 slug
    selectedCategory: null,            // 선택된 카테고리의 메타+문제 풀

    // [v2] 서바이벌 진행 상태
    roundIndex: 0,                     // 누적 라운드 (NPC accuracy curve 인덱스)
    alive: new Set(),                  // 살아있는 캐릭터 id 집합
    playerEliminated: false,
    playerChoice: null,                // 'O' | 'X' | null (현 라운드 입력 여부)

    // [v3] Grand Slam 추적
    consecutiveCorrect: 0,             // 현재 연속 정답 (오답 시 0)
    allCorrect: true,                  // 한 번이라도 오답이면 false (Grand Slam 자격)

    // [v2] NPC 풀 (게임 시작 시 1회 생성)
    npcs: [],                          // [{id, sprite, element, baseY, jitterO, jitterX, currentSide}]
    playerSprite: null,                // me 캐릭터 element

    // 라운드 진행
    timerRemaining: TIMER_DURATION_SEC,
    answerRevealed: false,
    timerHandle: null,
    npcTimerHandles: [],
  },

  // === BOOTSTRAP ===
  async init() {
    Game.parseUTM();
    Game.bindIntroHandlers();
    Game.bindGameHandlers();
    Game.bindEndHandlers();
    try {
      // [v4] 카테고리 인덱스 우선 시도 → 실패 시 CSV fallback
      const idxRes = await fetch(QUIZ_INDEX_PATH, { cache: 'no-store' });
      if (idxRes.ok) {
        const index = await idxRes.json();
        Game.state.categoryIndex = index;
        Game.populateCategorySelect(index);
        // 디폴트 슬러그 선택 + 메타 표시
        const defaultSlug = index.default_slug || (index.categories[0] && index.categories[0].slug);
        Game.selectCategory(defaultSlug);
        Game.showIntroStatus('');
        Game.enableStartButton();
        console.info(`[OXQuiz] ${index.categories.length}개 카테고리 로드, 디폴트 = ${defaultSlug}`);
        if (location.search.includes('dev=autostart')) {
          setTimeout(() => Game.startGame(), 200);
        }
        return;
      }
      console.warn('[OXQuiz] _index.json 없음 — CSV fallback');
      // Fallback: 단일 CSV (v1 호환)
      const text = await Game.fetchCSV(FALLBACK_CSV_PATH);
      const parsed = Game.parseCSV(text);
      const valid = parsed.filter(Game.validateQuestion);
      Game.state.questionPool = valid;
      Game.state.selectedCategory = { slug: 'fallback', name: '기본 (v1)', count: valid.length };
      if (valid.length < 5) {
        Game.showIntroStatus(`데이터 준비 중 (${valid.length}/5 최소)`);
        return;
      }
      Game.showIntroStatus('');
      Game.enableStartButton();
      if (location.search.includes('dev=autostart')) {
        setTimeout(() => Game.startGame(), 200);
      }
    } catch (err) {
      console.error('[OXQuiz] 데이터 로드 실패:', err);
      Game.state.loadError = err.message || String(err);
      Game.renderError(Game.state.loadError);
    }
  },

  // [v4] 카테고리 selector 채우기 (exam_group 별 optgroup 분리)
  populateCategorySelect(index) {
    const sel = document.getElementById('category-select');
    if (!sel || !index || !index.categories) return;
    sel.replaceChildren();
    // exam_group이 있는 카테고리는 optgroup 으로 묶고, 없는 카테고리는 그대로
    const grouped = new Map();   // group label → [cat]
    const standalone = [];
    for (const c of index.categories) {
      if (c.exam_group) {
        if (!grouped.has(c.exam_group)) grouped.set(c.exam_group, []);
        grouped.get(c.exam_group).push(c);
      } else {
        standalone.push(c);
      }
    }
    // 단독 카테고리 먼저
    for (const c of standalone) {
      const opt = document.createElement('option');
      opt.value = c.slug;
      opt.textContent = `${c.name} (${c.count}문항)`;
      if (c.is_default) opt.selected = true;
      sel.appendChild(opt);
    }
    // 그룹 카테고리
    for (const [group, cats] of grouped) {
      const og = document.createElement('optgroup');
      og.label = group;
      for (const c of cats) {
        const opt = document.createElement('option');
        opt.value = c.slug;
        const subjLabel = c.phase ? `${c.subject} · ${c.phase}` : c.subject || c.name;
        opt.textContent = `${subjLabel} (${c.count}문항)`;
        og.appendChild(opt);
      }
      sel.appendChild(og);
    }
    // change 이벤트 — 카테고리 전환
    sel.addEventListener('change', () => Game.selectCategory(sel.value));
  },

  // [v4] 카테고리 선택 — 메타 표시 + 문제 풀 lazy load
  async selectCategory(slug) {
    if (!slug) return;
    Game.state.selectedSlug = slug;
    const meta = Game.state.categoryIndex?.categories.find(c => c.slug === slug);
    if (!meta) return;
    Game.state.selectedCategory = meta;
    // 메타 라인 표시
    const metaEl = document.getElementById('category-meta');
    if (metaEl) {
      const parts = [];
      if (meta.exam_group) parts.push(meta.exam_group);
      if (meta.source && !meta.exam_group) parts.push(meta.source);
      parts.push(`${meta.count}문항`);
      metaEl.textContent = parts.join(' · ');
    }
    // 셀렉트 동기화 (autostart 등에서 strate set)
    const sel = document.getElementById('category-select');
    if (sel && sel.value !== slug) sel.value = slug;
  },

  // [v4] 선택된 카테고리의 문제 JSON fetch
  async loadCategoryQuestions(slug) {
    const url = `${QUIZ_CATEGORY_DIR}${slug}.json`;
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`category fetch ${res.status}: ${slug}`);
    const data = await res.json();
    if (!Array.isArray(data.questions)) throw new Error(`malformed category JSON: ${slug}`);
    // questions 정규화 (id, question, answer, explanation 만 사용)
    const valid = data.questions.filter(q =>
      Number.isInteger(q.id) && q.question && (q.answer === 'O' || q.answer === 'X')
    );
    return { meta: data, questions: valid };
  },

  bindIntroHandlers() {
    document.getElementById('start-btn')?.addEventListener('click', () => Game.startGame());
    Game.populateIntroCrowd();
  },

  populateIntroCrowd() {
    const crowd = document.getElementById('intro-crowd');
    if (!crowd || crowd.children.length > 0) return;
    const npcs = Game.shuffle(CHARACTER_POOL, CHARACTER_POOL.length);
    const halfIdx = Math.floor(npcs.length / 2);
    const sequence = [...npcs.slice(0, halfIdx), CHARACTER_ME, ...npcs.slice(halfIdx)];
    sequence.forEach(sprite => {
      const span = document.createElement('span');
      span.className = sprite === CHARACTER_ME ? 'crowd__char is-me' : 'crowd__char';
      span.style.backgroundImage = `url('${SPRITES_BASE}${sprite}.png')`;
      span.style.backgroundSize = 'contain';
      span.style.backgroundRepeat = 'no-repeat';
      span.style.backgroundPosition = 'center';
      crowd.appendChild(span);
    });
  },

  bindGameHandlers() {
    document.getElementById('box-o')?.addEventListener('click', () => Game.handleBoxClick('O'));
    document.getElementById('box-x')?.addEventListener('click', () => Game.handleBoxClick('X'));
  },

  bindEndHandlers() {
    document.getElementById('restart-btn')?.addEventListener('click', () => {
      Game.resetState();
      Game.switchView('intro');
    });
    document.getElementById('share-btn')?.addEventListener('click', () => Game.share());
  },

  showIntroStatus(message) {
    const el = document.getElementById('intro-status');
    if (el) el.textContent = message;
  },

  enableStartButton() {
    const btn = document.getElementById('start-btn');
    if (!btn) return;
    btn.disabled = false;
    btn.textContent = '시작하기 ▶';
  },

  resetState() {
    Game.clearRoundTimers();
    Game.state.currentRound = [];
    Game.state.questionIndex = 0;
    Game.state.score = 0;
    Game.state.roundIndex = 0;
    Game.state.alive = new Set();
    Game.state.playerEliminated = false;
    Game.state.playerChoice = null;
    Game.state.consecutiveCorrect = 0;   // [v3]
    Game.state.allCorrect = true;        // [v3]
    Game.state.sessionStartedAt = null;
    Game.state.timerRemaining = TIMER_DURATION_SEC;
    Game.state.answerRevealed = false;
    Game.state.npcs = [];
    Game.state.playerSprite = null;
    // arena 정리
    const sprites = document.getElementById('arena-sprites');
    if (sprites) sprites.replaceChildren();
    document.getElementById('arena')?.classList.remove('is-running', 'is-zoning');
    Game.toggleZoneFeedback(null, null);
  },

  clearRoundTimers() {
    if (Game.state.timerHandle) {
      clearInterval(Game.state.timerHandle);
      Game.state.timerHandle = null;
    }
    Game.state.npcTimerHandles.forEach(h => clearTimeout(h));
    Game.state.npcTimerHandles = [];
  },

  // === DATA (v1 100% 재사용) ===
  async fetchCSV(path) {
    const res = await fetch(path, { cache: 'no-store' });
    if (!res.ok) throw new Error(`CSV fetch ${res.status}`);
    return res.text();
  },

  parseCSV(text) {
    const lines = text.replace(/\r\n/g, '\n').split('\n').filter(l => l.trim().length > 0);
    if (lines.length === 0) return [];
    const header = Game.splitCSVLine(lines[0]).map(h => h.trim().toLowerCase());
    const idx = {
      id: header.indexOf('id'),
      question: header.indexOf('question'),
      answer: header.indexOf('answer'),
      explanation: header.indexOf('explanation'),
    };
    if (Object.values(idx).some(v => v === -1)) {
      throw new Error('CSV 헤더 누락 (id/question/answer/explanation 필요)');
    }
    return lines.slice(1).map(line => {
      const cells = Game.splitCSVLine(line);
      return {
        id: parseInt(cells[idx.id], 10),
        question: (cells[idx.question] || '').trim(),
        answer: (cells[idx.answer] || '').trim().toUpperCase(),
        explanation: (cells[idx.explanation] || '').trim(),
      };
    });
  },

  splitCSVLine(line) {
    const out = [];
    let cur = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i];
      if (inQuotes) {
        if (ch === '"' && line[i + 1] === '"') { cur += '"'; i += 1; }
        else if (ch === '"') { inQuotes = false; }
        else { cur += ch; }
      } else if (ch === '"') { inQuotes = true; }
      else if (ch === ',') { out.push(cur); cur = ''; }
      else { cur += ch; }
    }
    out.push(cur);
    return out;
  },

  validateQuestion(q) {
    if (!Number.isInteger(q.id)) return false;
    if (!q.question || typeof q.question !== 'string') return false;
    if (q.answer !== 'O' && q.answer !== 'X') return false;
    if (!q.explanation) return false;
    return true;
  },

  /** Fisher-Yates 셔플 후 앞에서 N개. 원본 배열은 변형되지 않음. */
  shuffle(arr, n) {
    const copy = arr.slice();
    for (let i = copy.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy.slice(0, n);
  },

  // === ANALYTICS (v2 페이로드 보강) ===
  parseUTM() {
    const params = new URLSearchParams(window.location.search);
    Game.state.utm = {
      source: params.get('utm_source'),
      medium: params.get('utm_medium'),
      campaign: params.get('utm_campaign'),
    };
  },

  ga(eventName, params = {}) {
    const payload = {
      ...params,
      utm_source: Game.state.utm.source || undefined,
      utm_medium: Game.state.utm.medium || undefined,
      utm_campaign: Game.state.utm.campaign || undefined,
    };
    if (typeof window.gtag === 'function') {
      window.gtag('event', eventName, payload);
    } else {
      console.debug('[OXQuiz][ga]', eventName, payload);
    }
  },

  // === GAME LOOP ===
  async startGame() {
    // [v4] 선택 카테고리 questions lazy load (캐시 활용)
    if (Game.state.selectedSlug) {
      try {
        const { questions } = await Game.loadCategoryQuestions(Game.state.selectedSlug);
        Game.state.questionPool = questions;
      } catch (err) {
        console.error('[OXQuiz] 카테고리 로드 실패:', err);
        Game.showIntroStatus('문제를 불러오지 못했어요. 다시 시도해주세요.');
        return;
      }
    }
    if (Game.state.questionPool.length < 5) {
      Game.showIntroStatus(`문제가 부족해요 (${Game.state.questionPool.length}/5 최소)`);
      return;
    }
    Game.resetState();
    Game.state.currentRound = Game.shuffle(Game.state.questionPool, Math.min(ROUND_BUFFER_SIZE, Game.state.questionPool.length));
    Game.state.sessionStartedAt = new Date().toISOString();
    Game.ga('game_start', {
      mode: 'survival_v2',
      start_alive: ALIVE_INITIAL,
      category: Game.state.selectedSlug || 'fallback',
    });
    Game.switchView('game');
    Game.spawnAllOnce();
    document.getElementById('arena')?.classList.add('is-running');
    Game.showQuestion();
  },

  /** 라운드 풀 소진 시 자동 재셔플 (실용상 거의 안 일어남) */
  ensureCurrentRound() {
    if (Game.state.questionIndex >= Game.state.currentRound.length) {
      Game.state.currentRound = Game.shuffle(Game.state.questionPool, Math.min(ROUND_BUFFER_SIZE, Game.state.questionPool.length));
      Game.state.questionIndex = 0;
    }
  },

  showQuestion() {
    Game.clearRoundTimers();
    Game.ensureCurrentRound();
    Game.state.playerChoice = null;
    Game.state.answerRevealed = false;
    Game.state.timerRemaining = TIMER_DURATION_SEC;
    Game.applyRoundTheme(Game.state.roundIndex);
    Game.renderHUD();
    Game.renderQuestion();
    Game.resetRoundVisuals();
    Game.setBoxesEnabled(true);
    Game.startTimer();
    Game.scheduleNPCDecisions();
  },

  applyRoundTheme(roundIdx) {
    const themeIndex = Math.min(
      Math.floor(roundIdx / QUESTIONS_PER_THEME),
      ROUND_THEMES.length - 1
    );
    const theme = ROUND_THEMES[themeIndex];
    const arena = document.getElementById('arena');
    if (arena && arena.dataset.theme !== theme) arena.dataset.theme = theme;
  },

  resetRoundVisuals() {
    // 라운드 시작 시 zone 활성, 박스 선택 해제, sprite 환호 해제
    const arena = document.getElementById('arena');
    if (arena) arena.classList.add('is-zoning');
    Game.toggleZoneFeedback(null, null);
    SIDES.forEach(side => {
      Game.boxEl(side)?.classList.remove('is-selected', 'is-correct-reveal', 'is-wrong-reveal');
    });
    document.getElementById('timer')?.classList.remove('is-warning');
    // alive sprite의 환호/도착 클래스 제거
    Game.state.npcs.forEach(npc => {
      if (Game.state.alive.has(npc.id)) {
        npc.element.classList.remove('is-cheering');
      }
    });
    if (Game.state.playerSprite && Game.state.alive.has(PLAYER_ID)) {
      Game.state.playerSprite.classList.remove('is-cheering');
    }
  },

  // === ARENA & SPAWN (v2 신규) ===

  /** 게임 시작 시 1회만 호출. 50개 sprite를 arena__sprites에 생성 + 무작위 위치 배치. */
  spawnAllOnce() {
    const sprites = document.getElementById('arena-sprites');
    if (!sprites) return;
    sprites.replaceChildren();
    Game.state.npcs = [];
    Game.state.alive = new Set();

    // 플레이어 sprite (id=0)
    const me = Game.makeArenaSprite(CHARACTER_ME, { isMe: true, npcId: null });
    me.id = 'sprite-me';
    sprites.appendChild(me);
    Game.state.playerSprite = me;
    Game.state.alive.add(PLAYER_ID);
    Game.assignSpriteRandomPos(me);

    const pool = Game.shuffle(CHARACTER_POOL, CHARACTER_POOL.length);
    for (let i = 0; i < NPC_COUNT; i += 1) {
      const id = i + 1;
      const sprite = pool[i % pool.length];
      const element = Game.makeArenaSprite(sprite, { isMe: false, npcId: id });
      sprites.appendChild(element);
      const baseY = SPRITE_Y_MIN_PCT + Math.random() * (SPRITE_Y_MAX_PCT - SPRITE_Y_MIN_PCT);
      const npc = {
        id,
        sprite,
        element,
        baseY,
        jitterO: (Math.random() - 0.5) * 2 * ZONE_JITTER_X_PCT,
        jitterX: (Math.random() - 0.5) * 2 * ZONE_JITTER_X_PCT,
        currentSide: null,
      };
      Game.state.npcs.push(npc);
      Game.state.alive.add(id);
      element.style.setProperty('--x', `${5 + Math.random() * 90}%`);
      element.style.setProperty('--y', `${baseY}%`);
    }
    if (SPAWN_LANE_PATTERN === 'column') Game.applyColumnSpawn();  // [v3]
  },

  // [v3] 세로 일렬 등장 — 모든 sprite를 화면 위에서 시작 → 1.5s 동안 baseY로 이동
  applyColumnSpawn() {
    Game._spawnTimers.forEach(clearTimeout);  // 재시작 시 stale timer 정리
    Game._spawnTimers = [];
    const all = [Game.state.playerSprite, ...Game.state.npcs.map(n => n.element)];
    all.forEach((el, i) => {
      if (!el) return;
      el.classList.add('is-spawning-column');
      el.style.setProperty('--spawn-delay', `${i * 18}ms`);  // 시간차로 순차 등장
      const handle = setTimeout(() => el.classList.remove('is-spawning-column'),
        SPAWN_COLUMN_DURATION_MS + i * 18);
      Game._spawnTimers.push(handle);
    });
  },
  _spawnTimers: [],

  makeArenaSprite(spriteName, { isMe, npcId }) {
    const span = document.createElement('span');
    span.className = 'character is-spawning';
    if (isMe) {
      span.classList.add('is-me');
      span.dataset.role = 'me';
    } else {
      span.dataset.role = 'npc';
      span.dataset.npcId = String(npcId);
    }
    span.style.backgroundImage = `url('${SPRITES_BASE}${spriteName}.png')`;
    span.style.setProperty('--jump-delay', `${Math.random() * 0.9}s`);
    setTimeout(() => span.classList.remove('is-spawning'), 400);
    return span;
  },

  /** 첫 spawn 직후 me 위치를 무작위로 (NPC와 동일) */
  assignSpriteRandomPos(el) {
    el.style.setProperty('--x', `${5 + Math.random() * 90}%`);
    el.style.setProperty('--y', `${SPRITE_Y_MIN_PCT + Math.random() * (SPRITE_Y_MAX_PCT - SPRITE_Y_MIN_PCT)}%`);
  },

  /** sprite를 지정 zone 중심 ±jitter 좌표로 이동 (transform 기반, CSS transition이 부드럽게 처리) */
  positionSprite(npc, side) {
    const center = side === 'O' ? ZONE_O_CENTER_X : ZONE_X_CENTER_X;
    const jitter = side === 'O' ? npc.jitterO : npc.jitterX;
    const x = center + jitter;
    npc.element.style.setProperty('--x', `${x}%`);
    npc.element.style.setProperty('--y', `${npc.baseY}%`);
    npc.currentSide = side;
  },

  // === PLAYER INPUT ===
  handleBoxClick(choice) {
    if (Game.state.answerRevealed) return;
    if (Game.state.playerEliminated || !Game.state.alive.has(PLAYER_ID)) return;
    Game.state.playerChoice = choice;
    SIDES.forEach(side => {
      Game.boxEl(side)?.classList.toggle('is-selected', side === choice);
    });
    const me = Game.state.playerSprite;
    if (!me) return;
    const center = choice === 'O' ? ZONE_O_CENTER_X : ZONE_X_CENTER_X;
    me.style.setProperty('--x', `${center}%`);
    const y = parseFloat(me.style.getPropertyValue('--y')) || 50;
    me.style.setProperty('--y', `${y}%`);
    me.dataset.side = choice;
  },

  // === NPC BEHAVIOR (v2 신규) ===

  getNpcAccuracy(roundIdx) {
    const idx = Math.min(roundIdx, NPC_ACCURACY_CURVE.length - 1);
    return NPC_ACCURACY_CURVE[idx];
  },

  /** correctAnswer + accuracy로 NPC 선택 결정 */
  npcChoose(correctAnswer, accuracy) {
    return Math.random() < accuracy ? correctAnswer : OPPOSITE[correctAnswer];
  },

  scheduleNPCDecisions() {
    Game.ensureCurrentRound();
    const q = Game.state.currentRound[Game.state.questionIndex];
    if (!q) return;
    const accuracy = Game.getNpcAccuracy(Game.state.roundIndex);
    const cutoff = TIMER_DURATION_SEC * 1000 - NPC_WAVER_CUTOFF_MS;

    const scheduleDecision = (npc, delay) => {
      if (delay >= cutoff) return;
      const handle = setTimeout(() => {
        if (Game.state.answerRevealed) return;
        Game.npcDecide(npc, Game.npcChoose(q.answer, accuracy));
      }, delay);
      Game.state.npcTimerHandles.push(handle);
    };

    Game.state.npcs.forEach(npc => {
      if (!Game.state.alive.has(npc.id)) return;
      const t1 = NPC_DECIDE_MIN_MS + Math.random() * (NPC_DECIDE_MAX_MS - NPC_DECIDE_MIN_MS);
      scheduleDecision(npc, t1);
      if (Math.random() < NPC_WAVER_PROBABILITY) {
        const t2 = t1 + NPC_WAVER_DELAY_MIN_MS + Math.random() * (NPC_WAVER_DELAY_MAX_MS - NPC_WAVER_DELAY_MIN_MS);
        scheduleDecision(npc, t2);
      }
    });
  },

  npcDecide(npc, choice) {
    if (npc.currentSide === choice) return;  // 이미 그 zone이면 no-op
    Game.positionSprite(npc, choice);
  },

  // === REVEAL & ELIMINATION (v2 신규) ===
  revealAnswer() {
    if (Game.state.answerRevealed) return;
    Game.state.answerRevealed = true;
    Game.clearRoundTimers();
    Game.setBoxesEnabled(false);

    Game.ensureCurrentRound();
    const q = Game.state.currentRound[Game.state.questionIndex];
    if (!q) return;
    const correctSide = q.answer;
    const wrongSide = OPPOSITE[correctSide];

    // 플레이어 정답 여부 (currentSide는 박스 데이터 또는 playerChoice 기준)
    // 플레이어가 한 번도 안 누르면 자동 오답 (= zone 미선택 = 탈락)
    const playerCorrect = Game.state.playerChoice === correctSide;
    const aliveBefore = Game.state.alive.size;

    // GA4: answer_o / answer_x
    Game.ga(correctSide === 'O' ? 'answer_o' : 'answer_x', {
      correct: playerCorrect,
      user_choice: Game.state.playerChoice || 'none',
      question_id: q.id,
      question_index: Game.state.questionIndex,
      round_index: Game.state.roundIndex,
      alive_before: aliveBefore,
    });

    // zone 시각 피드백
    Game.toggleZoneFeedback(correctSide, wrongSide);
    Game.boxEl(correctSide)?.classList.add('is-correct-reveal');
    Game.boxEl(wrongSide)?.classList.add('is-wrong-reveal');

    // 정답 zone 캐릭터 환호
    Game.state.npcs.forEach(npc => {
      if (Game.state.alive.has(npc.id) && npc.currentSide === correctSide) {
        npc.element.classList.add('is-cheering');
      }
    });
    if (Game.state.alive.has(PLAYER_ID) && Game.state.playerChoice === correctSide) {
      Game.state.playerSprite.classList.add('is-cheering');
    }

    // 오답 zone 캐릭터 탈락 (NPC + 플레이어 가능)
    let eliminatedCount = 0;
    Game.state.npcs.forEach(npc => {
      if (!Game.state.alive.has(npc.id)) return;
      // currentSide 가 wrongSide 이거나 null(선택 안 함) 이면 탈락
      if (npc.currentSide === wrongSide || npc.currentSide === null) {
        // [v4] 일부 NPC에 탈락 직전 비명 말풍선 (확률 30%)
        if (Math.random() < 0.3) Game.attachBubble(npc.element, 'wrong');
        Game.eliminate(npc.id, npc.element);
        eliminatedCount += 1;
      } else if (Math.random() < 0.15) {
        // [v4] 살아남은 NPC 일부에 환호 말풍선
        Game.attachBubble(npc.element, 'correct');
      }
    });
    if (Game.state.alive.has(PLAYER_ID) && !playerCorrect) {
      Game.eliminate(PLAYER_ID, Game.state.playerSprite);
      Game.state.playerEliminated = true;
      eliminatedCount += 1;
    }

    // 점수 처리
    if (playerCorrect) Game.state.score += 1;
    Game.trackCorrectness(playerCorrect);  // [v3] Grand Slam 추적

    // [v4] 시각 효과 폭발: 스탬프 + 파티클 + vignette
    Game.showStamp(playerCorrect ? 'pass' : 'fail');
    Game.spawnParticles(playerCorrect ? 'correct' : 'wrong', playerCorrect ? 14 : 10);
    if (!playerCorrect) {
      Game.toggleVignette(true);
      setTimeout(() => Game.toggleVignette(false), 800);
    }

    Game.renderHUD();
    Game.showToast(`${playerCorrect ? '✅' : '❌'} ${q.explanation}`);

    // round_advance 이벤트
    Game.ga('round_advance', {
      round_idx: Game.state.roundIndex,
      alive_count: Game.state.alive.size,
      eliminated_count: eliminatedCount,
    });

    setTimeout(() => Game.advance(), REVEAL_DELAY_MS);
  },

  eliminate(id, element) {
    if (!element) return;
    Game.state.alive.delete(id);
    Game.playEliminationEffect(element);
  },

  // === V4 ASSETS — 효과 자산 디스패처 (PROMPTS.md 매핑) ===
  // 스탬프: 큰 도장 PNG 1초 표시 후 fade-out
  showStamp(type) {
    // type: 'pass' | 'fail' | 'perfect' | 'wrong' | 'combo'
    const arena = document.getElementById('arena');
    if (!arena) return;
    const img = document.createElement('img');
    img.className = 'fx-stamp';
    img.src = `_refs/sprites/stamp-${type}.png`;
    img.alt = '';
    arena.appendChild(img);
    // 강제 reflow → 애니 시작
    void img.offsetWidth;
    img.classList.add('is-shown');
    setTimeout(() => {
      img.classList.add('is-fading');
      setTimeout(() => img.remove(), 400);
    }, 700);
  },

  // 파티클: 정답=star+coin, 오답=dust+spark, grand slam=confetti
  spawnParticles(kind, count = 12) {
    // kind: 'correct' | 'wrong' | 'grandslam'
    const arena = document.getElementById('arena');
    if (!arena) return;
    const POOLS = {
      correct:   ['particle-star-yellow', 'particle-coin-gold', 'particle-spark'],
      wrong:     ['particle-dust', 'particle-impact-burst'],
      grandslam: ['particle-confetti', 'particle-star-pink', 'particle-coin-gold', 'particle-gem'],
    };
    const pool = POOLS[kind] || POOLS.correct;
    for (let i = 0; i < count; i += 1) {
      const p = document.createElement('img');
      p.className = `fx-particle fx-particle--${kind}`;
      p.src = `_refs/sprites/${pool[i % pool.length]}.png`;
      p.alt = '';
      const angle = Math.random() * 360;
      const dist = 80 + Math.random() * 140;
      p.style.setProperty('--px', `${Math.cos(angle * Math.PI / 180) * dist}px`);
      p.style.setProperty('--py', `${Math.sin(angle * Math.PI / 180) * dist}px`);
      p.style.setProperty('--rot', `${(Math.random() - 0.5) * 720}deg`);
      p.style.setProperty('--delay', `${i * 25}ms`);
      arena.appendChild(p);
      setTimeout(() => p.remove(), 1200 + i * 25);
    }
  },

  // 말풍선: NPC sprite 머리 위 1초 표시. random emotion에서 선택
  attachBubble(element, kind) {
    if (!element) return;
    // kind: 'correct' | 'wrong' | null (랜덤)
    const POOLS = {
      correct: ['bubble-confident', 'bubble-cute', 'bubble-easy', 'bubble-go-go'],
      wrong:   ['bubble-shock', 'bubble-noooo', 'bubble-pity', 'bubble-confused', 'bubble-help', 'bubble-hmm'],
    };
    const pool = POOLS[kind] || POOLS.correct;
    const name = pool[Math.floor(Math.random() * pool.length)];
    const bubble = document.createElement('img');
    bubble.className = 'fx-bubble';
    bubble.src = `_refs/sprites/${name}.png`;
    bubble.alt = '';
    element.appendChild(bubble);
    setTimeout(() => bubble.remove(), 1100);
  },

  // Vignette: 화면 가장자리 빨간 압박감 오버레이 (타이머 위급 + reveal 직후)
  toggleVignette(on) {
    const root = document.getElementById('app');
    if (!root) return;
    root.classList.toggle('is-vignette', !!on);
  },

  // === V3 GRAND SLAM ===
  trackCorrectness(correct) {
    if (correct) {
      Game.state.consecutiveCorrect += 1;
    } else {
      Game.state.consecutiveCorrect = 0;
      Game.state.allCorrect = false;
    }
  },

  isGrandSlam() {
    return Game.state.allCorrect
      && Game.state.consecutiveCorrect >= GRAND_SLAM_THRESHOLD;
  },

  // === EFFECTS (4종 랜덤 dispatcher) ===
  playEliminationEffect(element) {
    const type = EFFECT_TYPES[Math.floor(Math.random() * EFFECT_TYPES.length)];
    element.classList.add('is-eliminated', `effect-${type}`);
    const dur = EFFECT_DURATION_MS[type] || 700;
    setTimeout(() => {
      element.style.display = 'none';
    }, dur);
  },

  // === RUNNING BACKGROUND ===
  // 활성/비활성은 startGame/endGame 에서 .is-running 토글로 처리
  // CSS @keyframes scroll-down 가 자동 처리

  // === ZONE FEEDBACK ===
  toggleZoneFeedback(correctSide, wrongSide) {
    const zoneO = document.getElementById('zone-o');
    const zoneX = document.getElementById('zone-x');
    [zoneO, zoneX].forEach(el => {
      if (el) el.classList.remove('is-correct-flash', 'is-wrong-darken');
    });
    if (correctSide) {
      const correctEl = correctSide === 'O' ? zoneO : zoneX;
      const wrongEl = wrongSide === 'O' ? zoneO : zoneX;
      correctEl?.classList.add('is-correct-flash');
      wrongEl?.classList.add('is-wrong-darken');
    }
  },

  // === END FLOW ===
  advance() {
    Game.state.roundIndex += 1;
    Game.state.questionIndex += 1;

    // 종료 조건 체크
    const result = Game.checkEndCondition();
    if (result) {
      Game.endGame(result);
      return;
    }
    Game.showQuestion();
  },

  /** 종료 조건 판정. 결과 문자열 또는 null. */
  checkEndCondition() {
    const aliveSize = Game.state.alive.size;
    const playerWin = aliveSize === 1 && Game.state.alive.has(PLAYER_ID);
    if (playerWin && Game.isGrandSlam()) return RESULT.WIN_GS;  // [v3]
    if (playerWin) return RESULT.WIN;
    if (aliveSize === 1 && !Game.state.alive.has(PLAYER_ID)) return RESULT.LOSE_SURV;
    if (aliveSize === 0) return RESULT.LOSE_SURV;  // 엣지: 모두 탈락
    if (Game.state.playerEliminated && aliveSize > 1) return RESULT.LOSE_RANK;
    return null;
  },

  endGame(result) {
    Game.clearRoundTimers();
    document.getElementById('arena')?.classList.remove('is-running', 'is-zoning');
    // [v3 bugfix] ranking = 살아남은 인원 + 1 (탈락 시 N명 살아있으면 (N+1)등).
    // 이전 공식 `50 - alive + 1`은 "죽은 순서"를 계산해 user 직관과 정반대.
    // win 케이스(alive includes player)는 GA event/COPY에서 1등 강제로 무관.
    const ranking = Game.state.alive.size + (Game.state.playerEliminated ? 1 : 0);
    const durationSec = Game.state.sessionStartedAt
      ? Math.round((Date.now() - new Date(Game.state.sessionStartedAt).getTime()) / 1000)
      : null;

    // [v3] Grand Slam은 별도 이벤트
    let eventName;
    if (result === RESULT.WIN_GS) eventName = 'game_end_grand_slam';
    else if (result === RESULT.WIN) eventName = 'game_end_win';
    else eventName = 'game_end_lose';

    Game.ga(eventName, {
      survived_rounds: Game.state.roundIndex,
      score: Game.state.score,
      duration_sec: durationSec,
      ranking: (result === RESULT.WIN || result === RESULT.WIN_GS) ? 1 : ranking,
      alive_at_death: Game.state.alive.size,
      reason: result,
      consecutive_correct: Game.state.consecutiveCorrect,  // [v3]
    });

    Game.switchView('end');
    Game.renderEnd(result, ranking);
    // [v4] 종료 화면 파티클 폭발
    if (result === RESULT.WIN_GS) {
      setTimeout(() => Game.spawnParticles('grandslam', 24), 300);
      setTimeout(() => Game.showStamp('perfect'), 600);
    } else if (result === RESULT.WIN) {
      setTimeout(() => Game.spawnParticles('correct', 16), 300);
    }
  },

  // === SHARE (v3: 4분기) ===
  buildShareText(result, ranking) {
    const url = `${location.origin}${location.pathname}`;
    const k = Game.state.score;
    const r = Game.state.roundIndex;
    if (result === RESULT.WIN_GS) {
      return `🏆 OX 서바이벌 GRAND SLAM 달성! ${GRAND_SLAM_THRESHOLD}라운드 무패 + 최후의 1인! 너도 도전 → ${url}`;
    }
    if (result === RESULT.WIN) {
      return `🥳 50명 OX 서바이벌 최후의 1인! Q.${r}까지 / 정답 ${k}개. 너도 해봐 → ${url}`;
    }
    if (result === RESULT.LOSE_SURV) {
      return `😢 OX 서바이벌, 50명 중 ${ranking}등 했어 (다른 1명이 살아남음). 정답 ${k}개. 너도 해봐 → ${url}`;
    }
    return `OX 서바이벌 50명 중 ${ranking}등 했어. Q.${r}에서 탈락 / 정답 ${k}개. 너도 해봐 → ${url}`;
  },

  async share() {
    const result = document.getElementById('end')?.dataset.result || RESULT.WIN;
    const rankingText = document.getElementById('end-secondary')?.dataset.ranking;
    const ranking = rankingText ? parseInt(rankingText, 10) : 1;
    const text = Game.buildShareText(result, ranking);
    const shareData = {
      title: '넌센스 OX 퀴즈 — 서바이벌',
      text,
      url: `${location.origin}${location.pathname}`,
    };
    let method = 'unknown';
    try {
      if (navigator.share && navigator.canShare?.(shareData)) {
        await navigator.share(shareData);
        method = 'webshare';
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        method = 'clipboard';
        Game.showToast('링크가 복사됐어요 📋');
      } else {
        window.prompt('이 링크를 복사하세요', text);
        method = 'prompt';
      }
      const shareResult = result === RESULT.WIN_GS ? 'grand_slam'
        : result.startsWith('lose') ? 'lose' : 'win';
      Game.ga('share_click', { method, result: shareResult });
    } catch (err) {
      if (err && err.name !== 'AbortError') {
        console.warn('[OXQuiz] 공유 실패:', err);
        Game.showToast('공유에 실패했어요 😢');
      }
    }
  },

  // === RENDER ===
  switchView(name) {
    Game.state.view = name;
    document.querySelectorAll('.view').forEach(el => { el.hidden = true; });
    document.getElementById(name)?.removeAttribute('hidden');
  },

  renderHUD() {
    const qNum = document.getElementById('q-num');
    const aliveCount = document.getElementById('alive-count');
    const aliveTotal = document.getElementById('alive-total');
    const aliveDisplay = document.getElementById('alive-display');
    const score = document.getElementById('score');
    if (qNum) qNum.textContent = String(Game.state.roundIndex + 1);
    const n = Game.state.alive.size;
    if (aliveCount) aliveCount.textContent = String(n);
    if (aliveTotal) aliveTotal.textContent = String(ALIVE_INITIAL);
    if (score) score.textContent = String(Game.state.score);
    // 살아남음 색상 단계
    if (aliveDisplay) {
      aliveDisplay.classList.toggle('is-warning', n <= 30 && n > 10);
      aliveDisplay.classList.toggle('is-danger', n <= 10);
    }
  },

  renderQuestion() {
    Game.ensureCurrentRound();
    const q = Game.state.currentRound[Game.state.questionIndex];
    const el = document.getElementById('question');
    if (el && q) el.textContent = q.question;
  },

  renderEnd(result, ranking) {
    const root = document.getElementById('end');
    if (!root) return;
    const r = Game.state.roundIndex;
    const k = Game.state.score;
    const COPY = {
      [RESULT.WIN_GS]:    { title: 'GRAND SLAM!',     emoji: '👑', primary: `${GRAND_SLAM_THRESHOLD}라운드 무패 + 최후의 1인!`, secondary: `⭐ ${k} · 50명 중 1등 (perfect)` },
      [RESULT.WIN]:       { title: '최후의 1인!',      emoji: '🥳', primary: `Q.${r}까지 살아남았다`, secondary: `정답 ${k}개 · 50명 중 1등` },
      [RESULT.LOSE_SURV]: { title: '아쉬워...',         emoji: '😢', primary: '너만 빼고 살아남았어',     secondary: `정답 ${k}개 · 50명 중 ${ranking}등` },
      [RESULT.LOSE_RANK]: { title: `${ranking}등!`,    emoji: '😅', primary: `Q.${r}에서 탈락`,         secondary: `정답 ${k}개 · 50명 중 ${ranking}등` },
    };
    const copy = COPY[result] || COPY[RESULT.LOSE_RANK];
    root.dataset.result = result;

    const setText = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };
    setText('end-title', copy.title);
    setText('end-emoji', copy.emoji);
    setText('end-primary', copy.primary);
    const secondary = document.getElementById('end-secondary');
    if (secondary) {
      secondary.textContent = copy.secondary;
      secondary.dataset.ranking = String(ranking);
    }
  },

  renderError(message) {
    Game.switchView('error');
    const errorMessage = document.getElementById('error-message');
    if (errorMessage && message) errorMessage.textContent = message;
  },

  setBoxesEnabled(enabled) {
    SIDES.forEach(side => {
      const el = Game.boxEl(side);
      if (el) el.disabled = !enabled;
    });
  },

  renderTimer() {
    const el = document.getElementById('timer-num');
    const remaining = Math.max(0, Game.state.timerRemaining);
    if (el) el.textContent = String(remaining);
    // [v4] 시계 이미지 동적 교체 (남은 초에 따라)
    const clockEl = document.getElementById('timer-clock');
    if (clockEl) {
      const variant = remaining <= 1 ? 'critical' : remaining <= 2 ? 'warning' : 'calm';
      const newSrc = `_refs/sprites/timer-clock-${variant}.png`;
      if (!clockEl.src.endsWith(`timer-clock-${variant}.png`)) {
        clockEl.src = newSrc;
      }
    }
  },

  showToast(message) {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = message;
    el.removeAttribute('hidden');
    clearTimeout(Game._toastTimer);
    Game._toastTimer = setTimeout(() => { el.setAttribute('hidden', ''); }, TOAST_DURATION_MS);
  },

  _toastTimer: null,

  // === RENDER UTILS ===
  boxEl(side) { return document.getElementById(side === 'O' ? 'box-o' : 'box-x'); },

  startTimer() {
    Game.renderTimer();
    Game.state.timerHandle = setInterval(() => {
      Game.state.timerRemaining -= 1;
      Game.renderTimer();
      if (Game.state.timerRemaining <= 2) {
        document.getElementById('timer')?.classList.add('is-warning');
      }
      if (Game.state.timerRemaining <= 0) {
        clearInterval(Game.state.timerHandle);
        Game.state.timerHandle = null;
        Game.revealAnswer();
      }
    }, 1000);
  },

  // === [v2 M10] QA 시뮬레이션 (콘솔 호출용) ===
  // window.Game.simulate(100) 으로 NPC 정답률 곡선 검증
  // [v3] simulate에 grandSlams 카운트 + 플레이어 정답률 파라미터 추가.
  // 기본 0.65 = SC-V3-01의 평균 사용자 (default invocation = success criteria 검증)
  simulate(n = 100, playerAccuracy = 0.65) {
    const results = { rounds: [], wins: 0, grandSlams: 0, losesByPlayer: 0, losesBySurvivor: 0, exceeded30: 0 };
    for (let i = 0; i < n; i += 1) {
      let alive = ALIVE_INITIAL, round = 0, playerAlive = true;
      let playerAllCorrect = true;
      while (alive > 1 && round < 30) {
        const acc = Game.getNpcAccuracy(round);
        const npcAlive = alive - (playerAlive ? 1 : 0);
        const npcDead = Math.round(npcAlive * (1 - acc));
        const playerCorrect = Math.random() < playerAccuracy;
        if (playerAlive && !playerCorrect) {
          playerAlive = false;
          playerAllCorrect = false;
          alive = npcAlive - npcDead;
          results.losesByPlayer += 1;
          results.rounds.push(round + 1);
          break;
        }
        alive = npcAlive - npcDead + (playerAlive ? 1 : 0);
        round += 1;
      }
      if (alive <= 1) {
        if (alive === 1 && playerAlive) {
          results.wins += 1;
          if (playerAllCorrect && round >= GRAND_SLAM_THRESHOLD) results.grandSlams += 1;
        } else {
          results.losesBySurvivor += 1;
        }
        results.rounds.push(round);
      }
      if (round >= 30) results.exceeded30 += 1;
    }
    const avgRound = results.rounds.reduce((a, b) => a + b, 0) / results.rounds.length;
    console.log('[OXQuiz][simulate]', {
      n, playerAccuracy, avgRound: avgRound.toFixed(2),
      wins: results.wins,
      grandSlams: results.grandSlams,
      grandSlamPct: (results.grandSlams / n * 100).toFixed(2) + '%',
      losesByPlayer: results.losesByPlayer,
      losesBySurvivor: results.losesBySurvivor,
      exceeded30: results.exceeded30,
    });
    return results;
  },
};

// ── ENTRY ──
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => Game.init());
} else {
  Game.init();
}

// ── EXPOSE FOR DEBUG (개발 콘솔에서 window.Game 으로 접근 가능) ──
window.Game = Game;
