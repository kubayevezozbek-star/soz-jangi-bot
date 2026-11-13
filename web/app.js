// ==========================================
// SO'Z JANGI - TELEGRAM MINI APP CLIENT
// ==========================================

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
  tg.ready();
}

// User state with persistent unique ID fallback (prevents multi-device collision)
function getAppUser() {
  let uid = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
  let fname = window.Telegram?.WebApp?.initDataUnsafe?.user?.first_name;
  let uname = window.Telegram?.WebApp?.initDataUnsafe?.user?.username || "";

  if (!uid) {
    let stored = localStorage.getItem('soz_jangi_uid');
    if (!stored) {
      stored = Math.floor(10000000 + Math.random() * 90000000);
      localStorage.setItem('soz_jangi_uid', stored);
    }
    uid = parseInt(stored);
    fname = localStorage.getItem('soz_jangi_uname') || `O'yinchi #${String(uid).slice(-4)}`;
  }

  return { id: uid, first_name: fname, username: uname };
}

const currentUser = getAppUser();

let userStats = {
  score: 0,
  games_played: 0,
  wins: 0,
  correct_count: 0,
  wrong_count: 0
};

// Audio Synthesizer (Zero External Dependencies)
let audioCtx = null;
let soundEnabled = true;

function initAudio() {
  if (!audioCtx) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) audioCtx = new AudioContext();
  }
}

function toggleSound() {
  soundEnabled = !soundEnabled;
  document.getElementById('soundIcon').textContent = soundEnabled ? '🔊' : '🔇';
}

function playTone(freq, type, duration, delay = 0) {
  if (!soundEnabled) return;
  initAudio();
  if (!audioCtx) return;
  setTimeout(() => {
    try {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      gain.gain.setValueAtTime(0.18, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + duration);
    } catch (e) {}
  }, delay);
}

function soundCorrect() {
  playTone(523.25, 'triangle', 0.12, 0);   // C5
  playTone(659.25, 'triangle', 0.22, 90);  // E5
  playTone(783.99, 'triangle', 0.35, 180); // G5
  haptic('success');
}

function soundWrong() {
  playTone(220, 'sawtooth', 0.18, 0);
  playTone(175, 'sawtooth', 0.28, 120);
  haptic('error');
}

function soundTick() {
  playTone(750, 'sine', 0.04, 0);
  haptic('light');
}

function soundWin() {
  playTone(523, 'triangle', 0.15, 0);
  playTone(659, 'triangle', 0.15, 120);
  playTone(783, 'triangle', 0.15, 240);
  playTone(1046, 'triangle', 0.45, 360);
  haptic('success');
}

function haptic(type = 'light') {
  try {
    if (tg?.HapticFeedback) {
      if (type === 'light') tg.HapticFeedback.impactOccurred('light');
      else if (type === 'medium') tg.HapticFeedback.impactOccurred('medium');
      else if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
      else if (type === 'error') tg.HapticFeedback.notificationOccurred('error');
    }
  } catch (e) {}
}

// Navigation between tabs
function switchTab(tabName) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));

  const targetView = document.getElementById(`view-${tabName}`);
  const targetNav = document.getElementById(`nav-${tabName}`);
  if (targetView) targetView.classList.add('active');
  if (targetNav) targetNav.classList.add('active');

  haptic('light');

  // Load specific tab data
  if (tabName === 'vocab') loadVocabCatalog();
  if (tabName === 'leaderboard') loadLeaderboard();
  if (tabName === 'profile') loadProfileView();
}

// App Initialization
async function initApp() {
  document.getElementById('headerUserName').textContent = currentUser.first_name;
  document.getElementById('profileFullName').textContent = currentUser.first_name;
  if (currentUser.first_name) {
    document.getElementById('headerAvatar').textContent = currentUser.first_name.charAt(0).toUpperCase();
    document.getElementById('profileAvatar').textContent = currentUser.first_name.charAt(0).toUpperCase();
  }

  await fetchUserStats();

  // Check URL params for room deep-link
  const urlParams = new URLSearchParams(window.location.search);
  const roomParam = urlParams.get('room');
  if (roomParam) {
    switchTab('rooms');
    document.getElementById('joinCodeInput').value = roomParam;
    joinRoomByCode(roomParam);
  }
}

