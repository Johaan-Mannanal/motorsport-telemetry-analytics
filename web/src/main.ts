/** App wiring: session/driver selection, matchup header, tabs, chart rendering. */

import * as charts from './charts';
import { loadIndex, loadSession, type DriverData, type SessionData, type SessionRef } from './data';
import { compoundColor, compoundText, driverColors, hexAlpha } from './theme';

const $ = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;

const state = {
  sessions: [] as SessionRef[],
  slug: '',
  data: null as SessionData | null,
  a: '',
  b: '',
  renderedTabs: new Set<string>(),
};

function esc(s: string): string {
  const d = document.createElement('span');
  d.textContent = s;
  return d.innerHTML;
}

function options(sel: HTMLSelectElement, values: { value: string; label: string }[], keep?: string): void {
  sel.innerHTML = values.map((v) => `<option value="${esc(v.value)}">${esc(v.label)}</option>`).join('');
  if (keep && values.some((v) => v.value === keep)) sel.value = keep;
}

function driver(code: string): DriverData {
  return state.data!.drivers[code];
}

function fmtLap(sec: number | null): string {
  return sec != null ? `${sec.toFixed(3)}s` : 'n/a';
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
      </span>
    </div>`;
  const fa = A.fastest.sec, fb = B.fastest.sec;
  let center = `<div class="gap"><span class="gap-v">n/a</span></div>`;
  if (fa != null && fb != null) {
    const gap = fb - fa;
    const winner = gap > 0 ? state.a : state.b;
    const winCol = gap > 0 ? colA : colB;
    center = `<div class="gap">
      <span class="gap-v">${gap >= 0 ? '+' : ''}${gap.toFixed(3)}s</span>
      <span class="gap-sub" style="color:${winCol}">${gap > 0 ? '◀' : '▶'} ${esc(winner)} faster</span>
    </div>`;
  }
  $('matchup').innerHTML = chip(state.a, A, colA, 'a') + center + chip(state.b, B, colB, 'b');
  $('session-sub').textContent = state.data!.label;
}

function renderSectors(): void {
  const [colA, colB] = colors();
  const A = driver(state.a), B = driver(state.b);
  const keys = ['s1', 's2', 's3'] as const;
  const fmt = (v: number | null) => (v != null ? v.toFixed(3) : '–');
  const rows = keys.map((k, i) => {
    const sa = A.fastest.sectors[k], sb = B.fastest.sectors[k];
    let chip = '', aWin = '', bWin = '';
    if (sa != null && sb != null) {
      const d = sb - sa;                       // +ve = B slower = A faster (same as the old chart)
      const col = d > 0 ? colA : colB;         // chip carries the FASTER driver's color
      aWin = d > 0 ? ` style="box-shadow: inset 3px 0 0 ${colA}"` : '';
      bWin = d < 0 ? ` style="box-shadow: inset 3px 0 0 ${colB}"` : '';
      chip = `<span class="t-chip" style="color:${col}; background:${hexAlpha(col, 0.15)}">${d >= 0 ? '+' : ''}${d.toFixed(3)}</span>`;
    }
    return `<div class="t-row">
      <span class="t-k mono">S${i + 1}</span>
      <span class="t-v mono"${aWin}>${fmt(sa)}</span>
      <span class="t-v mono"${bWin}>${fmt(sb)}</span>
      <span class="t-d">${chip}</span>
    </div>`;
  }).join('');
  $('timing').innerHTML = `<div class="t-row t-head">
    <span class="t-k"></span>
    <span class="t-v mono">${esc(state.a)}</span>
    <span class="t-v mono">${esc(state.b)}</span>
    <span class="t-d"></span>
  </div>${rows}`;
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
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .map((v) => `<span class="tick mono" style="left:${((v - 1) / maxLap) * 100}%">${v}</span>`).join('');
  $('stints').innerHTML = lane(state.a, A) + lane(state.b, B) + `<div class="lane-axis">${ticks}</div>`;
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
      break;
    case 'telemetry':
      charts.delta('chart-delta', A, B, state.a, state.b, colB);
      charts.channel('chart-speed', 'Speed', A, B, state.a, state.b, colA, colB);
      charts.channel('chart-throttle', 'Throttle', A, B, state.a, state.b, colA, colB);
      charts.channel('chart-brake', 'Brake', A, B, state.a, state.b, colA, colB);
      charts.channel('chart-gear', 'nGear', A, B, state.a, state.b, colA, colB);
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
        break;
      }
      box.innerHTML = [
        ['Baseline MAE', `${m.baseline_mae.toFixed(3)}s`],
        ['Model MAE', `${m.model_mae.toFixed(3)}s`],
        ['Improvement', m.improvement_mae_pct != null ? `${m.improvement_mae_pct.toFixed(0)}%` : 'n/a'],
        ['Train / test laps', `${m.n_train} / ${m.n_test}`],
      ].map(([k, v]) => `<div class="metric"><span class="metric-k">${k}</span><span class="metric-v mono">${v}</span></div>`).join('');
      charts.degradation('chart-degradation', state.data!);
      $('model-notes').innerHTML = m.notes.map((n) => `<li>${esc(n)}</li>`).join('');
      break;
    }
  }
  state.renderedTabs.add(tab);
}

function activeTab(): string {
  return document.querySelector<HTMLButtonElement>('.tab.active')!.dataset.tab!;
}

function syncUrl(): void {
  const q = new URLSearchParams({ session: state.slug, a: state.a, b: state.b });
  history.replaceState(null, '', `?${q.toString()}`);
}

function rerender(): void {
  renderMatchup();
  state.renderedTabs.clear();
  renderTab(activeTab());
  syncUrl();
}

async function selectSession(slug: string): Promise<void> {
  state.slug = slug;
  state.data = await loadSession(slug);
  const codes = Object.keys(state.data.drivers).sort();
  options($('driverA'), codes.map((c) => ({ value: c, label: c })), state.a);
  options($('driverB'), codes.map((c) => ({ value: c, label: c })), state.b);
  state.a = ($('driverA') as HTMLSelectElement).value;
  const selB = $('driverB') as HTMLSelectElement;
  if (selB.value === state.a && codes.length > 1) selB.value = codes.find((c) => c !== state.a)!;
  state.b = selB.value;
  rerender();
}

async function init(): Promise<void> {
  state.sessions = await loadIndex();
  options($('session'), state.sessions.map((s) => ({ value: s.slug, label: s.label })));

  // Shareable URLs: ?session=<slug>&a=<drv>&b=<drv>
  const q = new URLSearchParams(location.search);
  const wantSlug = q.get('session');
  state.a = q.get('a') ?? '';
  state.b = q.get('b') ?? '';
  const initial = state.sessions.find((s) => s.slug === wantSlug)?.slug ?? state.sessions[0].slug;
  ($('session') as HTMLSelectElement).value = initial;

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
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
      btn.classList.add('active');
      const tab = btn.dataset.tab!;
      document.querySelectorAll('.panel').forEach((p) => p.classList.add('hidden'));
      $(`panel-${tab}`).classList.remove('hidden');
      if (!state.renderedTabs.has(tab)) renderTab(tab);
    });
  });

  await selectSession(initial);
}

void init().catch((err) => {
  document.querySelector('main')!.innerHTML =
    `<p class="caption">Failed to load session data: ${esc(String(err))}</p>`;
});
