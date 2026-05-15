/* =================================================================
   OX 서바이벌 — audio.js (Web Audio API 합성, 외부 자산 0)
   8-bit 톤 긴장감 BGM + 클릭 / 정답 / 오답 / 탈락 SFX + 음소거 토글
   ================================================================= */
'use strict';

const AudioMgr = (() => {
  let ctx = null;
  let masterGain = null;
  let bgmTimer = null;
  let bgmStep = 0;
  let muted = false;
  const LS_KEY = 'oxquiz.mute';

  // 초기 mute 상태 (LocalStorage)
  try {
    const stored = localStorage.getItem(LS_KEY);
    if (stored === '1') muted = true;
  } catch (e) {}

  function ensureCtx() {
    if (ctx) return ctx;
    try {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      masterGain = ctx.createGain();
      masterGain.gain.value = muted ? 0 : 0.6;
      masterGain.connect(ctx.destination);
    } catch (e) {
      ctx = null;
    }
    return ctx;
  }

  function resumeCtx() {
    const c = ensureCtx();
    if (c && c.state === 'suspended') c.resume();
    return c;
  }

  /**
   * 단일 음을 재생.
   * @param {number} freq Hz
   * @param {number} duration sec
   * @param {string} type 'square'|'sawtooth'|'triangle'|'sine'
   * @param {number} vol 0~1
   * @param {number} when 시작 시각 offset (sec)
   * @param {object} envelope { attack, release } sec
   */
  function tone(freq, duration, type = 'square', vol = 0.18, when = 0, envelope = {}) {
    const c = ensureCtx();
    if (!c || muted) return;
    const start = c.currentTime + when;
    const stop = start + duration;
    const osc = c.createOscillator();
    const g = c.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    const attack = envelope.attack ?? 0.005;
    const release = envelope.release ?? 0.04;
    g.gain.setValueAtTime(0, start);
    g.gain.linearRampToValueAtTime(vol, start + attack);
    g.gain.setValueAtTime(vol, stop - release);
    g.gain.linearRampToValueAtTime(0.0001, stop);
    osc.connect(g).connect(masterGain);
    osc.start(start);
    osc.stop(stop + 0.02);
  }

  // 노이즈 — 탈락 효과음용
  function noise(duration, vol = 0.2, when = 0, lowpass = 800) {
    const c = ensureCtx();
    if (!c || muted) return;
    const start = c.currentTime + when;
    const bufferSize = Math.floor(c.sampleRate * duration);
    const buf = c.createBuffer(1, bufferSize, c.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) data[i] = (Math.random() * 2 - 1);
    const src = c.createBufferSource();
    src.buffer = buf;
    const filter = c.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = lowpass;
    const g = c.createGain();
    g.gain.setValueAtTime(vol, start);
    g.gain.exponentialRampToValueAtTime(0.001, start + duration);
    src.connect(filter).connect(g).connect(masterGain);
    src.start(start);
    src.stop(start + duration + 0.02);
  }

  // === SFX ===
  function playClick() {
    tone(440, 0.06, 'square', 0.12);
    tone(880, 0.04, 'square', 0.08, 0.02);
  }

  function playCorrect() {
    // 상승 화음 — 도-미-솔 (C5-E5-G5)
    tone(523.25, 0.10, 'triangle', 0.20);
    tone(659.25, 0.10, 'triangle', 0.20, 0.08);
    tone(783.99, 0.18, 'triangle', 0.22, 0.16);
  }

  function playWrong() {
    // 하강 — 미-도 단조 톤
    tone(311.13, 0.08, 'sawtooth', 0.18);
    tone(207.65, 0.18, 'sawtooth', 0.18, 0.08);
  }

  function playElim() {
    // 탈락 — 노이즈 + 저음 하강
    noise(0.22, 0.18, 0, 600);
    tone(196.00, 0.10, 'sawtooth', 0.22, 0.04);
    tone(146.83, 0.20, 'sawtooth', 0.22, 0.14);
    tone(98.00, 0.30, 'sawtooth', 0.22, 0.32);
  }

  function playStart() {
    // 게임 시작 팡파레
    tone(523.25, 0.08, 'square', 0.18);
    tone(659.25, 0.08, 'square', 0.18, 0.08);
    tone(783.99, 0.08, 'square', 0.20, 0.16);
    tone(1046.50, 0.20, 'square', 0.22, 0.24);
  }

  function playVictory() {
    // 승리 — 5음 상승
    const notes = [523.25, 659.25, 783.99, 1046.50, 1318.51];
    notes.forEach((f, i) => tone(f, 0.18, 'triangle', 0.22, i * 0.12));
  }

  // === BGM ===
  // 8-bit 긴장감 루프 (16스텝, 약 4.8초, A 단조 기반)
  // 매 스텝: 베이스 + (옵션) 멜로디
  // 단조 음계 A♭, B♭, C, D♭, E♭, E, G — 어두운 톤
  const BGM_STEP_MS = 280;
  const BGM_BASS = [
    // [freq, type, vol]
    [110.00, 'sawtooth', 0.08],  // A2
    [0, null, 0],
    [110.00, 'sawtooth', 0.08],  // A2
    [0, null, 0],
    [123.47, 'sawtooth', 0.08],  // B2
    [0, null, 0],
    [98.00, 'sawtooth', 0.08],   // G2
    [0, null, 0],
    [110.00, 'sawtooth', 0.08],  // A2
    [0, null, 0],
    [82.41, 'sawtooth', 0.08],   // E2
    [0, null, 0],
    [87.31, 'sawtooth', 0.08],   // F2
    [0, null, 0],
    [82.41, 'sawtooth', 0.08],   // E2
    [82.41, 'sawtooth', 0.08],   // E2 (텐션)
  ];
  // 멜로디는 일부 스텝에만 (긴장감)
  const BGM_MELODY = {
    0: [523.25, 'square', 0.06],   // C5
    4: [493.88, 'square', 0.06],   // B4
    8: [466.16, 'square', 0.06],   // B♭4
    12: [493.88, 'square', 0.06],  // B4
    14: [523.25, 'square', 0.07],  // C5
  };

  function startBGM() {
    stopBGM();
    if (muted) return;
    resumeCtx();
    bgmStep = 0;
    bgmTimer = setInterval(() => {
      if (muted) return;
      const bassEntry = BGM_BASS[bgmStep];
      if (bassEntry && bassEntry[1]) {
        tone(bassEntry[0], BGM_STEP_MS / 1000 * 0.9, bassEntry[1], bassEntry[2]);
      }
      const mel = BGM_MELODY[bgmStep];
      if (mel) {
        tone(mel[0], BGM_STEP_MS / 1000 * 1.4, mel[1], mel[2]);
      }
      // 매 4스텝마다 하이햇 같은 노이즈 (8-bit hat)
      if (bgmStep % 4 === 2) {
        noise(0.04, 0.06, 0, 4000);
      }
      bgmStep = (bgmStep + 1) % BGM_BASS.length;
    }, BGM_STEP_MS);
  }

  function stopBGM() {
    if (bgmTimer) {
      clearInterval(bgmTimer);
      bgmTimer = null;
    }
  }

  // === Mute toggle ===
  function setMute(v) {
    muted = !!v;
    try { localStorage.setItem(LS_KEY, muted ? '1' : '0'); } catch (e) {}
    if (masterGain) {
      masterGain.gain.value = muted ? 0 : 0.6;
    }
    if (muted) {
      stopBGM();
    }
    // 버튼 UI 동기화
    document.querySelectorAll('[data-mute-toggle]').forEach((b) => {
      b.setAttribute('aria-pressed', String(muted));
      b.dataset.muted = muted ? '1' : '0';
      const lbl = b.querySelector('[data-mute-icon]');
      if (lbl) lbl.textContent = muted ? '🔇' : '🔊';
    });
  }

  function toggleMute() {
    setMute(!muted);
    return muted;
  }

  function isMuted() { return muted; }

  // 페이지 로드 시 UI 동기화 (DOMContentLoaded 후 호출)
  function bindUI() {
    document.querySelectorAll('[data-mute-toggle]').forEach((btn) => {
      btn.setAttribute('aria-pressed', String(muted));
      btn.dataset.muted = muted ? '1' : '0';
      const lbl = btn.querySelector('[data-mute-icon]');
      if (lbl) lbl.textContent = muted ? '🔇' : '🔊';
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleMute();
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindUI);
  } else {
    bindUI();
  }

  return {
    playClick, playCorrect, playWrong, playElim, playStart, playVictory,
    startBGM, stopBGM,
    setMute, toggleMute, isMuted,
    resumeCtx,
  };
})();
window.AudioMgr = AudioMgr;
