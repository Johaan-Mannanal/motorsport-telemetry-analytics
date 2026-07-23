/** Plotly chart renderers for the dashboard. */

import Plotly from 'plotly.js-dist-min';
import type { Annotations, Config, Data, Layout, LayoutAxis, PlotData, PlotMarker } from 'plotly.js';
import { deltaTime, interpolate, commonGrid, type Channel } from './analysis';
import type { DriverData, SessionData } from './data';
import { baseLayout, FAINT, MUTED, PLOT_CONFIG, compoundColor, hexAlpha } from './theme';

type El = string; // element id

function react(el: El, traces: Partial<PlotData>[], layout: Partial<Layout>): void {
  void Plotly.react(el, traces as Data[], layout as Layout, PLOT_CONFIG as Config);
}

/** Direct driver labels at each trace's right end (identity is never legend-only). */
function endLabels(entries: { x: number; y: number; text: string; color: string }[]): Partial<Annotations>[] {
  return entries.map((e) => ({
    x: e.x, y: e.y, xref: 'x' as const, yref: 'y' as const, text: e.text, showarrow: false,
    xanchor: 'left' as const, xshift: 6,
    font: { color: e.color, size: 11, family: "'JetBrains Mono', ui-monospace, monospace" },
  }));
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
  const lastA = a.laps[a.laps.length - 1], lastB = b.laps[b.laps.length - 1];
  layout.annotations = endLabels([
    ...(lastA ? [{ x: lastA.LapNumber, y: lastA.sec, text: nameA, color: colA }] : []),
    ...(lastB ? [{ x: lastB.LapNumber, y: lastB.sec, text: nameB, color: colB }] : []),
  ]);
  react(el, [trace(a, nameA, colA), trace(b, nameB, colB)], layout);
}

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
