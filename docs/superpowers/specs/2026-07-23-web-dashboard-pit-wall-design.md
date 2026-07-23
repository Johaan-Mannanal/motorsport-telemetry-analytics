# Web Dashboard Refresh — "Pit Wall"

**Date:** 2026-07-23
**Status:** Approved by Johaan (scope, identity, type, chart depth, motion, and approach "C — full broadcast concept" confirmed in conversation)
**Scope:** `web/` only — the Vite/TypeScript dashboard deployed at motorsport-telemetry-analytics.vercel.app. The Streamlit app, Python analysis code, data formats, and README assets are untouched.

## Goals

- **Clean and premium; the design stays out of the data's way.** Restraint over spectacle.
- Own identity: **refined racing red** — a calm carbon shell where F1 red appears only as a signal. Deliberately NOT the portfolio's obsidian-and-gold family.
- Full restyle of the Plotly charts so charts and chrome read as one system.
- Broadcast-grade structure: timing-tower matchup header, timing-screen sector rows, stint bars.

## Non-goals

- No new npm dependencies. No React/Tailwind.
- No changes to `data.ts` accessors, `analysis.ts` math, the JSON data format, or any displayed value's derivation.
- No Streamlit/theme.py changes; no README screenshot regeneration (follow-up).

## 1. Design tokens (`web/src/style.css` + `web/src/theme.ts`)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0a0b0d` | Page (carbon near-black; flat — the current red radial glow is removed) |
| `--panel` | `#111317` | Cards, chart panels, chips |
| `--panel-2` | `#171a1f` | Raised elements (segmented control, tooltips) |
| `--border` | `#23272e` | Hairlines (neutral gray — NOT red-tinted) |
| `--border-2` | `#2e333b` | Interactive borders |
| `--ink` | `#e8eaed` | Primary text |
| `--muted` | `#98a0a8` | Secondary text |
| `--faint` | `#6a7178` | Captions, labels |
| `--red` | `#e10600` | THE accent: active tab underline, brand lights, focus rings, "faster" arrow. Never body text, never decorative washes. |
| `--red-soft` | `rgba(225, 6, 0, 0.12)` | Active-state fills |

Fonts: **Inter** (400/500/600) for UI, **JetBrains Mono** (500/700) for all numerals with `font-variant-numeric: tabular-nums`. Rajdhani is removed from the Google Fonts link. `theme.ts` exports the same values for Plotly (`BG`, `PANEL`, `GRID = #23272e`, `INK`, `MUTED`, `ACCENT = #e10600`).

Radii 10–12px; panel padding 16–20px; `theme-color` meta → `#0a0b0d`. Team colors (`TEAM_COLORS`, `driverColors` nudge logic) unchanged — they are the data's categorical palette, bound to entities.

## 2. Header — broadcast timing tower

Replaces the current brand bar + controls + chips + 3 metric tiles stack:

