/** App wiring: session/driver selection, matchup header, tabs, chart rendering. */

import * as charts from './charts';
import { loadIndex, loadSession, type DriverData, type SessionData, type SessionRef } from './data';
import { compoundColor, compoundText, driverColors } from './theme';

const $ = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;

const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** Five lights on, hold, lights out — once per page load. */
async function lightsOut(): Promise<void> {
  if (REDUCED) return;
  const lights = Array.from(document.querySelectorAll('.lights i'));
  for (const l of lights) { l.classList.add('on'); await sleep(180); }
  await sleep(500);
  lights.forEach((l) => l.classList.remove('on'));
}

const state = {
  sessions: [] as SessionRef[],
  slug: '',
  data: null as SessionData | null,
  a: '',
  b: '',
  tab: 'pace',
  request: 0,
  renderedTabs: new Set<string>(),
};
type HistoryMode = 'push' | 'replace' | 'none';
let retryAction: () => void = () => { void init(); };

function esc(s: string): string {
  const d = document.createElement('span');
  d.textContent = s;
  return d.innerHTML.replaceAll('"', '&quot;');
}

function options(sel: HTMLSelectElement, values: { value: string; label: string }[], keep?: string): void {
  sel.innerHTML = values.map((v) => `<option value="${esc(v.value)}">${esc(v.label)}</option>`).join('');
  if (keep && values.some((v) => v.value === keep)) sel.value = keep;
}

function driver(code: string): DriverData {
  return state.data!.drivers[code];
}

function fmtLap(sec: number | null): string {
  if (sec == null || !Number.isFinite(sec)) return 'n/a';
  const milliseconds = Math.round(sec * 1000);
  return `${Math.floor(milliseconds / 60000)}:${((milliseconds % 60000) / 1000).toFixed(3).padStart(6, '0')}`;
}

function renderMatchup(): void {
  const [colA, colB] = colors();
  const A = driver(state.a), B = driver(state.b);
  const chip = (code: string, d: DriverData, col: string, side: 'a' | 'b') => `
    <div class="chip chip-${side}" style="--team:${col}">
      <span class="chip-bar"></span>
      <span class="chip-txt">
        <span class="abbr">${esc(code)}</span>
        <span class="team">${esc(d.team ?? '')}</span>
        <span class="lap">${fmtLap(d.fastest.sec)}</span>
        <span class="team">Lap ${d.fastest.lap ?? '–'} · ${esc(d.fastest.compound ?? 'Unknown compound')}</span>
      </span>
    </div>`;
  const fa = A.fastest.sec, fb = B.fastest.sec;
  let center = `<div class="gap"><span class="gap-v">n/a</span></div>`;
  if (fa != null && fb != null) {
    const gap = fb - fa;
    const winner = gap > 0 ? state.a : state.b;
    const winCol = gap > 0 ? colA : colB;
    center = `<div class="gap">
      <span class="gap-v">${Math.abs(gap).toFixed(3)}s</span>
      <span class="gap-sub">${Math.abs(gap) < .0005 ? 'Equal lap time' : `<span aria-hidden="true" style="color:${winCol}">${gap > 0 ? '◀' : '▶'}</span> ${esc(winner)} faster`}</span>
    </div>`;
  }
  $('matchup').innerHTML = chip(state.a, A, colA, 'a') + center + chip(state.b, B, colB, 'b');
  $('session-sub').textContent = state.data!.label;
}

