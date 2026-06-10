'use strict';

// ── Device detection ─────────────────────────────────────────────────────────
// Sets body.mobile / body.tablet / body.desktop so CSS and JS can both react.
function detectDevice() {
  const w = window.innerWidth;
  document.body.classList.remove('mobile', 'tablet', 'desktop');
  if (w < 600)       document.body.classList.add('mobile');
  else if (w < 1024) document.body.classList.add('tablet');
  else               document.body.classList.add('desktop');
}
detectDevice();
window.addEventListener('resize', detectDevice);

// ── Zone state ───────────────────────────────────────────────────────────────
// Zone state — id (string) → zone object from /status
const state = {};
let pollTimer = null;

// ── API ──────────────────────────────────────────────────────────────────────

async function api(method, path, body) {
  const opts = { method };
  if (body) {
    opts.headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
    opts.body = new URLSearchParams(body).toString();
  }
  const res = await fetch(path, opts);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

// ── State ────────────────────────────────────────────────────────────────────

// Merge incoming data into state, preserving inputs if not included in response.
function merge(incoming) {
  for (const id in incoming) {
    const z = incoming[id];
    if (!state[id]) state[id] = {};
    const prevInputs = state[id].inputs;
    Object.assign(state[id], z);
    if (!z.inputs || Object.keys(z.inputs).length === 0) {
      state[id].inputs = prevInputs || {};
    }
  }
}

// ── Rendering ────────────────────────────────────────────────────────────────

function renderAll() {
  const grid = document.getElementById('zone-grid');
  const ids = Object.keys(state).sort((a, b) => Number(a) - Number(b));
  ids.forEach(id => {
    if (!document.getElementById(`zc-${id}`)) {
      grid.appendChild(buildCard(id));
    }
    syncCard(id);
  });
}

function buildCard(id) {
  const d = document.createElement('div');
  d.id = `zc-${id}`;
  d.className = 'zone-card off';
  d.innerHTML = `
    <div class="zone-header">
      <span class="zone-name" id="zn-${id}">Zone ${id}</span>
      <label class="power-switch" title="Power on/off">
        <input type="checkbox" id="pwr-${id}" onchange="setPower(${id}, this.checked)">
        <span class="switch-track"><span class="switch-thumb"></span></span>
      </label>
    </div>
    <div class="zone-body" id="zbody-${id}">
      <select class="source-select" id="src-${id}"
              onchange="setInput(${id}, this.value)"></select>
      <div class="ctrl-row">
        <span class="ctrl-lbl">VOL</span>
        <input type="range" class="slider" id="vol-${id}" min="0" max="100" step="1"
               oninput="document.getElementById('vl-${id}').textContent = this.value"
               onchange="setVolume(${id}, this.value)">
        <span class="ctrl-val" id="vl-${id}">0</span>
      </div>
      <div class="btn-row">
        <button class="ctrl-btn" id="mute-${id}" onclick="toggleMute(${id})">Mute</button>
        <button class="ctrl-btn eq-toggle" id="eqtog-${id}"
                onclick="toggleEq(${id})">EQ &#9660;</button>
      </div>
      <div class="eq-panel" id="eq-${id}">
        <div class="ctrl-row">
          <span class="ctrl-lbl">BAL</span>
          <input type="range" class="slider" id="bal-${id}" min="-18" max="18" step="1"
                 oninput="document.getElementById('bl-${id}').textContent = this.value"
                 onchange="setBalance(${id}, this.value)">
          <span class="ctrl-val" id="bl-${id}">0</span>
        </div>
        <div class="ctrl-row">
          <span class="ctrl-lbl">TRE</span>
          <input type="range" class="slider" id="tre-${id}" min="-10" max="10" step="1"
                 oninput="document.getElementById('tl-${id}').textContent = this.value"
                 onchange="setTreble(${id}, this.value)">
          <span class="ctrl-val" id="tl-${id}">0</span>
        </div>
        <div class="ctrl-row">
          <span class="ctrl-lbl">BASS</span>
          <input type="range" class="slider" id="bas-${id}" min="-10" max="10" step="1"
                 oninput="document.getElementById('bsl-${id}').textContent = this.value"
                 onchange="setBass(${id}, this.value)">
          <span class="ctrl-val" id="bsl-${id}">0</span>
        </div>
      </div>
    </div>`;
  return d;
}

function syncCard(id) {
  const z = state[id];
  if (!z) return;

  const card = document.getElementById(`zc-${id}`);
  card.classList.toggle('on',  !!z.power);
  card.classList.toggle('off', !z.power);

  document.getElementById(`zn-${id}`).textContent = z.name || `Zone ${id}`;
  document.getElementById(`pwr-${id}`).checked = !!z.power;

  // Volume
  setSliderVal(`vol-${id}`, `vl-${id}`, z.volume ?? 0);

  // Source select — only rebuild when we have input names
  const inputs = z.inputs || {};
  if (Object.keys(inputs).length > 0) {
    const sel = document.getElementById(`src-${id}`);
    sel.innerHTML = '';
    Object.keys(inputs).sort((a, b) => Number(a) - Number(b)).forEach(num => {
      const opt = document.createElement('option');
      opt.value = num;
      opt.textContent = inputs[num];
      sel.appendChild(opt);
    });
    sel.value = String(z.input ?? 1);
  }

  // Mute
  const muteBtn = document.getElementById(`mute-${id}`);
  const isMuted = !!z.mute;
  muteBtn.classList.toggle('active', isMuted);
  muteBtn.textContent = isMuted ? '🔇 Muted' : 'Mute';

  // EQ sliders
  setSliderVal(`bal-${id}`, `bl-${id}`,  z.balance ?? 0);
  setSliderVal(`tre-${id}`, `tl-${id}`,  z.treble  ?? 0);
  setSliderVal(`bas-${id}`, `bsl-${id}`, z.bass    ?? 0);

  // Enable/disable all controls in zone body based on power state
  document.getElementById(`zbody-${id}`)
    .querySelectorAll('input, select, button')
    .forEach(el => { el.disabled = !z.power; });
}

function setSliderVal(sliderId, labelId, val) {
  const el = document.getElementById(sliderId);
  const lbl = document.getElementById(labelId);
  if (el) el.value = val;
  if (lbl) lbl.textContent = val;
}

// ── Zone actions ─────────────────────────────────────────────────────────────

async function run(fn) {
  setStatus('loading');
  try {
    await fn();
    setStatus('ok');
  } catch (e) {
    setStatus('error', String(e));
    console.error(e);
  }
}

async function setPower(id, on) {
  await run(async () => {
    merge(await api('PUT', `/zone/${id}/power`, { power: on ? 1 : 0 }));
    renderAll();
  });
}

async function setAllPower(on) {
  await run(async () => {
    await api('PUT', '/zone/all/power', { power: on ? 1 : 0 });
    // Full refresh — multiple zones changed and rx_bytes may have missed some
    merge(await api('GET', '/status'));
    renderAll();
  });
}

async function setVolume(id, vol) {
  await run(async () => {
    merge(await api('PUT', `/zone/${id}/volume`, { volume: vol }));
    // No renderAll — volume label already updated via oninput
  });
}

async function setInput(id, input) {
  await run(async () => {
    merge(await api('PUT', `/zone/${id}/input`, { input }));
    renderAll();
  });
}

async function toggleMute(id) {
  const z = state[id];
  if (!z || !z.power) return;
  await run(async () => {
    merge(await api('PUT', `/zone/${id}/mute`, { mute: z.mute ? 0 : 1 }));
    renderAll();
  });
}

async function setBalance(id, val) {
  await run(async () => {
    merge(await api('PUT', `/zone/${id}/balance`, { balance: val }));
  });
}

async function setTreble(id, val) {
  await run(async () => {
    merge(await api('PUT', `/zone/${id}/treble`, { treble: val }));
  });
}

async function setBass(id, val) {
  await run(async () => {
    merge(await api('PUT', `/zone/${id}/bass`, { bass: val }));
  });
}

async function sendMp3(action) {
  await run(async () => { await api('PUT', `/mp3/${action}`); });
}

// ── UI helpers ────────────────────────────────────────────────────────────────

function toggleMp3() {
  const row = document.querySelector('.mp3-row');
  const btn = document.querySelector('.mp3-toggle');
  const open = row.classList.toggle('mp3-open');
  btn.innerHTML = open ? 'MP3 &#9650;' : 'MP3 &#9660;';
}

function toggleEq(id) {
  const panel  = document.getElementById(`eq-${id}`);
  const toggle = document.getElementById(`eqtog-${id}`);
  const open   = panel.classList.toggle('open');
  toggle.classList.toggle('active-eq', open);
  toggle.innerHTML = open ? 'EQ &#9650;' : 'EQ &#9660;';
}

function setStatus(status, msg) {
  const dot = document.getElementById('status-dot');
  const txt = document.getElementById('status-txt');
  dot.className = 'status-dot ' + status;
  txt.textContent = {
    ok:      'Connected',
    loading: 'Refreshing…',
    error:   'Error — ' + (msg || ''),
  }[status] ?? msg;
}

async function refresh() {
  clearTimeout(pollTimer);
  await run(async () => {
    merge(await api('GET', '/status'));
    renderAll();
  });
  pollTimer = setTimeout(refresh, 15000);
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', refresh);

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/ui/sw.js');
}
