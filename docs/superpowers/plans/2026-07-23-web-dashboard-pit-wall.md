# Web Dashboard "Pit Wall" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin and restructure the `web/` F1 dashboard to the approved "Pit Wall" design — carbon shell, red-as-signal, broadcast timing-tower header, timing rows, stint bars, full Plotly restyle — with zero new dependencies.

**Architecture:** Tokens live in `web/src/style.css` (CSS custom properties) and `web/src/theme.ts` (the same values for Plotly + team/compound colors). Structure changes happen in `web/index.html`; new DOM renderers (matchup, sector timing rows, stint bars, weather/model stat tiles, lights-out loader) go in `web/src/main.ts`; every Plotly chart adopts one shared template from `theme.ts`. `web/src/data.ts` and `web/src/analysis.ts` are never touched.

**Tech Stack:** Vite 6 + TypeScript 5 (strict), plotly.js-dist-min, vanilla CSS. Fonts via Google Fonts.

**Spec:** `docs/superpowers/specs/2026-07-23-web-dashboard-pit-wall-design.md`

## Global Constraints

- Zero new npm dependencies.
- DO NOT modify `web/src/data.ts`, `web/src/analysis.ts`, `web/public/data/*`, or anything outside `web/`.
- Every displayed value keeps its exact current derivation (same fields, same `toFixed` precision).
- Palette: bg `#0a0b0d`, panel `#111317`, panel-2 `#171a1f`, border `#23272e`, border-2 `#2e333b`, ink `#e8eaed`, muted `#98a0a8`, faint `#6a7178`, red `#e10600` (accent ONLY: active tab, lights, focus, faster-arrow, improvement stat).
- Fonts: Inter (400/500/600) + JetBrains Mono (500/700), `tabular-nums` on numerals. Rajdhani is removed.
- Team colors (`TEAM_COLORS`, `driverColors`) unchanged. Compound colors: SOFT `#ff2d55`, MEDIUM `#ffd60a`, HARD `#e8eaed`, INTERMEDIATE `#30d158`, WET `#0a84ff`.
- All new motion disabled under `prefers-reduced-motion: reduce`.
- After every task: `cd web && npm run build` (tsc --noEmit && vite build) must pass. No test suite exists — build + stated visual check is the verification. Dev server: `cd web && npm run dev` → http://localhost:5173.
- ARIA roles (`tablist`/`tab`/`tabpanel`, `aria-live` on matchup) preserved.

---

### Task 1: Tokens, fonts, and shell CSS

