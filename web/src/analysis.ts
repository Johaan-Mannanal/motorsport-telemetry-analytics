/** Client-side telemetry math (ports src/telemetry_analysis.py). */

export interface TelemetryRow {
  Distance: number;
  Speed: number;
  Throttle: number;
  Brake: number;
  nGear: number;
}

export type Channel = 'Speed' | 'Throttle' | 'Brake' | 'nGear';

/** Interpolate continuous channels; hold brake/gear states between samples. Rows and grid must be sorted. */
export function interpolate(rows: TelemetryRow[], channel: Channel, grid: number[]): number[] {
  if (rows.length < 2) throw new Error('Telemetry needs at least two samples. Choose another driver or session.');
  const xs = rows.map((r) => r.Distance);
  const ys = rows.map((r) => r[channel]);
  const out = new Array<number>(grid.length);
  let j = 0;
  for (let i = 0; i < grid.length; i++) {
    const x = Math.max(xs[0], Math.min(grid[i], xs[xs.length - 1]));
    while (j < xs.length - 2 && xs[j + 1] <= x) j++;
    const x0 = xs[j], x1 = xs[j + 1], y0 = ys[j], y1 = ys[j + 1];
    out[i] = channel === 'Brake' || channel === 'nGear'
      ? (x >= x1 ? y1 : y0)
      : x1 === x0 ? y0 : y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
  }
  return out;
}

/** Shared distance axis spanning the overlap of two laps. */
export function commonGrid(a: TelemetryRow[], b: TelemetryRow[], n = 500): number[] {
  if (a.length < 2 || b.length < 2) throw new Error('Telemetry needs at least two samples. Choose another driver or session.');
  const lo = Math.max(a[0].Distance, b[0].Distance);
  const hi = Math.min(a[a.length - 1].Distance, b[b.length - 1].Distance);
  if (hi <= lo || n < 2) throw new Error('These laps have no usable distance overlap. Choose another comparison.');
  const grid = new Array<number>(n);
  for (let i = 0; i < n; i++) grid[i] = lo + ((hi - lo) * i) / (n - 1);
  return grid;
}

/**
 * Cumulative time gained/lost by lap B relative to lap A along the lap, by integrating the
 * speed difference over distance. Positive means B is slower (behind) at that point.
 */
export function deltaTime(a: TelemetryRow[], b: TelemetryRow[], n = 500): { x: number[]; y: number[] } {
  const grid = commonGrid(a, b, n);
  const va = interpolate(a, 'Speed', grid).map((v) => Math.max(v / 3.6, 1e-3));
  const vb = interpolate(b, 'Speed', grid).map((v) => Math.max(v / 3.6, 1e-3));
  const step = grid[1] - grid[0];
  const y = new Array<number>(n);
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc += step / vb[i] - step / va[i];
    y[i] = acc;
  }
  const y0 = y[0];
  return { x: grid, y: y.map((v) => v - y0) };
}