function renderSectors(): void {
  const A = driver(state.a), B = driver(state.b);
  const keys = ['s1', 's2', 's3'] as const;
  const fmt = (v: number | null) => (v != null ? v.toFixed(3) : '–');
  const rows = keys.map((k, i) => {
    const sa = A.fastest.sectors[k], sb = B.fastest.sectors[k];
    let chip = '–';
    if (sa != null && sb != null) {
      const d = sb - sa;                       // +ve = B slower = A faster (same as the old chart)
      chip = Math.abs(d) < .0005 ? 'Equal' : `${esc(d > 0 ? state.a : state.b)} by ${Math.abs(d).toFixed(3)}`;
    }
    return `<tr><th scope="row">S${i + 1}</th><td>${fmt(sa)}</td><td>${fmt(sb)}</td><td>${chip}</td></tr>`;
  }).join('');
  $('timing').innerHTML = `<table aria-label="Sector comparison"><caption>Sector comparison · seconds</caption><thead><tr>
    <th scope="col">Sector</th><th scope="col">${esc(state.a)}</th><th scope="col">${esc(state.b)}</th><th scope="col">Faster</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
}

function renderLapData(): void {
  const a = new Map(driver(state.a).laps.map(l => [l.LapNumber, l.sec]));
  const b = new Map(driver(state.b).laps.map(l => [l.LapNumber, l.sec]));
  const laps = [...new Set([...a.keys(), ...b.keys()])].sort((x, y) => x - y);
  $('lap-data').innerHTML = `<table aria-label="Lap times"><caption>All timed laps, including pit and safety-car laps</caption>
    <thead><tr><th scope="col">Lap</th><th scope="col">${esc(state.a)}</th><th scope="col">${esc(state.b)}</th></tr></thead>
    <tbody>${laps.map(l => `<tr><th scope="row">${l}</th><td>${fmtLap(a.get(l) ?? null)}</td><td>${fmtLap(b.get(l) ?? null)}</td></tr>`).join('')}</tbody></table>`;
}

function renderStints(): void {
  const A = driver(state.a), B = driver(state.b);
  const maxLap = Math.max(1, ...A.stints.map((s) => s.EndLap), ...B.stints.map((s) => s.EndLap));
  const lane = (code: string, d: DriverData) => {
    const segs = d.stints.map((s) => {
      const left = ((s.StartLap - 1) / maxLap) * 100;
      const width = ((s.EndLap - s.StartLap + 1) / maxLap) * 100;
      return `<span class="seg" title="${esc(`${s.Compound}: laps ${s.StartLap}–${s.EndLap}`)}"
        style="left:${left}%; width:${width}%; background:${compoundColor(s.Compound)}; color:${compoundText(s.Compound)}">
        <span class="seg-label mono">${esc(`${s.Compound} · ${s.Laps}`)}</span></span>`;
    }).join('');
    return `<div class="lane"><span class="lane-k mono">${esc(code)}</span><div class="lane-track">${segs}</div></div>`;
  };
  const tickVals = [1, Math.round(maxLap * 0.25), Math.round(maxLap * 0.5), Math.round(maxLap * 0.75), maxLap];
  const ticks = tickVals
    .filter((v) => v >= 1)
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .map((v) => `<span class="tick mono" style="left:${((v - 1) / maxLap) * 100}%">${v}</span>`).join('');
  $('stints').innerHTML = lane(state.a, A) + lane(state.b, B) + `<div class="lane-axis">${ticks}</div>`;
  $('stint-data').innerHTML = `<table aria-label="Tyre stints"><caption>Compounds and recorded lap ranges for each driver</caption>
    <thead><tr><th scope="col">Driver</th><th scope="col">Compound</th><th scope="col">Laps</th></tr></thead>
    <tbody>${[state.a, state.b].flatMap(code => driver(code).stints.map(s =>
      `<tr><th scope="row">${esc(code)}</th><td>${esc(s.Compound)}</td><td>${s.StartLap}–${s.EndLap}</td></tr>`)).join('')}</tbody></table>`;
}

function renderWeather(): void {
  const w = state.data!.weather;
  $('weather').innerHTML = w
    ? ([['Air', `${w.airTemp}°C`], ['Track', `${w.trackTemp}°C`], ['Humidity', `${w.humidity}%`],
        ['Wind', `${w.windSpeed} m/s`], ['Rain', w.rain ? 'Yes' : 'No']] as [string, string][])
        .map(([k, v]) => `<div class="stat"><span class="stat-k">${k}</span><span class="stat-v">${v}</span></div>`).join('')
    : '<p class="caption">No weather data.</p>';
}

function colors(): [string, string] {
  return driverColors(driver(state.a).team, driver(state.b).team);
}

function renderTab(tab: string): void {
  const [colA, colB] = colors();
  const A = driver(state.a), B = driver(state.b);
  switch (tab) {
    case 'pace':
      charts.lapPace('chart-pace', A, B, state.a, state.b, colA, colB);
      renderLapData();
      break;
    case 'telemetry':
      $('telemetry-status').textContent = '';
      try {
        charts.delta('chart-delta', A, B, state.a, state.b, colB);
        charts.channel('chart-speed', 'Speed', A, B, state.a, state.b, colA, colB);
        charts.channel('chart-throttle', 'Throttle', A, B, state.a, state.b, colA, colB);
        charts.channel('chart-brake', 'Brake', A, B, state.a, state.b, colA, colB);
        charts.channel('chart-gear', 'nGear', A, B, state.a, state.b, colA, colB);
      } catch (err) {
        ['delta', 'speed', 'throttle', 'brake', 'gear'].forEach(id => charts.clear(`chart-${id}`));
        $('telemetry-status').textContent = err instanceof Error ? err.message : 'Telemetry unavailable. Choose another comparison.';
      }
      break;
    case 'track':
      charts.trackMap('chart-track', A, state.a);
      renderSectors();
      break;
    case 'tyres':
      renderStints();
      renderWeather();
      break;
    case 'model': {
      const m = state.data!.model;
      const box = $('model-metrics');
      if (!m) {
        box.innerHTML = '<p class="caption">Not enough green laps in this session to fit the model.</p>';
        charts.clear('chart-degradation');
        $('degradation-data').replaceChildren();
        $('model-notes').replaceChildren();
        break;
      }
      box.innerHTML = ([
        ['Baseline MAE', `${m.baseline_mae.toFixed(3)}s`, ''],
        ['Model MAE', `${m.model_mae.toFixed(3)}s`, ''],
        ['Improvement', m.improvement_mae_pct != null ? `${m.improvement_mae_pct.toFixed(0)}%` : 'n/a', ' stat-accent'],
        ['Train / test laps', `${m.n_train} / ${m.n_test}`, ''],
      ] as [string, string, string][]).map(([k, v, cls]) =>
        `<div class="stat${cls}"><span class="stat-k">${k}</span><span class="stat-v">${v}</span></div>`).join('');
      charts.degradation('chart-degradation', state.data!);
      $('degradation-data').innerHTML = `<table aria-label="Degradation evidence"><caption>Tyre-age correlation, not isolated tyre wear. R² near 0 indicates a weak fit.</caption>
        <thead><tr><th scope="col">Compound</th><th scope="col">s / lap</th><th scope="col">R²</th><th scope="col">Laps</th></tr></thead>
        <tbody>${m.degradation.map(d => `<tr><th scope="row">${esc(d.compound)}</th><td>${d.slope_s_per_lap.toFixed(3)}</td><td>${d.r_squared.toFixed(2)}</td><td>${d.n_laps}</td></tr>`).join('')}</tbody></table>`;
      $('model-notes').innerHTML = m.notes.map((n) => `<li>${esc(n)}</li>`).join('');
      break;
    }
  }
  state.renderedTabs.add(tab);
}

function syncUrl(mode: HistoryMode = 'push'): void {
  if (mode === 'none') return;
  const q = new URLSearchParams({ session: state.slug, a: state.a, b: state.b, tab: state.tab });
  const next = `?${q.toString()}`;
  if (location.search !== next) history[mode === 'replace' ? 'replaceState' : 'pushState'](null, '', next);
}

function activateTab(tab: string, mode: HistoryMode = 'push'): void {
  const buttons = [...document.querySelectorAll<HTMLButtonElement>('.tab')];
  state.tab = buttons.some(b => b.dataset.tab === tab) ? tab : 'pace';
  buttons.forEach(btn => {
    const active = btn.dataset.tab === state.tab;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', String(active));
    btn.tabIndex = active ? 0 : -1;
    $(`panel-${btn.dataset.tab}`).classList.toggle('hidden', !active);
  });
  if (state.data) {
    if (!state.renderedTabs.has(state.tab)) renderTab(state.tab);
    charts.resizeVisible();
    syncUrl(mode);
  }
  $('reset-zoom').classList.toggle('hidden', state.tab === 'tyres');
}

function syncDrivers(): void {
  for (const [id, other] of [['driverA', state.b], ['driverB', state.a]]) {
    [...$(id).querySelectorAll('option')].forEach(option => { option.disabled = option.value === other; });
  }
}

function rerender(mode: HistoryMode = 'push'): void {
  syncDrivers();
  renderMatchup();
  state.renderedTabs.clear();
  activateTab(state.tab, mode);
}

function busy(loading: boolean): void {
  $('load-status').textContent = loading ? 'Loading session data…' : '';
  document.querySelectorAll<HTMLButtonElement | HTMLSelectElement>('#driverA, #driverB, .tab, #reset-zoom')
    .forEach(el => { el.disabled = loading || !state.data; });
  $('matchup').setAttribute('aria-busy', String(loading));
}

function showError(message: string): void {
  $('error-message').textContent = message;
  $('load-error').classList.remove('hidden');
}

async function selectSession(slug: string, a = state.a, b = state.b, tab = state.tab, mode: HistoryMode = 'push'): Promise<void> {
  const request = ++state.request;
  busy(true);
  $('load-error').classList.add('hidden');
  ($('session') as HTMLSelectElement).value = slug;
  try {
    const data = await loadSession(slug);
    if (request !== state.request) return;
    const codes = Object.keys(data.drivers).sort();
    if (codes.length < 2) throw new Error('This session needs at least two drivers.');
    state.a = codes.includes(a) ? a : codes[0];
    state.b = codes.includes(b) && b !== state.a ? b : codes.find(c => c !== state.a)!;
    state.slug = slug;
    state.data = data;
    state.tab = tab;
    options($('driverA'), codes.map(c => ({ value: c, label: c })), state.a);
    options($('driverB'), codes.map(c => ({ value: c, label: c })), state.b);
    rerender(mode);
  } catch (err) {
    if (request !== state.request) return;
    retryAction = () => { void selectSession(slug, a, b, tab, mode); };
    showError(`Could not load this session. ${err instanceof Error ? err.message : 'Try again.'} Retry or choose another session.${state.data ? ' Your previous comparison is still shown.' : ''}`);
    if (state.data) {
      ($('session') as HTMLSelectElement).value = state.slug;
      syncUrl('replace');
    }
  } finally {
    if (request === state.request) busy(false);
  }
}

function restoreUrl(mode: HistoryMode): void {
  const q = new URLSearchParams(location.search);
  const wantSlug = q.get('session');
  const initial = state.sessions.find((s) => s.slug === wantSlug)?.slug ?? state.sessions[0].slug;
  void selectSession(initial, q.get('a') ?? '', q.get('b') ?? '', q.get('tab') ?? 'pace', mode);
}

function bindEvents(): void {
  $('retry').addEventListener('click', () => retryAction());
  $('reset-zoom').addEventListener('click', () => charts.resetVisible());
  $('session').addEventListener('change', (e) => {
    void selectSession((e.target as HTMLSelectElement).value);
  });
  $('driverA').addEventListener('change', (e) => {
    state.a = (e.target as HTMLSelectElement).value;
    rerender();
  });
  $('driverB').addEventListener('change', (e) => {
    state.b = (e.target as HTMLSelectElement).value;
    rerender();
  });

  document.querySelectorAll<HTMLButtonElement>('.tab').forEach((btn) => {
    btn.addEventListener('click', () => activateTab(btn.dataset.tab!));
    btn.addEventListener('keydown', e => {
      const buttons = [...document.querySelectorAll<HTMLButtonElement>('.tab')];
      let index = buttons.indexOf(btn);
      if (e.key === 'ArrowRight') index = (index + 1) % buttons.length;
      else if (e.key === 'ArrowLeft') index = (index - 1 + buttons.length) % buttons.length;
      else if (e.key === 'Home') index = 0;
      else if (e.key === 'End') index = buttons.length - 1;
      else return;
      e.preventDefault();
      buttons[index].focus();
      activateTab(buttons[index].dataset.tab!);
    });
  });
  window.addEventListener('popstate', () => { if (state.sessions.length) restoreUrl('none'); });
}

async function init(): Promise<void> {
  busy(true);
  $('load-error').classList.add('hidden');
  try {
    state.sessions = await loadIndex();
    if (!state.sessions.length) throw new Error('No bundled sessions are available.');
    options($('session'), state.sessions.map(s => ({ value: s.slug, label: s.label })));
    restoreUrl('replace');
  } catch {
    busy(false);
    retryAction = () => { void init(); };
    showError('Could not load the session list. Check your connection and retry.');
  }
}

bindEvents();
void lightsOut();
void init();