async function fetchUserStats() {
  try {
    const res = await fetch(`/api/user/${currentUser.id}`);
    const data = await res.json();
    if (data) {
      userStats = data;
      document.getElementById('headerUserScore').textContent = data.score || 0;
      document.getElementById('homeScoreVal').textContent = data.score || 0;
      document.getElementById('homeGamesVal').textContent = data.games_played || 0;
      document.getElementById('homeWinsVal').textContent = data.wins || 0;

      // Calculate rank title
      let rankTitle = "Boshlovchi";
      if (data.score >= 500) rankTitle = "Lug'at Qiroli 👑";
      else if (data.score >= 250) rankTitle = "So'z Ustasi ⚡";
      else if (data.score >= 100) rankTitle = "Tajribali Jangchi ⚔️";
      else if (data.score >= 30) rankTitle = "Faol O'rganuvchi 📖";

      document.getElementById('userRankBadge').textContent = rankTitle;
    }
  } catch (e) {}
}

// ==========================================
// MULTIPLAYER ROOM & WEBSOCKET ENGINE
// ==========================================

let activeRoomCode = null;
let currentMaxPlayers = 2;
let currentQMode = 'choice'; // 'choice' (strictly test) or 'written' (strictly written)
let currentTimeLimit = 15;   // 10, 15, 20, 25, 30
let ws = null;
let timerInterval = null;
let currentQuestion = null;

function selectMaxPlayers(num) {
  currentMaxPlayers = num;
  document.querySelectorAll('#playerChips .chip').forEach((c, idx) => {
    c.classList.toggle('active', idx === (num - 2));
  });
  haptic('light');
}

function selectQMode(mode) {
  currentQMode = mode;
  const chipChoice = document.getElementById('chipModeChoice');
  const chipWritten = document.getElementById('chipModeWritten');
  if (chipChoice) chipChoice.classList.toggle('active', mode === 'choice');
  if (chipWritten) chipWritten.classList.toggle('active', mode === 'written');
  haptic('light');
}

function selectTimerLimit(seconds) {
  currentTimeLimit = seconds;
  document.querySelectorAll('#timerChips .chip').forEach(c => {
    c.classList.toggle('active', c.textContent.includes(seconds + ' soniya'));
  });
  haptic('light');
}

// Create Room
async function handleCreateRoomClick() {
  const day = parseInt(document.getElementById('roomDayInput').value) || 1;
  try {
    const res = await fetch('/api/room/create', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        user_id: currentUser.id,
        first_name: currentUser.first_name,
        username: currentUser.username,
        max_players: currentMaxPlayers,
        day: day,
        q_mode: currentQMode,
        time_limit: currentTimeLimit
      })
    });
    const data = await res.json();
    if (data.code) {
      connectToGameWebSocket(data.code, false, data.room);
    }
  } catch (e) {
    alert("Xona yaratishda xatolik yuz berdi");
  }
}

// Solo Mode: Instant 1-player room with selected mode and timer
async function startSoloGame() {
  const randomDay = Math.floor(Math.random() * 96) + 1;
  try {
    const res = await fetch('/api/room/create', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        user_id: currentUser.id,
        first_name: currentUser.first_name,
        username: currentUser.username,
        max_players: 1,
        day: randomDay,
        q_mode: currentQMode,
        time_limit: currentTimeLimit
      })
    });
    const data = await res.json();
    if (data.code) {
      connectToGameWebSocket(data.code, true, data.room);
    }
  } catch (e) {
    alert("Solo o'yinni boshlashda xatolik");
  }
}

// Join Room By Code
async function joinRoomByCode(codeToJoin) {
  const code = (codeToJoin || document.getElementById('joinCodeInput').value).trim();
  if (!code) return;

  try {
    const res = await fetch('/api/room/join', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        code: code,
        user_id: currentUser.id,
        first_name: currentUser.first_name,
        username: currentUser.username
      })
    });
    const data = await res.json();
    if (data.success) {
      connectToGameWebSocket(code, false, data.room);
    } else {
      alert(data.error || "Xona topilmadi yoki to'lgan");
    }
  } catch (e) {
    alert("Xonaga ulanishda xatolik");
  }
}

