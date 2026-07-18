/** Plotly chart renderers for the dashboard. */

import Plotly from 'plotly.js-dist-min';
import type { Config, Data, Layout, LayoutAxis, PlotData, PlotMarker } from 'plotly.js';
import { deltaTime, interpolate, commonGrid, type Channel } from './analysis';
import type { DriverData, SessionData } from './data';
import { baseLayout, MUTED, PLOT_CONFIG } from './theme';

type El = string; // element id

function react(el: El, traces: Partial<PlotData>[], layout: Partial<Layout>): void {
  void Plotly.react(el, traces as Data[], layout as Layout, PLOT_CONFIG as Config);
}

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
  react(el, [trace(a, nameA, colA), trace(b, nameB, colB)], layout);
}

export function delta(el: El, a: DriverData, b: DriverData, nameA: string, nameB: string,
                      colB: string): void {
  const d = deltaTime(a.telemetry, b.telemetry);
  const layout = baseLayout(`Delta time: ${nameB} relative to ${nameA}`);
  layout.xaxis = { ...layout.xaxis, title: { text: 'Distance (m)' } };
  layout.yaxis = { ...layout.yaxis, title: { text: `Δt (s)  +ve = ${nameB} slower` } };
  layout.shapes = [{ type: 'line', x0: d.x[0], x1: d.x[d.x.length - 1], y0: 0, y1: 0,
                     line: { color: MUTED, dash: 'dash', width: 1 } }];
  react(el, [{ x: d.x, y: d.y, mode: 'lines', line: { color: colB, width: 2 },
               fill: 'tozeroy', fillcolor: 'rgba(0,210,255,0.10)', name: nameB }], layout);
}

export function channel(el: El, ch: Channel, a: DriverData, b: DriverData,
                        nameA: string, nameB: string, colA: string, colB: string): void {
  const grid = commonGrid(a.telemetry, b.telemetry);
  const layout = baseLayout(`${ch} vs distance`);
  layout.xaxis = { ...layout.xaxis, title: { text: 'Distance (m)' } };
  layout.yaxis = { ...layout.yaxis, title: { text: ch } };
  react(el, [
    { x: grid, y: interpolate(a.telemetry, ch, grid), name: nameA, mode: 'lines', line: { color: colA, width: 2 } },
    { x: grid, y: interpolate(b.telemetry, ch, grid), name: nameB, mode: 'lines', line: { color: colB, width: 2 } },
  ], layout);
}

export function trackMap(el: El, d: DriverData, name: string): void {
  const layout = baseLayout(`${name} fastest lap speed`, 470);
  layout.xaxis = { visible: false };
  layout.yaxis = { visible: false, scaleanchor: 'x', scaleratio: 1 } as LayoutAxis;
  react(el, [{
    x: d.position.map((p) => p.X), y: d.position.map((p) => p.Y), mode: 'markers',
    marker: { size: 4, color: d.position.map((p) => p.Speed), colorscale: 'Turbo',
              colorbar: { title: { text: 'km/h' } } } as Partial<PlotMarker>,
    hoverinfo: 'skip',
  }], layout);
}

export function sectors(el: El, a: DriverData, b: DriverData, nameA: string, nameB: string,
                        colA: string, colB: string): void {
  const keys = ['s1', 's2', 's3'] as const;
  const deltas = keys.map((k) => {
    const sa = a.fastest.sectors[k], sb = b.fastest.sectors[k];
    return sa != null && sb != null ? +(sb - sa).toFixed(3) : null;
  });
  const layout = baseLayout(`Sector deltas: ${nameB} minus ${nameA}`);
  layout.yaxis = { ...layout.yaxis, title: { text: 'Δt (s)' } };
  react(el, [{
    x: ['S1', 'S2', 'S3'], y: deltas, type: 'bar',
    marker: { color: deltas.map((v) => (v ?? 0) > 0 ? colB : colA) },
    text: deltas.map((v) => (v == null ? '' : (v > 0 ? '+' : '') + v.toFixed(3))),
    textposition: 'outside',
  }], layout);
}

export function degradation(el: El, session: SessionData): void {
  const deg = session.model?.degradation ?? [];
  const palette: Record<string, string> = { SOFT: '#ff2d55', MEDIUM: '#ffd60a', HARD: '#e6edf3',
                                            INTERMEDIATE: '#30d158', WET: '#0a84ff' };
  const layout = baseLayout('Tyre degradation (s lost per lap of tyre life)');
  layout.yaxis = { ...layout.yaxis, title: { text: 's / lap' } };
  react(el, [{
    x: deg.map((d) => d.compound), y: deg.map((d) => d.slope_s_per_lap), type: 'bar',
    marker: { color: deg.map((d) => palette[d.compound.toUpperCase()] ?? MUTED) },
    text: deg.map((d) => d.slope_s_per_lap.toFixed(3)), textposition: 'outside',
  }], layout);
}
