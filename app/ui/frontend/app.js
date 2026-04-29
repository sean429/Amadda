'use strict';

const API = 'http://127.0.0.1:8765';

// ─── DOM refs ────────────────────────────────────────────────────────────────
const feed           = document.getElementById('feed');
const textInput      = document.getElementById('text-input');
const sendBtn        = document.getElementById('send-btn');
const micBtn         = document.getElementById('mic-btn');
const menuBtn        = document.getElementById('menu-btn');
const dropdownOverlay= document.getElementById('dropdown-overlay');
const autoSnapshotStatus = document.getElementById('auto-snapshot-status');
const wakewordStatus     = document.getElementById('wakeword-status');

// Panels
const historyOverlay = document.getElementById('history-overlay');
const historyBody    = document.getElementById('history-body');
const trackedOverlay = document.getElementById('tracked-overlay');
const trackedList    = document.getElementById('tracked-list');
const trackedInput   = document.getElementById('tracked-input');
const trackedAddBtn  = document.getElementById('tracked-add');

// ─── State ───────────────────────────────────────────────────────────────────
let micListening  = false;
let autoSnapOn    = true;
let wakewordOn    = false;
let pendingIntent = null;
let trackedApps   = [];
let _wakewordPollTimer = null;

// ─── Helpers ─────────────────────────────────────────────────────────────────
function now() {
  return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}

function addBlock(html, cls = 'block-result', extra = '') {
  const div = document.createElement('div');
  div.className = `block ${cls}`;
  div.innerHTML = html + `<div class="block-time">${now()}</div>`;
  if (extra) div.classList.add(extra);
  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
  return div;
}

function addUserBlock(text) {
  addBlock(`<span>${escapeHtml(text)}</span>`, 'block-user');
}

function addSystemBlock(text) {
  addBlock(`<span>${escapeHtml(text)}</span>`, 'block-system');
}

function addResultBlock(message, success = true) {
  addBlock(`<span>${escapeHtml(message)}</span>`, 'block-result', success ? 'success' : 'error');
}

function addSummaryBlock(markdownText) {
  const rendered = typeof marked !== 'undefined'
    ? marked.parse(markdownText)
    : `<pre>${escapeHtml(markdownText)}</pre>`;
  addBlock(rendered, 'block-summary');
}

function addConfirmBlock(message, onConfirm, onCancel) {
  const div = document.createElement('div');
  div.className = 'block block-confirm';
  div.innerHTML = `
    <span>${escapeHtml(message)}</span>
    <div class="confirm-btns">
      <button class="btn btn-confirm">실행</button>
      <button class="btn btn-cancel">취소</button>
    </div>
    <div class="block-time">${now()}</div>
  `;
  div.querySelector('.btn-confirm').onclick = () => { div.remove(); onConfirm(); };
  div.querySelector('.btn-cancel').onclick  = () => { div.remove(); onCancel && onCancel(); };
  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// ─── Command handling ─────────────────────────────────────────────────────────
async function runCommand(text, confirmed = false) {
  try {
    const res  = await fetch(`${API}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, confirmed }),
    });
    const data = await res.json();

    if (data.permission?.requires_confirmation && !confirmed) {
      const reason = data.permission.reason || '이 작업을 실행하시겠습니까?';
      addConfirmBlock(reason,
        () => runCommand(text, true),
        () => addSystemBlock('취소되었습니다.')
      );
      return;
    }

    if (!data.result) {
      addSystemBlock('명령을 처리했습니다.');
      return;
    }

    const { success, message, data: rdata } = data.result;

    if ((data.intent?.intent === 'summarize' || data.intent?.intent === 'introduce') && success && message) {
      addSummaryBlock(message);
    } else {
      addResultBlock(message, success);
    }
  } catch (err) {
    addResultBlock('서버 연결 오류: ' + err.message, false);
  }
}

async function onSend() {
  const text = textInput.value.trim();
  if (!text) return;
  textInput.value = '';
  addUserBlock(text);
  await runCommand(text);
}

// ─── Mic / voice ─────────────────────────────────────────────────────────────
async function onMic() {
  if (micListening) return;
  micListening = true;
  micBtn.classList.add('listening');

  try {
    const res  = await fetch(`${API}/voice/transcribe`, { method: 'POST' });
    const data = await res.json();
    micBtn.classList.remove('listening');
    micBtn.classList.add('processing');

    if (data.success && data.text) {
      addUserBlock(data.text);
      await runCommand(data.text);
    } else {
      addSystemBlock('음성 인식에 실패했습니다.');
    }
  } catch (err) {
    addResultBlock('음성 오류: ' + err.message, false);
  } finally {
    micListening = false;
    micBtn.classList.remove('listening', 'processing');
  }
}

// ─── Dropdown menu ────────────────────────────────────────────────────────────
function openDropdown() { dropdownOverlay.classList.add('open'); }
function closeDropdown() { dropdownOverlay.classList.remove('open'); }

menuBtn.addEventListener('click', e => { e.stopPropagation(); openDropdown(); });
dropdownOverlay.addEventListener('click', e => {
  if (!document.getElementById('dropdown-panel').contains(e.target)) closeDropdown();
});

document.getElementById('menu-save-snapshot').addEventListener('click', async () => {
  closeDropdown();
  addSystemBlock('스냅샷 저장 중...');
  await runCommand('스냅샷 저장해줘', true);
});

document.getElementById('menu-restore-snapshot').addEventListener('click', async () => {
  closeDropdown();
  addSystemBlock('최근 스냅샷 복구 중...');
  await runCommand('최근 스냅샷 복구해줘', true);
});

document.getElementById('menu-history').addEventListener('click', () => {
  closeDropdown();
  openHistoryPanel();
});

document.getElementById('menu-tracked-apps').addEventListener('click', () => {
  closeDropdown();
  openTrackedPanel();
});

document.getElementById('menu-auto-snapshot').addEventListener('click', async () => {
  autoSnapOn = !autoSnapOn;
  await fetch(`${API}/settings/auto-snapshot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled: autoSnapOn }),
  });
  autoSnapshotStatus.textContent = autoSnapOn ? 'ON' : 'OFF';
  addSystemBlock(`자동 스냅샷 ${autoSnapOn ? '활성화' : '비활성화'} 됨.`);
  closeDropdown();
});