// WebSocket Connection
function connectToGameWebSocket(roomCode, autoStart = false, initialRoom = null) {
  activeRoomCode = roomCode;
  if (ws) {
    try { ws.close(); } catch(e) {}
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/${roomCode}/${currentUser.id}`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("WebSocket connected to room:", roomCode);
    if (autoStart) {
      ws.send(JSON.stringify({type: 'start_game'}));
    }
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleServerEvent(msg);
    } catch(e) {}
  };

  ws.onclose = () => {
    console.log("WebSocket disconnected");
  };

  showLobby(initialRoom || roomCode);
}

function showLobby(roomData) {
  switchTab('rooms');
  document.getElementById('roomSetupCard').style.display = 'none';
  document.getElementById('roomJoinCard').style.display = 'none';
  document.getElementById('roomLobbyCard').style.display = 'block';

  const code = typeof roomData === 'object' ? roomData.code : roomData;
  document.getElementById('lobbyDisplayCode').textContent = code;

  const day = (typeof roomData === 'object' && roomData.day) ? roomData.day : (document.getElementById('roomDayInput').value || 1);
  const qMode = (typeof roomData === 'object' && roomData.q_mode) ? roomData.q_mode : currentQMode;
  const tLimit = (typeof roomData === 'object' && roomData.time_limit) ? roomData.time_limit : currentTimeLimit;

  document.getElementById('lobbyDayBadge').textContent = `📅 ${day}-kun`;
  document.getElementById('lobbyModeBadge').textContent = qMode === 'choice' ? '🔘 Test (Variantli)' : '✍️ Yozma Tarjima';
  document.getElementById('lobbyTimerBadge').textContent = `⏱️ ${tLimit}s`;

  const btn = document.getElementById('btnLobbyStart');
  if (btn) {
    btn.disabled = false;
    btn.innerHTML = '🚀 O\'YINNI BOSHLASH';
  }
}

function closeLobby() {
  if (ws) {
    try { ws.close(); } catch(e) {}
  }
  document.getElementById('roomSetupCard').style.display = 'block';
  document.getElementById('roomJoinCard').style.display = 'block';
  document.getElementById('roomLobbyCard').style.display = 'none';
}

function shareRoomLink() {
  const code = document.getElementById('lobbyDisplayCode').textContent;
  const shareText = `🎮 Kel, 'So'z Jangi'da bellashamiz!\nXona kodi: ${code}\nUlanish: https://t.me/soz_jangi_bot?start=room_${code}`;
  if (tg && tg.openTelegramLink) {
    tg.openTelegramLink(`https://t.me/share/url?url=https://t.me/soz_jangi_bot?start=room_${code}&text=${encodeURIComponent(shareText)}`);
  } else {
    navigator.clipboard?.writeText(shareText);
    alert("Xona havolasi nusxalandi! Do'stlaringizga yuboring.");
  }
}

function triggerReadyOrStart() {
  haptic('medium');
  const btn = document.getElementById('btnLobbyStart');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '⏳ O\'yin boshlanmoqda...';
  }

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({type: 'start_game'}));
  } else if (activeRoomCode) {
    connectToGameWebSocket(activeRoomCode, true);
  }
}

// Server Message Handler
function handleServerEvent(msg) {
  switch (msg.type) {
    case 'room_update':
      if (msg.room) {
        showLobby(msg.room);
      }
      renderLobbyPlayers(msg.players);
      break;
    case 'new_question':
      launchNewQuestion(msg.question, msg.room);
      break;
    case 'answer_result':
      showAnswerResult(msg);
      break;
    case 'round_ended':
      showRoundEnded(msg);
      break;
    case 'player_answered':
      renderOpponentProgress(msg.user_id);
      break;
    case 'game_over':
      renderGameOverPodium(msg);
      break;
  }
}

function renderLobbyPlayers(players) {
  const listEl = document.getElementById('lobbyPlayerList');
  if (!listEl) return;
  listEl.innerHTML = '';

  players.forEach(p => {
    const item = document.createElement('div');
    item.className = 'player-item';
    item.innerHTML = `
      <div class="player-info">
        <div class="player-avatar">${p.first_name.charAt(0).toUpperCase()}</div>
        <div>
          <div style="font-weight: 700; font-size: 14.5px;">${p.first_name}</div>
          <div style="font-size: 11.5px; color: var(--accent);">⭐ ${p.score} ball</div>
        </div>
      </div>
      <span class="ready-tag ${p.is_ready ? 'ready' : 'waiting'}">
        ${p.is_ready ? 'Tayyor ✓' : 'Kutilmoqda...'}
      </span>
    `;
    listEl.appendChild(item);
  });
}

// ==========================================
// BATTLE ARENA (THE LIVE GAMEPLAY)
// ==========================================

