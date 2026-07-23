/** Shared visual tokens and F1 team colours (mirrors src/theme.py). */
import type { Config, Layout } from 'plotly.js';

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

const TEAM_COLORS: Record<string, string> = {
  'red bull': '#3671C6',
  ferrari: '#E8002D',
  mercedes: '#27F4D2',
  mclaren: '#FF8000',
  'aston martin': '#229971',
  alpine: '#2293D1',
  williams: '#64C4FF',
  rb: '#6692FF',
  alphatauri: '#6692FF',
  'racing bulls': '#6692FF',
  sauber: '#52E252',
  kick: '#52E252',
  'alfa romeo': '#C92D4B',
  haas: '#B6BABD',
};
const FALLBACK = ['#ff1801', '#00d2ff'];

export function teamColor(team: string | null | undefined, index = 0): string {
  if (team) {
    const t = team.toLowerCase();
    for (const [key, col] of Object.entries(TEAM_COLORS)) {
      if (t.includes(key)) return col;
    }
  }
  return FALLBACK[index % FALLBACK.length];
}

/** Two distinct colours for a driver pairing (nudged apart if same team). */
export function driverColors(teamA?: string | null, teamB?: string | null): [string, string] {
  const a = teamColor(teamA, 0);
  let b = teamColor(teamB, 1);
  if (a.toLowerCase() === b.toLowerCase()) b = a.toLowerCase() !== '#00d2ff' ? '#00d2ff' : '#ffb000';
  return [a, b];
}

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

export const PLOT_CONFIG: Partial<Config> = { displayModeBar: false, responsive: true };
