/** App wiring: session/driver selection, matchup header, tabs, chart rendering. */

import * as charts from './charts';
import { loadIndex, loadSession, type DriverData, type SessionData, type SessionRef } from './data';
import { driverColors } from './theme';

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

function renderMatchup(): void {
  const [colA, colB] = colors();
  const chip = (code: string, col: string) => {
    const team = driver(code).team ?? '';
    return `<div class="chip"><span class="dot" style="background:${col}"></span>
      <span class="txt"><span class="abbr">${esc(code)}</span><span class="team">${esc(team)}</span></span></div>`;
  };
  $('matchup').innerHTML = `${chip(state.a, colA)}<span class="vs">VS</span>${chip(state.b, colB)}`;
}

function colors(): [string, string] {
  return driverColors(driver(state.a).team, driver(state.b).team);
}

function renderMetrics(): void {
  const fa = driver(state.a).fastest.sec;
  const fb = driver(state.b).fastest.sec;
  $('mAk').textContent = `${state.a} fastest lap`;
  $('mBk').textContent = `${state.b} fastest lap`;
  $('mAv').textContent = fa != null ? `${fa.toFixed(3)}s` : 'n/a';
  $('mBv').textContent = fb != null ? `${fb.toFixed(3)}s` : 'n/a';
  if (fa != null && fb != null) {
    const gap = fb - fa;
    $('mGap').textContent = `${gap >= 0 ? '+' : ''}${gap.toFixed(3)}s`;
    $('mGapSub').textContent = `${gap > 0 ? state.a : state.b} faster`;
  } else {
    $('mGap').textContent = 'n/a';
    $('mGapSub').textContent = '';
  }
}

function table(rows: Record<string, unknown>[], cols: [string, string][]): string {
  if (!rows.length) return '<p class="caption">No data.</p>';
  const head = cols.map(([, label]) => `<th>${esc(label)}</th>`).join('');
  const body = rows.map((r) =>
    `<tr>${cols.map(([k]) => `<td>${esc(String(r[k] ?? ''))}</td>`).join('')}</tr>`).join('');
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
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
      charts.sectors('chart-sectors', A, B, state.a, state.b, colA, colB);
      break;
    case 'tyres': {
      const stintCols: [string, string][] = [['Stint', 'Stint'], ['Compound', 'Compound'],
        ['Laps', 'Laps'], ['StartLap', 'Start'], ['EndLap', 'End']];
      $('stintsAh').textContent = `${state.a} stints`;
      $('stintsBh').textContent = `${state.b} stints`;
      $('stintsA').innerHTML = table(A.stints, stintCols);
      $('stintsB').innerHTML = table(B.stints, stintCols);
      const w = state.data!.weather;
      $('weather').innerHTML = w
        ? table([
            { k: 'Air temp (°C)', v: w.airTemp }, { k: 'Track temp (°C)', v: w.trackTemp },
            { k: 'Humidity (%)', v: w.humidity }, { k: 'Wind (m/s)', v: w.windSpeed },
            { k: 'Rainfall', v: w.rain ? 'Yes' : 'No' },
          ], [['k', 'Metric'], ['v', 'Value']])
        : '<p class="caption">No weather data.</p>';
      break;
    }
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
  renderMetrics();
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