function launchNewQuestion(q, room) {
  currentQuestion = q;
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-battle').classList.add('active');

  const fbBox = document.getElementById('battleFeedbackBox');
  fbBox.className = 'feedback-box';
  fbBox.textContent = '';

  document.getElementById('battleQNumber').textContent = q.number;
  document.getElementById('battleQTotal').textContent = q.total;
  document.getElementById('battleWordEn').textContent = q.en;
  document.getElementById('battleWordPron').textContent = q.pron ? `[${q.pron}]` : '';

  const isChoice = (q.type === 'choice');
  document.getElementById('battleModeTag').textContent = isChoice 
    ? `4 talik Test (⏱️ ${Math.round(q.time_limit)}s)` 
    : `Yozma Tarjima (⏱️ ${Math.round(q.time_limit)}s)`;
  document.getElementById('choicesStack').style.display = isChoice ? 'flex' : 'none';
  document.getElementById('writtenWrap').style.display = isChoice ? 'none' : 'flex';

  if (isChoice) {
    const container = document.getElementById('choicesStack');
    container.innerHTML = '';
    q.options.forEach((opt, idx) => {
      const letter = String.fromCharCode(65 + idx);
      const card = document.createElement('button');
      card.className = 'choice-card';
      card.innerHTML = `<span><b>${letter})</b> ${opt}</span>`;
      card.onclick = () => submitChoice(opt, card);
      container.appendChild(card);
    });
  } else {
    const wInput = document.getElementById('battleWrittenInput');
    wInput.value = '';
    wInput.disabled = false;
    setTimeout(() => wInput.focus(), 150);
  }

  // Live player pills
  const opponentsDiv = document.getElementById('battleOpponentsRow');
  opponentsDiv.innerHTML = '';
  if (room && room.players) {
    room.players.forEach(p => {
      const pill = document.createElement('span');
      pill.id = `pill_${p.user_id}`;
      pill.className = 'round-pill';
      pill.style.fontSize = '12px';
      pill.style.padding = '3px 8px';
      pill.textContent = `${p.first_name}: ${p.score}`;
      opponentsDiv.appendChild(pill);
    });
  }

  startCountdown(q.time_limit);
}

function startCountdown(seconds) {
  clearInterval(timerInterval);
  const fill = document.getElementById('battleTimerFill');
  const num = document.getElementById('battleTimerNum');
  let remaining = seconds;
  const total = seconds;

  fill.style.width = '100%';
  fill.classList.remove('warning');
  num.textContent = remaining;

  const startMs = Date.now();
  timerInterval = setInterval(() => {
    const elapsed = (Date.now() - startMs) / 1000;
    const left = Math.max(0, total - elapsed);
    const pct = (left / total) * 100;
    fill.style.width = `${pct}%`;
    num.textContent = Math.ceil(left);

    if (left <= 3.2) {
      fill.classList.add('warning');
      soundTick();
    }

    if (left <= 0) {
      clearInterval(timerInterval);
    }
  }, 100);
}

function submitChoice(opt, cardEl) {
  document.querySelectorAll('.choice-card').forEach(c => c.disabled = true);
  cardEl.style.borderColor = 'var(--primary)';

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'submit_answer',
      answer: opt
    }));
  }
}

function submitWrittenAnswer() {
  const input = document.getElementById('battleWrittenInput');
  const val = input.value.trim();
  if (!val) return;
  input.disabled = true;

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'submit_answer',
      answer: val
    }));
  }
}

document.getElementById('battleWrittenInput').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') submitWrittenAnswer();
});

function showAnswerResult(res) {
  const fb = document.getElementById('battleFeedbackBox');
  if (res.is_correct) {
    soundCorrect();
    fb.className = 'feedback-box show correct';
    fb.innerHTML = `✓ TO'G'RI! +${res.points} ball qo'shildi! 🎉`;
  } else {
    soundWrong();
    fb.className = 'feedback-box show wrong';
    fb.innerHTML = `✗ NOTO'G'RI! -1 ball jarima.<br><span style="font-size:13px; font-weight:normal;">To'g'ri javob: <b>${res.correct_answer}</b></span>`;
  }
  document.getElementById('headerUserScore').textContent = res.new_score;
}

function showRoundEnded(data) {
  clearInterval(timerInterval);
  if (data.correct_option_index >= 0) {
    const cards = document.querySelectorAll('.choice-card');
    if (cards[data.correct_option_index]) {
      cards[data.correct_option_index].classList.add('correct');
    }
  }
}

function renderOpponentProgress(userId) {
  const pill = document.getElementById(`pill_${userId}`);
  if (pill) {
    pill.style.borderColor = 'var(--success)';
    pill.innerHTML += ' ✓';
  }
}