- **Brand bar** (sticky, as today): brand mark becomes **five small light dots** (`.lights`, 5 `<i>` elements) in a row — dark until the loader plays, then resting state: all dim red. Wordmark "Telemetry **Analytics**" in Inter 600 (accent word in `--red`), Source link styled as today but neutral.
- **Controls row** unchanged structurally (session + Driver A + Driver B selects), restyled: mono uppercase labels, `--panel` selects, red focus ring.
- **Matchup strip** (`#matchup`, one panel, CSS grid `1fr auto 1fr`):
  - Left/right: **driver chips** — a 4px full-height **team-color vertical bar** on the chip's outer edge, driver code in JetBrains Mono 700 ~1.6rem, team name muted below, and that driver's **fastest lap time** in mono beneath (absorbing today's per-driver metric tiles).
  - Center: **the gap** — `+0.123s` as one large mono numeral (~2.4rem), with a small arrow + "CODE faster" line under it pointing at the winner; the arrow/text uses the winner's team color. When either lap is missing: `n/a`, no arrow.
  - Below the strip, a thin **session sub-bar**: event label from the session index (e.g. "2023 Italian Grand Prix — Race") in muted small-caps.
- The standalone `.metrics` section on the main page is removed (its data moved into the chips/center). The `renderMetrics()` logic in `main.ts` is folded into `renderMatchup()`.
- Demo-note caption stays, moved under the session sub-bar.

## 3. Tabs — segmented control

Same five tabs, same `data-tab` wiring. Restyle: one `--panel` pill container, segments as buttons; active segment gets `--panel-2` fill, `--ink` text, and a 2px `--red` underline inside the segment. Inter 500, no uppercase. Keyboard focus ring red. Horizontal scroll preserved on narrow screens.

## 4. Tab internals

### 4.1 Lap pace + Telemetry tabs
Structure unchanged (delta chart, 2×2 channel grid). Charts restyled via the template (§5). Captions stay.

### 4.2 Track & sectors
- Track map: colorscale **`Turbo` → `Inferno`** (perceptually-uniform dark→hot ramp; Turbo is a rainbow and fails the sequential-color rule). Colorbar restyled (thin, mono ticks, muted title "km/h").
- The sector-delta **bar chart is replaced by timing-screen rows** (plain DOM, new renderer in `main.ts`): a `.timing` panel with three rows S1/S2/S3. Each row: sector label (mono, faint) | A's sector time (mono) | B's sector time (mono) | **delta chip** `+0.123` right-aligned, chip background at 15% of the faster driver's team color with the team color as text. Faster driver's time cell gets a 3px team-color left bar. Sector times come from `fastest.sectors.s1/s2/s3` exactly as the current chart does; missing sector → `–` and no chip. `charts.sectors` is deleted.

### 4.3 Tyres & weather
- The two stint `<table>`s are replaced by **stint bars** (plain DOM/CSS, new renderer): one labeled lane per driver (code in mono at left), a full-width track representing laps 1→max(EndLap of both drivers), and one absolutely-positioned segment per stint spanning `StartLap→EndLap`, filled with the compound color, labeled `COMPOUND · n laps` inside (or a tooltip-title when the segment is under ~64px wide). 2px gaps between segments; lap-number ticks (start, quartiles, end) in faint mono under the lanes.
- Compound colors (single source, exported from `theme.ts`, also consumed by `charts.degradation`): SOFT `#ff2d55`, MEDIUM `#ffd60a`, HARD `#e8eaed`, INTERMEDIATE `#30d158`, WET `#0a84ff`. HARD/MEDIUM segments (light fills) use dark text `#0a0b0d`; SOFT/INTER/WET use `--ink`.
- Weather table → one row of five small **stat tiles** (label + mono value): air temp, track temp, humidity, wind, rainfall. Missing weather → single caption line, as today.

### 4.4 Pace model
- The four model metrics become **stat tiles** (mono numerals ~1.5rem, muted labels); the "Improvement" tile value is the page's one red numeral.
- Degradation chart keeps its form (bar, compound colors from the shared export), restyled via the template; per-bar value labels stay.
- Methodology `<details>` restyled (panel background, mono summary).

## 5. Plotly template (`theme.ts` → consumed by every chart in `charts.ts`)

- Backgrounds transparent (panel provides the surface); grid `#23272e` at reduced prominence (`gridwidth: 1`, no zeroline except where meaningful); axis lines off; ticks mono 11px `--faint`.
- Titles: left-aligned (`x: 0`), 12px, `--muted`, uppercase with letter-spacing (set via title text styling), so panels read as labeled instruments rather than captioned figures.
- Font stack: Inter for labels/legend, `JetBrains Mono` for tick labels (`tickfont.family`).
- **Hover:** `hovermode: 'x unified'` on all distance/lap line charts with `spikelines` (thin, `--faint`, dash dot); styled `hoverlabel` (`--panel-2` bg, `--border-2` border, Inter 12px, mono numbers via unified formatting). Bar charts keep per-mark hover.
- Traces: 2px lines (unchanged); lap-pace markers 5px (unchanged).
- **Direct labels:** lap-pace and each channel chart add a text annotation with the driver code at each trace's right end in the team color — identity is never legend-only. Legends stay, recessive (10px, `--faint`).
- Delta chart: zero-line solid `--muted` 1px (today dashed); fill `tozeroy` re-tinted to **driver B's team color at 10% alpha** (replacing the hardcoded cyan `rgba(0,210,255,0.10)`).
- Margins tightened (t: 40 with the smaller titles).

## 6. Motion

- **Signature — "lights out":** on the FIRST session load only: the dashboard content is hidden; the five brand lights illuminate bright red one-by-one (~180ms apart), hold ~500ms, then all cut to dim simultaneously as the content fades/translates in (~300ms). Total ≈ 1.6s. Implemented in `main.ts` + CSS classes; runs once per page load (not per session switch).
- Session/driver switches and tab changes: 150ms opacity crossfade on the panel container. No count-ups (numbers are precise timing data — they appear set).
- `prefers-reduced-motion: reduce`: no lights sequence (content renders immediately, lights sit in resting state), no crossfades.

## 7. Files touched

- `web/index.html` — header/matchup/metrics/tabs/panel structure edits; font link (drop Rajdhani); theme-color.
- `web/src/style.css` — full rewrite on the new tokens.
- `web/src/theme.ts` — tokens, compound-color export, Plotly template/hover/config.
- `web/src/charts.ts` — template adoption in every renderer; Inferno; delta fill; direct labels; delete `sectors`.
- `web/src/main.ts` — matchup+gap renderer (absorbs `renderMetrics`), timing-rows renderer, stint-bars renderer, weather tiles, model stat tiles, lights-out loader, crossfades.
- NOT touched: `web/src/data.ts`, `web/src/analysis.ts`, `web/public/data/*`, everything outside `web/`.

## 8. Accessibility & correctness constraints

- All displayed values keep their exact current derivations (same fields, same `toFixed` precisions).
- `role="tablist"/"tab"/"tabpanel"` and `aria-live` on the matchup preserved; stint bars and timing rows are real text in the DOM (screen-reader readable), not canvas.
- Red is never the only carrier of meaning (deltas are signed numbers; the winner is named in text). `--red` on `--bg` is used at display sizes/weights only.
- Contrast: `--ink` and `--muted` on `--panel` ≥ AA; compound-segment text follows the light/dark fill rule in §4.3.
- Reduced-motion coverage per §6.
- `npm run build` (`tsc --noEmit && vite build`) must pass; no `any`-typed escapes added.

## 9. Verification

- Build passes; browser pass at ~1280px and ~390px on all five tabs × at least two sessions (a race and the Monaco qualifying, which exercises missing-model and short-stint paths).
- Hover/tooltip check on line charts; stint-bar labels on narrow segments; timing rows with a missing sector (if present in bundled data, else forced via dev tools).
- Reduced-motion pass. `?session=&a=&b=` URL params still work.
