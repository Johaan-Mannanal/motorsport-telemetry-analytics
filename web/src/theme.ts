/** Shared visual tokens and F1 team colours (mirrors src/theme.py). */
import type { Config, Layout } from 'plotly.js';

export const BG = '#0d1117';
export const PANEL = '#141a22';
export const GRID = '#2a323d';
export const INK = '#e6edf3';
export const MUTED = '#9aa7b4';
export const ACCENT = '#ff1801';

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

/** Base Plotly layout matching the dark theme. */
export function baseLayout(title: string, height = 340): Partial<Layout> {
  return {
    title: { text: title, font: { color: INK, size: 16 } },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: INK, family: 'Inter, system-ui, sans-serif', size: 13 },
    xaxis: { gridcolor: GRID, zerolinecolor: GRID, linecolor: GRID },
    yaxis: { gridcolor: GRID, zerolinecolor: GRID, linecolor: GRID },
    legend: { bgcolor: 'rgba(0,0,0,0)' },
    margin: { l: 56, r: 20, t: 48, b: 44 },
    height,
  };
}

export const PLOT_CONFIG: Partial<Config> = { displayModeBar: false, responsive: true };