// ==========================================
// GAME OVER & PODIUM & CONFETTI
// ==========================================

function renderGameOverPodium(data) {
  clearInterval(timerInterval);
  soundWin();

  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-gameover').classList.add('active');

  const podium = document.getElementById('podiumWrap');
  podium.innerHTML = '';

  const lb = data.leaderboard;
  // Order 2nd, 1st, 3rd for realistic sports podium
  const arrangeOrder = [1, 0, 2];
  arrangeOrder.forEach(idx => {
    if (lb[idx]) {
      const p = lb[idx];
      const col = document.createElement('div');
      col.className = `podium-col podium-rank-${p.rank}`;
      col.innerHTML = `
        <div class="podium-medal">${p.medal}</div>
        <div class="podium-player-name">${p.name}</div>
        <div class="podium-player-score">${p.score} ⭐</div>
        <div class="podium-pedestal">${p.rank}</div>
      `;
      podium.appendChild(col);
    }
  });

  // Mistakes of current user
  const me = lb.find(x => x.user_id === currentUser.id);
  const mBox = document.getElementById('gameOverMistakesCard');
  const mList = document.getElementById('gameOverMistakesList');
  if (me && me.mistakes && me.mistakes.length > 0) {
    mBox.style.display = 'block';
    mList.innerHTML = '';
    me.mistakes.forEach(m => {
      const item = document.createElement('div');
      item.style.padding = '8px 0';
      item.style.borderBottom = '1px solid var(--card-border)';
      item.style.fontSize = '13px';
      item.innerHTML = `
        <div style="font-weight:700; color:white;">${m.en} ${m.pron ? `(${m.pron})` : ''}</div>
        <div>Siz: <span style="color:var(--danger); text-decoration:line-through;">${m.user_answer}</span> ➔ To'g'ri: <b style="color:var(--success);">${m.correct}</b></div>
      `;
      mList.appendChild(item);
    });
  } else {
    mBox.style.display = 'none';
  }

  fetchUserStats();
  fireConfetti();
}

// Canvas Confetti
function fireConfetti() {
  const canvas = document.getElementById('confettiCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const particles = [];
  const colors = ['#8b5cf6', '#06b6d4', '#f59e0b', '#10b981', '#ec4899', '#3b82f6'];

  for (let i = 0; i < 90; i++) {
    particles.push({
      x: canvas.width / 2,
      y: canvas.height / 2,
      vx: (Math.random() - 0.5) * 14,
      vy: (Math.random() - 0.7) * 16,
      size: Math.random() * 8 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      alpha: 1,
      rotation: Math.random() * 360
    });
  }

  let animationId;
  function update() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = false;
    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.4; // gravity
      p.alpha -= 0.012;
      p.rotation += 4;
      if (p.alpha > 0) {
        alive = true;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rotation * Math.PI) / 180);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.alpha;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
        ctx.restore();
      }
    });

    if (alive) {
      animationId = requestAnimationFrame(update);
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }
  update();
}

// ==========================================
// 96 DAYS VOCABULARY CATALOG & MODAL
// ==========================================

let vocabSummaryCache = null;

async function loadVocabCatalog() {
  if (!vocabSummaryCache) {
    try {
      const res = await fetch('/api/vocab/summary');
      vocabSummaryCache = await res.json();
    } catch(e) {}
  }
  renderVocabDays(vocabSummaryCache || []);
}

function renderVocabDays(days) {
  const container = document.getElementById('vocabDaysContainer');
  if (!container) return;
  container.innerHTML = '';

  days.forEach(d => {
    const card = document.createElement('div');
    card.className = 'day-card';
    card.onclick = () => openDayDetailModal(d.day);
    card.innerHTML = `
      <div>
        <div style="font-weight: 800; font-size: 15px; margin-bottom: 2px;">${d.day}-KUN LUG'ATI</div>
        <div style="font-size: 12px; color: var(--text-muted);">${d.count} ta so'z (${d.sample})</div>
      </div>
      <button class="icon-btn" style="width:32px; height:32px; font-size:14px;">➔</button>
    `;
    container.appendChild(card);
  });
}

function filterVocabList() {
  const q = document.getElementById('vocabSearchInput').value.toLowerCase();
  if (!vocabSummaryCache) return;
  const filtered = vocabSummaryCache.filter(d => 
    `${d.day}-kun`.includes(q) || d.sample.toLowerCase().includes(q)
  );
  renderVocabDays(filtered);
}