document.getElementById('menu-wakeword').addEventListener('click', async () => {
  wakewordOn = !wakewordOn;
  await fetch(`${API}/settings/wakeword`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled: wakewordOn }),
  });
  wakewordStatus.textContent = wakewordOn ? 'ON' : 'OFF';
  if (wakewordOn) {
    addSystemBlock('"아맞다" 또는 "아맞다야" 라고 말하면 음성 명령 모드가 시작돼요.');
    _startWakewordPolling();
  } else {
    _stopWakewordPolling();
    addSystemBlock('"아맞다" 트리거 비활성화됨.');
  }
  closeDropdown();
});

function _startWakewordPolling() {
  if (_wakewordPollTimer) return;
  _wakewordPollTimer = setInterval(async () => {
    if (!wakewordOn || micListening) return;
    try {
      const res  = await fetch(`${API}/wakeword/poll`);
      const data = await res.json();
      if (data.triggered) {
        addSystemBlock('👂 "아맞다" 감지 — 말씀하세요...');
        await onMic();
      }
    } catch { /* 서버 일시 미응답 무시 */ }
  }, 800);
}

function _stopWakewordPolling() {
  if (_wakewordPollTimer) {
    clearInterval(_wakewordPollTimer);
    _wakewordPollTimer = null;
  }
}

document.getElementById('menu-summarize').addEventListener('click', async () => {
  closeDropdown();
  addSystemBlock('AI 작업 요약 생성 중...');
  await runCommand('작업 요약해줘', true);
});