**Files:**
- Modify: `web/index.html` (font link line 12, theme-color line 8)
- Modify: `web/src/style.css` (full rewrite)
- Modify: `web/src/theme.ts` (color constants + compound exports; NOT baseLayout — that's Task 3)

**Interfaces:**
- Produces: CSS tokens (`--bg`, `--panel`, `--panel-2`, `--border`, `--border-2`, `--ink`, `--muted`, `--faint`, `--red`, `--red-soft`, `--mono`); theme.ts exports `BG, PANEL, PANEL2, GRID, INK, MUTED, FAINT, ACCENT, COMPOUND_COLORS, compoundColor(c), compoundText(c), hexAlpha(hex, alpha)`. All later tasks consume these.

- [ ] **Step 1: Fonts + theme-color in `web/index.html`**

Replace line 8 with:
```html
  <meta name="theme-color" content="#0a0b0d" />
```
Replace the font link (line 12) with:
```html
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet" />
```

- [ ] **Step 2: Update `web/src/theme.ts` constants**

Replace lines 4–9 with:
```ts
export const BG = '#0a0b0d';
export const PANEL = '#111317';
export const PANEL2 = '#171a1f';
export const GRID = '#23272e';
export const INK = '#e8eaed';
export const MUTED = '#98a0a8';
export const FAINT = '#6a7178';
export const ACCENT = '#e10600';

/** Tyre compound colors (single source; used by stint bars and the degradation chart). */
export const COMPOUND_COLORS: Record<string, string> = {
  SOFT: '#ff2d55',
  MEDIUM: '#ffd60a',
  HARD: '#e8eaed',
  INTERMEDIATE: '#30d158',
  WET: '#0a84ff',
};

export function compoundColor(compound: string): string {
  return COMPOUND_COLORS[compound.toUpperCase()] ?? MUTED;
}

/** Text color that stays readable on a compound-colored fill. */
export function compoundText(compound: string): string {
  return ['MEDIUM', 'HARD'].includes(compound.toUpperCase()) ? BG : INK;
}

/** '#rrggbb' + alpha -> 'rgba(...)'. */
export function hexAlpha(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}
```
(Leave `TEAM_COLORS`, `FALLBACK`, `teamColor`, `driverColors`, `baseLayout`, `PLOT_CONFIG` as they are for now. `baseLayout` still compiles because it only uses GRID/INK.)

- [ ] **Step 3: Rewrite `web/src/style.css`**

Replace the entire file with:
```css
:root {
  --bg: #0a0b0d;
  --panel: #111317;
  --panel-2: #171a1f;
  --border: #23272e;
  --border-2: #2e333b;
  --ink: #e8eaed;
  --muted: #98a0a8;
  --faint: #6a7178;
  --red: #e10600;
  --red-soft: rgba(225, 6, 0, 0.12);
  --mono: 'JetBrains Mono', ui-monospace, monospace;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--ink);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.55;
}

.wrap { width: min(100% - 36px, 1180px); margin-inline: auto; }
.mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }
.hidden { display: none; }

:focus-visible { outline: 2px solid var(--red); outline-offset: 2px; border-radius: 4px; }

/* Header */
.top { border-bottom: 1px solid var(--border); background: rgba(10, 11, 13, 0.85); backdrop-filter: blur(8px); position: sticky; top: 0; z-index: 10; }
.top-inner { display: flex; align-items: center; justify-content: space-between; height: 56px; }
.brand { display: flex; align-items: center; gap: 12px; }
.brand h1 { font-size: 1.02rem; font-weight: 600; letter-spacing: 0.2px; }
.brand em { color: var(--red); font-style: normal; }
.lights { display: flex; gap: 4px; }
.lights i { width: 9px; height: 9px; border-radius: 50%; background: rgba(225, 6, 0, 0.22); transition: background 0.12s, box-shadow 0.12s; }
.lights i.on { background: var(--red); box-shadow: 0 0 10px rgba(225, 6, 0, 0.8); }
.top-links a { color: var(--muted); font-family: var(--mono); font-size: 0.78rem; text-decoration: none;
  border: 1px solid var(--border-2); border-radius: 8px; padding: 7px 12px; }
.top-links a:hover { color: var(--ink); border-color: var(--muted); }

/* Controls */
.controls { display: flex; flex-wrap: wrap; gap: 16px; margin: 24px 0 12px; }
.controls label { display: flex; flex-direction: column; gap: 6px; font-size: 0.7rem;
  letter-spacing: 1.5px; text-transform: uppercase; color: var(--faint); font-family: var(--mono); }
.controls select {
  background: var(--panel); color: var(--ink); border: 1px solid var(--border-2);
  border-radius: 9px; padding: 9px 12px; font-size: 0.95rem; min-width: 150px; cursor: pointer;
}
.controls select:first-of-type { min-width: 300px; }
.controls select:focus-visible { outline: 2px solid var(--red); }

/* Matchup timing tower */
.matchup { display: grid; grid-template-columns: 1fr auto 1fr; align-items: stretch; gap: 14px;
  background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
  padding: 16px 18px; margin: 14px 0 6px; }
.chip { display: flex; align-items: center; gap: 14px; min-width: 0; }
.chip-b { flex-direction: row-reverse; text-align: right; }
.chip-bar { width: 4px; align-self: stretch; border-radius: 2px; background: var(--team); flex: 0 0 auto; }
.chip-txt { display: flex; flex-direction: column; gap: 2px; line-height: 1.2; min-width: 0; }
.chip .abbr { font-family: var(--mono); font-weight: 700; font-size: 1.55rem; letter-spacing: 1px; }
.chip .team { color: var(--muted); font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chip .lap { font-family: var(--mono); color: var(--muted); font-size: 0.9rem; font-variant-numeric: tabular-nums; }
.gap { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; padding: 0 10px; }
.gap-v { font-family: var(--mono); font-weight: 700; font-size: 2.3rem; line-height: 1; font-variant-numeric: tabular-nums; }
.gap-sub { font-size: 0.78rem; font-weight: 600; }
.session-sub { color: var(--faint); font-size: 0.78rem; font-family: var(--mono);
  letter-spacing: 1px; text-transform: uppercase; margin: 6px 2px 14px; }

/* Tabs — segmented control */
.tabs { display: inline-flex; gap: 2px; background: var(--panel); border: 1px solid var(--border);
  border-radius: 10px; padding: 3px; margin-bottom: 18px; overflow-x: auto; max-width: 100%; }
.tab { background: none; border: none; color: var(--muted); font-family: 'Inter', system-ui, sans-serif;
  font-weight: 500; font-size: 0.88rem; padding: 8px 14px; cursor: pointer; border-radius: 8px;
  white-space: nowrap; position: relative; }
.tab:hover { color: var(--ink); }
.tab.active { color: var(--ink); background: var(--panel-2); box-shadow: inset 0 -2px 0 var(--red); }

/* Panels & charts */
.panel { margin-bottom: 40px; }
.chart { background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
  padding: 6px; margin-bottom: 14px; min-height: 200px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.grid-track { display: grid; grid-template-columns: 3fr 2fr; gap: 14px; align-items: start; }
.caption { color: var(--faint); font-size: 0.82rem; margin: 4px 0 14px; }
.demo-note { margin: -6px 0 12px; }
.demo-note a { color: var(--muted); text-decoration: underline; }
.subh { font-size: 0.78rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--muted); margin: 14px 0 8px; }

/* Stat tiles (weather, model metrics) */
.stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px; }
.stat { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
  padding: 12px 14px; display: flex; flex-direction: column; gap: 3px; }
.stat-k { color: var(--faint); font-size: 0.72rem; letter-spacing: 1px; text-transform: uppercase; font-family: var(--mono); }
.stat-v { font-family: var(--mono); font-weight: 700; font-size: 1.4rem; font-variant-numeric: tabular-nums; }
.stat-accent .stat-v { color: var(--red); }

/* Sector timing rows */
.timing { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.t-row { display: grid; grid-template-columns: 52px 1fr 1fr 96px; align-items: center;
  padding: 11px 14px; border-bottom: 1px solid var(--border); }
.t-row:last-child { border-bottom: none; }
.t-head { color: var(--faint); font-size: 0.72rem; letter-spacing: 1px; text-transform: uppercase; padding-block: 9px; }
.t-k { color: var(--faint); font-size: 0.78rem; letter-spacing: 1px; }
.t-v { font-variant-numeric: tabular-nums; font-size: 0.95rem; padding-left: 10px; }
.t-d { text-align: right; }
.t-chip { display: inline-block; border-radius: 6px; padding: 2px 8px; font-size: 0.8rem;
  font-weight: 700; font-variant-numeric: tabular-nums; }

/* Stint bars */
.stints { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px 26px; }
.lane { display: grid; grid-template-columns: 56px 1fr; align-items: center; gap: 12px; margin-bottom: 12px; }
.lane-k { color: var(--muted); font-weight: 700; font-size: 0.9rem; }
.lane-track { position: relative; height: 30px; background: var(--bg); border-radius: 6px; }
.seg { position: absolute; top: 0; height: 100%; border-radius: 6px; overflow: hidden;
  display: flex; align-items: center; padding: 0 8px; box-shadow: 0 0 0 2px var(--panel); }
.seg-label { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.5px; white-space: nowrap; }
.lane-axis { position: relative; height: 16px; margin-left: 68px; }
.lane-axis .tick { position: absolute; transform: translateX(-50%); color: var(--faint); font-size: 0.68rem; }

/* Methodology notes */
.notes { margin-top: 8px; color: var(--muted); background: var(--panel); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px 16px; }
.notes summary { cursor: pointer; font-family: var(--mono); font-size: 0.8rem; }
.notes ul { margin: 10px 0 0 20px; font-size: 0.88rem; display: flex; flex-direction: column; gap: 6px; }

.foot { border-top: 1px solid var(--border); margin-top: 20px; padding: 18px 0 26px;
  color: var(--faint); font-size: 0.78rem; }

/* Lights-out loader & crossfades (behavior wired in Task 7) */
main.preload { opacity: 0; }
main.reveal { animation: reveal 0.3s ease-out; }
@keyframes reveal { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.panel:not(.hidden) { animation: fadein 0.15s ease-out; }
@keyframes fadein { from { opacity: 0; } to { opacity: 1; } }

@media (prefers-reduced-motion: reduce) {
  main.preload { opacity: 1; }
  main.reveal, .panel:not(.hidden) { animation: none; }
  .lights i { transition: none; }
}

@media (max-width: 760px) {
  .grid2, .grid-track { grid-template-columns: 1fr; }
  .controls select:first-of-type { min-width: 100%; }
  .matchup { grid-template-columns: 1fr; }
  .chip-b { flex-direction: row; text-align: left; }
  .gap { order: -1; }
}
```
Note: the old `.metrics/.metric` and `table` styles are intentionally gone — the interim state (Tasks 1→5) renders those elements with browser defaults on dark background, which is acceptable mid-refactor; Tasks 2/5/6 replace the markup. `.brand-mark` styles are gone; the lights markup arrives in Task 2.

- [ ] **Step 4: Build and visually verify**

Run: `cd web && npm run build` — Expected: pass.
On `npm run dev`: carbon shell, no red glow wash, Inter/mono type, segmented-looking tabs, red only on focus/active-tab/brand em.

- [ ] **Step 5: Commit**

```bash
git add web/index.html web/src/style.css web/src/theme.ts
git commit -m "Carbon tokens, Inter/mono type, and Pit Wall shell styles for the web dashboard"
```

---

### Task 2: Timing-tower header + matchup + segmented tabs

**Files:**
- Modify: `web/index.html` (brand lights, matchup/session-sub structure, remove `.metrics` section)
- Modify: `web/src/main.ts` (rewrite `renderMatchup`, delete `renderMetrics`)

**Interfaces:**
- Consumes: Task 1 CSS classes (`.lights`, `.matchup`, `.chip*`, `.gap*`, `.session-sub`), `hexAlpha` (not needed here), `DriverData` from `./data`.
- Produces: `renderMatchup(): void` covering chips + gap + session sub-bar; `#session-sub` element; `.lights i` elements consumed by Task 7's loader.

- [ ] **Step 1: Update `web/index.html` structure**

Replace the brand block (lines 18–21) with:
```html
      <div class="brand">
        <span class="lights" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>
        <h1>Telemetry <em>Analytics</em></h1>
      </div>
```
Replace the matchup + metrics + demo-note region (lines 41–49: the `demo-note` paragraph, `#matchup` section, and the whole `.metrics` section) with:
```html
    <section id="matchup" class="matchup" aria-live="polite"></section>
    <p class="session-sub" id="session-sub"></p>
    <p class="caption demo-note">Five bundled public-demo sessions. The <a href="https://github.com/Johaan-Mannanal/motorsport-telemetry-analytics">local Streamlit app</a> loads any session from 2018 onward.</p>
```
(The three `mAk/mAv/mBk/mBv/mGap/mGapSub` metric elements are gone. `#model-metrics` in the model panel stays — it's a different element.)

- [ ] **Step 2: Rewrite the matchup renderer in `web/src/main.ts`**

Replace `renderMatchup` (lines 33–41) and DELETE `renderMetrics` (lines 47–62) entirely, replacing both with:
```ts
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
```
In `rerender()` (lines 137–143), delete the `renderMetrics();` line.
(`.abbr`, `.lap`, `.gap-v` get mono via the Task 1 CSS — no `mono` class needed in the markup. Gap semantics unchanged: `fb - fa`, positive means A faster, exactly as the old `renderMetrics`.)

- [ ] **Step 3: Build and visually verify**

Run: `cd web && npm run build` — Expected: pass (TypeScript will error if any `renderMetrics` reference or `mAv`-style id lookup remains — remove them all).
On dev: header shows five dim red lights + wordmark; matchup is one panel — team-color bars, big mono codes, fastest laps in chips, big center gap with a colored arrow naming the faster driver; session label beneath in small caps; tabs render as a segmented pill.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/src/main.ts
git commit -m "Broadcast timing-tower matchup header with lights brand mark"
```

---

### Task 3: Plotly template + full chart restyle

**Files:**
- Modify: `web/src/theme.ts` (baseLayout rework)
- Modify: `web/src/charts.ts` (all renderers except `sectors`, which Task 4 deletes)

**Interfaces:**
- Consumes: Task 1 exports (`PANEL2`, `FAINT`, `compoundColor`, `hexAlpha`).
- Produces: `baseLayout(title, height?)` with unified hover/spikes (line charts); `endLabels(...)` annotation helper inside charts.ts. Task 4 relies on `charts.sectors` still existing after this task (unchanged).

- [ ] **Step 1: Rework `baseLayout` in `web/src/theme.ts`**

Replace the `baseLayout` function (lines 48–60) with:
```ts
/** Base Plotly layout: recessive grid, left-aligned muted titles, unified crosshair hover. */
export function baseLayout(title: string, height = 340): Partial<Layout> {
  const tickfont = { family: "'JetBrains Mono', ui-monospace, monospace", size: 11, color: FAINT };
  return {
    title: { text: title.toUpperCase(), font: { color: MUTED, size: 12 }, x: 0, xanchor: 'left' },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: INK, family: 'Inter, system-ui, sans-serif', size: 13 },
    xaxis: { gridcolor: GRID, zeroline: false, linecolor: 'rgba(0,0,0,0)', tickfont,
             showspikes: true, spikecolor: FAINT, spikethickness: 1, spikedash: 'dot', spikemode: 'across' },
    yaxis: { gridcolor: GRID, zeroline: false, linecolor: 'rgba(0,0,0,0)', tickfont },
    legend: { bgcolor: 'rgba(0,0,0,0)', font: { size: 10, color: FAINT } },
    hovermode: 'x unified',
    hoverlabel: { bgcolor: PANEL2, bordercolor: '#2e333b', font: { color: INK, family: 'Inter, system-ui, sans-serif', size: 12 } },
    margin: { l: 56, r: 52, t: 40, b: 44 },
    height,
  };
}
```

- [ ] **Step 2: Restyle every chart in `web/src/charts.ts`**

Update the theme import (line 7) to:
```ts
import { baseLayout, FAINT, MUTED, PLOT_CONFIG, compoundColor, hexAlpha } from './theme';
```
Add `Annotations` to the existing plotly type import (line 4), making it:
```ts
import type { Annotations, Config, Data, Layout, LayoutAxis, PlotData, PlotMarker } from 'plotly.js';
```
Add after the `react` helper (line 13):
```ts
/** Direct driver labels at each trace's right end (identity is never legend-only). */
function endLabels(entries: { x: number; y: number; text: string; color: string }[]): Partial<Annotations>[] {
  return entries.map((e) => ({
    x: e.x, y: e.y, xref: 'x' as const, yref: 'y' as const, text: e.text, showarrow: false,
    xanchor: 'left' as const, xshift: 6,
    font: { color: e.color, size: 11, family: "'JetBrains Mono', ui-monospace, monospace" },
  }));
}
```
Replace `lapPace` (lines 15–27) with:
```ts
export function lapPace(el: El, a: DriverData, b: DriverData, nameA: string, nameB: string,
                        colA: string, colB: string): void {
  const trace = (d: DriverData, name: string, color: string): Partial<PlotData> => ({
    x: d.laps.map((l) => l.LapNumber),
    y: d.laps.map((l) => l.sec),
    name, mode: 'lines+markers',
    line: { color, width: 2 }, marker: { size: 5 },
  });
  const layout = baseLayout('Lap time by lap');
  layout.xaxis = { ...layout.xaxis, title: { text: 'Lap number' } };
  layout.yaxis = { ...layout.yaxis, title: { text: 'Lap time (s)' } };
  const lastA = a.laps[a.laps.length - 1], lastB = b.laps[b.laps.length - 1];
  layout.annotations = endLabels([
    ...(lastA ? [{ x: lastA.LapNumber, y: lastA.sec, text: nameA, color: colA }] : []),
    ...(lastB ? [{ x: lastB.LapNumber, y: lastB.sec, text: nameB, color: colB }] : []),
  ]);
  react(el, [trace(a, nameA, colA), trace(b, nameB, colB)], layout);
}
```
Replace `delta` (lines 29–39) with:
```ts
export function delta(el: El, a: DriverData, b: DriverData, nameA: string, nameB: string,
                      colB: string): void {
  const d = deltaTime(a.telemetry, b.telemetry);
  const layout = baseLayout(`Delta time: ${nameB} relative to ${nameA}`);
  layout.xaxis = { ...layout.xaxis, title: { text: 'Distance (m)' } };
  layout.yaxis = { ...layout.yaxis, title: { text: `Δt (s)  +ve = ${nameB} slower` } };
  layout.shapes = [{ type: 'line', x0: d.x[0], x1: d.x[d.x.length - 1], y0: 0, y1: 0,
                     line: { color: MUTED, width: 1 } }];
  react(el, [{ x: d.x, y: d.y, mode: 'lines', line: { color: colB, width: 2 },
               fill: 'tozeroy', fillcolor: hexAlpha(colB, 0.1), name: nameB }], layout);
}
```
Replace `channel` (lines 41–51) with:
```ts
export function channel(el: El, ch: Channel, a: DriverData, b: DriverData,
                        nameA: string, nameB: string, colA: string, colB: string): void {
  const grid = commonGrid(a.telemetry, b.telemetry);
  const ya = interpolate(a.telemetry, ch, grid);
  const yb = interpolate(b.telemetry, ch, grid);
  const layout = baseLayout(`${ch} vs distance`);
  layout.xaxis = { ...layout.xaxis, title: { text: 'Distance (m)' } };
  layout.yaxis = { ...layout.yaxis, title: { text: ch } };
  const xEnd = grid[grid.length - 1];
  layout.annotations = endLabels([
    { x: xEnd, y: ya[ya.length - 1], text: nameA, color: colA },
    { x: xEnd, y: yb[yb.length - 1], text: nameB, color: colB },
  ]);
  react(el, [
    { x: grid, y: ya, name: nameA, mode: 'lines', line: { color: colA, width: 2 } },
    { x: grid, y: yb, name: nameB, mode: 'lines', line: { color: colB, width: 2 } },
  ], layout);
}
```
Replace `trackMap` (lines 53–63) with:
```ts
export function trackMap(el: El, d: DriverData, name: string): void {
  const layout = baseLayout(`${name} fastest lap speed`, 470);
  layout.xaxis = { visible: false };
  layout.yaxis = { visible: false, scaleanchor: 'x', scaleratio: 1 } as LayoutAxis;
  layout.hovermode = 'closest';
  react(el, [{
    x: d.position.map((p) => p.X), y: d.position.map((p) => p.Y), mode: 'markers',
    marker: { size: 4, color: d.position.map((p) => p.Speed), colorscale: 'Inferno',
              colorbar: { title: { text: 'km/h', font: { size: 11, color: MUTED } }, thickness: 10,
                          outlinewidth: 0, tickfont: { family: "'JetBrains Mono', ui-monospace, monospace", size: 10, color: FAINT } } } as Partial<PlotMarker>,
    hoverinfo: 'skip',
  }], layout);
}
```
Replace `degradation` (lines 82–93) with:
```ts
export function degradation(el: El, session: SessionData): void {
  const deg = session.model?.degradation ?? [];
  const layout = baseLayout('Tyre degradation (s lost per lap of tyre life)');
  layout.yaxis = { ...layout.yaxis, title: { text: 's / lap' } };
  layout.hovermode = 'closest';
  layout.xaxis = { ...layout.xaxis, showspikes: false };
  react(el, [{
    x: deg.map((d) => d.compound), y: deg.map((d) => d.slope_s_per_lap), type: 'bar',
    marker: { color: deg.map((d) => compoundColor(d.compound)) },
    text: deg.map((d) => d.slope_s_per_lap.toFixed(3)), textposition: 'outside',
    textfont: { family: "'JetBrains Mono', ui-monospace, monospace", size: 11, color: MUTED },
  }], layout);
}
```
Leave `sectors` (lines 65–80) untouched — Task 4 deletes it. (Its old dashed zeroline/`MUTED` import still compiles.)

- [ ] **Step 3: Build and visually verify**

Run: `cd web && npm run build` — Expected: pass.
On dev: all charts show muted small-caps left titles, mono tick labels, faint grid, unified crosshair tooltips on the line charts (dark panel tooltip), driver-code labels at the right ends of traces, track map in Inferno heat colors with a thin colorbar, delta fill tinted to driver B's team color.

- [ ] **Step 4: Commit**

```bash
git add web/src/theme.ts web/src/charts.ts
git commit -m "Shared Pit Wall Plotly template: unified hover, direct labels, Inferno track map"
```

---

### Task 4: Sector timing rows

**Files:**
- Modify: `web/index.html` (panel-track structure)
- Modify: `web/src/main.ts` (renderSectors + renderTab wiring)
- Modify: `web/src/charts.ts` (delete `sectors`)

**Interfaces:**
- Consumes: `hexAlpha` from `./theme`; Task 1 CSS (`.timing`, `.t-*`); `driver().fastest.sectors.s1/s2/s3`.
- Produces: `renderSectors(): void` in main.ts. `charts.sectors` no longer exists after this task.

- [ ] **Step 1: Update panel-track markup in `web/index.html`**

Replace the panel-track section (lines 75–80) with:
```html
    <section class="panel hidden" id="panel-track" role="tabpanel">
      <div class="grid-track">
        <div id="chart-track" class="chart"></div>
        <div>
          <h3 class="subh">Sector times (fastest lap)</h3>
          <div id="timing" class="timing"></div>
        </div>
      </div>
    </section>
```

- [ ] **Step 2: Add the renderer and rewire in `web/src/main.ts`**

Update the theme import (line 5) to:
```ts
import { driverColors, hexAlpha } from './theme';
```
Add after `renderMatchup`:
```ts
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
```
In `renderTab`, replace the `'track'` case with:
```ts
    case 'track':
      charts.trackMap('chart-track', A, state.a);
      renderSectors();
      break;
```
(The `'track'` case previously destructured `colA/colB` at the top of `renderTab` — that stays; `renderSectors` computes its own.)

- [ ] **Step 3: Delete `sectors` from `web/src/charts.ts`**

Remove the entire `sectors` function (lines 65–80). If `MUTED` is now unused in charts.ts, remove it from the import.

- [ ] **Step 4: Build and visually verify**

Run: `cd web && npm run build` — Expected: pass (build fails if any `charts.sectors` reference remains).
On dev, Track & sectors tab: Inferno track map left; right side a timing panel — header row with the two driver codes, three rows S1–S3, mono times, the faster time cell carrying a team-color inner bar, delta chip tinted with the faster driver's color.

- [ ] **Step 5: Commit**

```bash
git add web/index.html web/src/main.ts web/src/charts.ts
git commit -m "Replace sector bar chart with broadcast timing rows"
```

---

### Task 5: Stint bars + weather stat tiles

**Files:**
- Modify: `web/index.html` (panel-tyres structure)
- Modify: `web/src/main.ts` (renderStints/renderWeather; delete `table` helper)

**Interfaces:**
- Consumes: `compoundColor`, `compoundText` from `./theme`; Task 1 CSS (`.stints`, `.lane*`, `.seg*`, `.stat-row`, `.stat*`); `driver().stints` rows (`Stint, Compound, Laps, StartLap, EndLap`).
- Produces: `renderStints(): void`, `renderWeather(): void`. The generic `table()` helper is gone after this task.

- [ ] **Step 1: Update panel-tyres markup in `web/index.html`**

Replace the panel-tyres section (lines 82–89) with:
```html
    <section class="panel hidden" id="panel-tyres" role="tabpanel">
      <h3 class="subh">Stints</h3>
      <div id="stints" class="stints"></div>
      <h3 class="subh">Weather (session average)</h3>
      <div id="weather" class="stat-row"></div>
    </section>
```

- [ ] **Step 2: Renderers in `web/src/main.ts`**

Update the theme import to:
```ts
import { compoundColor, compoundText, driverColors, hexAlpha } from './theme';
```
DELETE the `table` helper (lines 64–70). Add after `renderSectors`:
```ts
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
```
Replace the `'tyres'` case in `renderTab` (currently lines 90–106) with:
```ts
    case 'tyres':
      renderStints();
      renderWeather();
      break;
```
(This also removes the now-dead `stintsAh/stintsBh/stintsA/stintsB` lookups. The weather VALUES are the same fields at the same raw precision as the old table.)

- [ ] **Step 3: Build and visually verify**

Run: `cd web && npm run build` — Expected: pass (fails if `table()` or the old stint element ids are still referenced).
On dev, Tyres tab: two labeled lanes with compound-colored stint segments over a shared lap axis (2px panel gaps between segments, labels clipped gracefully on short stints, hover title shows the lap range), lap ticks beneath; weather as a row of five stat tiles.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/src/main.ts
git commit -m "Compound-colored stint bars and weather stat tiles"
```

---

### Task 6: Pace-model stat tiles + notes restyle

**Files:**
- Modify: `web/index.html` (model-metrics class)
- Modify: `web/src/main.ts` (model case markup)

**Interfaces:**
- Consumes: Task 1 CSS (`.stat-row`, `.stat`, `.stat-accent`).
- Produces: nothing consumed later.

- [ ] **Step 1: Markup class in `web/index.html`**

In the model panel (line 94), change:
```html
      <div class="metrics" id="model-metrics"></div>
```
to:
```html
      <div class="stat-row" id="model-metrics"></div>
```

- [ ] **Step 2: Stat-tile markup in `web/src/main.ts`**

In the `'model'` case, replace the `box.innerHTML = [...]` statement (lines 114–119) with:
```ts
      box.innerHTML = ([
        ['Baseline MAE', `${m.baseline_mae.toFixed(3)}s`, ''],
        ['Model MAE', `${m.model_mae.toFixed(3)}s`, ''],
        ['Improvement', m.improvement_mae_pct != null ? `${m.improvement_mae_pct.toFixed(0)}%` : 'n/a', ' stat-accent'],
        ['Train / test laps', `${m.n_train} / ${m.n_test}`, ''],
      ] as [string, string, string][]).map(([k, v, cls]) =>
        `<div class="stat${cls}"><span class="stat-k">${k}</span><span class="stat-v">${v}</span></div>`).join('');
```

- [ ] **Step 3: Build and visually verify**

Run: `cd web && npm run build` — Expected: pass.
On dev, Pace model tab: four stat tiles, "Improvement" numeral in red (the page's only red number), degradation chart in compound colors, methodology notes in a bordered panel.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/src/main.ts
git commit -m "Pace-model stat tiles with a single red improvement numeral"
```

---

### Task 7: Lights-out loader + crossfades

**Files:**
- Modify: `web/index.html` (preload class on `<main>`)
- Modify: `web/src/main.ts` (loader + init wiring)

**Interfaces:**
- Consumes: `.lights i` elements (Task 2), CSS classes `main.preload`, `main.reveal`, panel `fadein` (Task 1 — already shipped).
- Produces: the complete refresh.

- [ ] **Step 1: Preload class in `web/index.html`**

Change `<main class="wrap">` (line 28) to:
```html
  <main class="wrap preload">
```
(With CSS shipped in Task 1, no-JS users are covered? No — `main.preload { opacity: 0 }` would hide content without JS. Guard it: this page is fully JS-rendered anyway — without JS there is no content at all — so the preload class is safe here. This is the documented reasoning; do not add an html.js gate.)

- [ ] **Step 2: Loader in `web/src/main.ts`**

Add near the top (after the `$` helper):
```ts
const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** Five lights on, hold, lights out — once per page load. */
async function lightsOut(): Promise<void> {
  const main = document.querySelector('main')!;
  if (REDUCED) { main.classList.remove('preload'); return; }
  const lights = Array.from(document.querySelectorAll('.lights i'));
  for (const l of lights) { l.classList.add('on'); await sleep(180); }
  await sleep(500);
  lights.forEach((l) => l.classList.remove('on'));
  main.classList.remove('preload');
  main.classList.add('reveal');
}
```
At the end of `init()`, replace `await selectSession(initial);` with:
```ts
  const lightsDone = lightsOut();
  await selectSession(initial);
  await lightsDone;
```
Also add the session/driver-switch crossfade: in `rerender()`, after `renderTab(activeTab());`, insert:
```ts
  // Restart the active panel's fade so session/driver switches read as a quiet crossfade.
  const activePanel = document.querySelector<HTMLElement>('.panel:not(.hidden)');
  if (activePanel && !REDUCED) {
    activePanel.style.animation = 'none';
    void activePanel.offsetHeight;   // reflow to reset the animation
    activePanel.style.animation = '';
  }
```
Also: in the init error handler at the bottom of the file, reveal the main element so the error is visible even if the loader never finished:
```ts
void init().catch((err) => {
  const main = document.querySelector('main')!;
  main.classList.remove('preload');
  main.innerHTML = `<p class="caption">Failed to load session data: ${esc(String(err))}</p>`;
});
```

- [ ] **Step 3: Build and visually verify**

Run: `cd web && npm run build` — Expected: pass.
On dev, hard reload: five lights illuminate left-to-right, hold, cut out together as the dashboard fades up (~1.6s total). Switching sessions or tabs afterward: only quick 150ms fades, no lights. With reduced-motion emulated: content appears immediately, lights stay dim.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/src/main.ts
git commit -m "Lights-out load sequence and quiet crossfades"
```

---

### Task 8: Static verification pass

**Files:** none created — checks only (fix anything found, then commit fixes if any).

- [ ] **Step 1: Static checks**

From the repo root, run and record results:
```bash
cd web && npm run build                                  # must pass
grep -rn "Rajdhani" web/index.html web/src/ || echo OK   # expect OK
grep -rn "#ff1801\|#0d1117" web/src/style.css web/index.html || echo OK   # expect OK
grep -rn "Turbo" web/src/ || echo OK                     # expect OK (Inferno replaced it)
grep -n "ff1801" web/src/theme.ts                        # EXPECTED 1 hit: the FALLBACK driver color (a data color, kept deliberately)
grep -c "hovermode" web/src/theme.ts                     # expect 1 (the template)
```
Also confirm `web/src/data.ts` and `web/src/analysis.ts` show no diff: `git diff --stat main -- web/src/data.ts web/src/analysis.ts` must be empty.

- [ ] **Step 2: Report**

List anything deferred to the in-browser pass (the controller runs it): five tabs × two sessions (a race + Monaco qualifying for the no-model/short-stint paths), hover tooltips, narrow-segment stint labels, 390px layout, reduced-motion, `?session=&a=&b=` URL params.

---

### Out of scope / follow-ups (do NOT do in this plan)

- Streamlit app theme, README/portfolio screenshots (`motorsport.png`), `web/public/favicon.svg` refresh — favicon already matches the red identity; leave it.
- Pushing to origin / deploying — Johaan reviews locally first.