async function openDayDetailModal(day) {
  try {
    const res = await fetch(`/api/vocab/day/${day}`);
    const words = await res.json();

    document.getElementById('modalDayTitle').textContent = `${day}-Kun Lug'atlari (${words.length} ta so'z)`;
    const wordsList = document.getElementById('modalDayWordsList');
    wordsList.innerHTML = '';

    words.forEach((w, idx) => {
      const row = document.createElement('div');
      row.style.padding = '8px 0';
      row.style.borderBottom = '1px solid var(--card-border)';
      row.style.fontSize = '13.5px';
      row.innerHTML = `
        <div style="display:flex; justify-content:space-between;">
          <b>${idx + 1}. ${w.en}</b>
          <span style="color:var(--text-muted); font-style:italic;">${w.pron ? `[${w.pron}]` : ''}</span>
        </div>
        <div style="color:#38bdf8; font-size:13px; margin-top:2px;">➔ ${w.uz}</div>
      `;
      wordsList.appendChild(row);
    });

    // Wire battle start button
    document.getElementById('btnStartDayBattle').onclick = () => {
      closeModal();
      document.getElementById('roomDayInput').value = day;
      switchTab('rooms');
      handleCreateRoomClick();
    };

    document.getElementById('dayDetailModal').classList.add('active');
  } catch (e) {}
}

function closeModal() {
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
}

// ==========================================
// LEADERBOARD VIEW
// ==========================================

async function loadLeaderboard() {
  const container = document.getElementById('leaderboardList');
  container.innerHTML = '<p style="text-align:center; color:var(--text-muted); padding:20px;">Yuklanmoqda...</p>';
  try {
    const res = await fetch('/api/leaderboard');
    const users = await res.json();
    container.innerHTML = '';
    users.forEach((u, i) => {
      const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}.`;
      const item = document.createElement('div');
      item.className = 'player-item';
      item.innerHTML = `
        <div class="player-info">
          <span style="font-weight: 800; font-size: 18px; width: 28px; text-align:center;">${medal}</span>
          <div>
            <div style="font-weight: 700; font-size: 14.5px;">${u.first_name || u.username || "O'yinchi"}</div>
            <div style="font-size: 11.5px; color: var(--text-muted);">${u.games_played} ta o'yin | ${u.wins} g'alaba</div>
          </div>
        </div>
        <span style="font-weight: 900; color: var(--accent); font-size: 15.5px;">${u.score} ⭐</span>
      `;
      container.appendChild(item);
    });
  } catch(e) {}
}

// ==========================================
// PROFILE & MISTAKES VIEW
// ==========================================

async function loadProfileView() {
  await fetchUserStats();
  document.getElementById('profScoreVal').textContent = userStats.score || 0;
  document.getElementById('profGamesVal').textContent = userStats.games_played || 0;
  document.getElementById('profWinsVal').textContent = userStats.wins || 0;
  document.getElementById('profCorrectVal').textContent = userStats.correct_count || 0;
  document.getElementById('profWrongVal').textContent = userStats.wrong_count || 0;

  // Load mistakes list
  const mContainer = document.getElementById('profileMistakesList');
  mContainer.innerHTML = '<p style="color:var(--text-muted); font-size:13px; text-align:center;">Yuklanmoqda...</p>';
  try {
    const res = await fetch(`/api/user/${currentUser.id}/mistakes`);
    const mistakes = await res.json();
    if (!mistakes || mistakes.length === 0) {
      mContainer.innerHTML = '<p style="color:var(--text-muted); font-size:13px; text-align:center; padding:10px;">Ajoyib! Hozircha xatolaringiz yo\'q 🎉</p>';
    } else {
      mContainer.innerHTML = '';
      mistakes.forEach(m => {
        const item = document.createElement('div');
        item.style.padding = '8px 0';
        item.style.borderBottom = '1px solid var(--card-border)';
        item.style.fontSize = '13px';
        item.innerHTML = `
          <div style="display:flex; justify-content:space-between;">
            <b style="color:white;">${m.en}</b>
            <span style="color:var(--text-muted); font-style:italic;">${m.pron ? `[${m.pron}]` : ''}</span>
          </div>
          <div style="color:var(--success); font-weight:600; margin-top:2px;">➔ ${m.uz}</div>
        `;
        mContainer.appendChild(item);
      });
    }
  } catch(e) {
    mContainer.innerHTML = '';
  }
}

// Run app on DOM ready
document.addEventListener('DOMContentLoaded', initApp);