// ─── Snapshot history panel ───────────────────────────────────────────────────
async function openHistoryPanel() {
  historyOverlay.classList.add('open');
  historyBody.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">불러오는 중...</div>';

  try {
    const res  = await fetch(`${API}/snapshots/history?n=20`);
    const data = await res.json();
    const snapshots = data.snapshots || [];

    if (snapshots.length === 0) {
      historyBody.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">저장된 스냅샷이 없습니다.</div>';
      return;
    }

    historyBody.innerHTML = '';
    snapshots.forEach(snap => {
      const date = new Date(snap.created_at);
      const timeStr = date.toLocaleString('ko-KR', {
        month: 'numeric', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
      const items = snap.items || [];
      const preview = items.slice(0, 4);

      const card = document.createElement('div');
      card.className = 'snapshot-card';
      card.innerHTML = `
        <div class="snapshot-card-header">
          <span class="snapshot-time">${timeStr} · ${items.length}개 항목</span>
          <button class="snapshot-restore" data-id="${snap.snapshot_id}">복구</button>
        </div>
        <div class="snapshot-items-list">
          ${preview.map(it => `
            <div class="snapshot-item-row">
              <span class="tag">${escapeHtml(it.item_type === 'browser_tab' ? '탭' : it.app_name.slice(0,6))}</span>
              <span class="snapshot-item-title">${escapeHtml(it.title)}</span>
            </div>`).join('')}
          ${items.length > 4 ? `<div style="color:var(--text-muted);font-size:10px;margin-top:3px;">+${items.length-4}개 더</div>` : ''}
        </div>
      `;
      card.querySelector('.snapshot-restore').addEventListener('click', async () => {
        historyOverlay.classList.remove('open');
        addSystemBlock('스냅샷 복구 중...');
        await runCommand('최근 스냅샷 복구해줘', true);
      });
      historyBody.appendChild(card);
    });
  } catch (err) {
    historyBody.innerHTML = `<div style="color:var(--text-muted);">오류: ${escapeHtml(err.message)}</div>`;
  }
}

document.getElementById('history-close').addEventListener('click', () => {
  historyOverlay.classList.remove('open');
});
historyOverlay.addEventListener('click', e => {
  if (!e.target.closest('.panel')) historyOverlay.classList.remove('open');
});

// ─── Tracked apps panel ───────────────────────────────────────────────────────
async function openTrackedPanel() {
  trackedOverlay.classList.add('open');
  await refreshTrackedList();
}

async function refreshTrackedList() {
  try {
    const res  = await fetch(`${API}/tracked-apps`);
    const data = await res.json();
    trackedApps = (data.tracked_apps || []).map(a => a.process_name);
    renderTrackedList();
  } catch { trackedApps = []; renderTrackedList(); }
}

function renderTrackedList() {
  trackedList.innerHTML = '';
  trackedApps.forEach((name, i) => {
    const chip = document.createElement('div');
    chip.className = 'tracked-chip';
    chip.innerHTML = `
      <span>${escapeHtml(name)}</span>
      <button class="tracked-chip-remove" data-i="${i}">×</button>
    `;
    chip.querySelector('.tracked-chip-remove').addEventListener('click', async () => {
      trackedApps.splice(i, 1);
      await saveTrackedApps();
      renderTrackedList();
    });
    trackedList.appendChild(chip);
  });
}

async function saveTrackedApps() {
  await fetch(`${API}/tracked-apps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(trackedApps.map(name => ({ process_name: name }))),
  });
}

trackedAddBtn.addEventListener('click', async () => {
  const val = trackedInput.value.trim();
  if (!val || trackedApps.includes(val)) return;
  trackedInput.value = '';
  trackedApps.push(val);
  await saveTrackedApps();
  renderTrackedList();
});
trackedInput.addEventListener('keydown', e => { if (e.key === 'Enter') trackedAddBtn.click(); });

document.getElementById('tracked-close').addEventListener('click', () => {
  trackedOverlay.classList.remove('open');
});
trackedOverlay.addEventListener('click', e => {
  if (!e.target.closest('.panel')) trackedOverlay.classList.remove('open');
});

// ─── Input events ─────────────────────────────────────────────────────────────
sendBtn.addEventListener('click', onSend);
micBtn.addEventListener('click', onMic);
textInput.addEventListener('keydown', e => { if (e.key === 'Enter') onSend(); });
document.getElementById('clear-btn').addEventListener('click', () => { feed.innerHTML = ''; });

// ─── Init ─────────────────────────────────────────────────────────────────────
(async () => {
  // Check auto-snapshot state
  try {
    const res  = await fetch(`${API}/settings/auto-snapshot`);
    const data = await res.json();
    autoSnapOn = data.enabled;
    autoSnapshotStatus.textContent = autoSnapOn ? 'ON' : 'OFF';
  } catch { /* server not ready yet */ }

  addBlock(
    '<span style="color:#fff;font-weight:600;text-shadow:0 0 12px rgba(255,255,255,0.85),0 0 28px rgba(255,255,255,0.40);">Amadda is online · listening</span>',
    'block-system'
  );
})();
