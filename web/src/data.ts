/** Session data loading and types (matches scripts/export_web_data.py). */

import type { TelemetryRow } from './analysis';

export interface DriverData {
  team: string | null;
  laps: { LapNumber: number; sec: number }[];
  compounds: string[];
  fastest: {
    sec: number | null;
    lap: number | null;
    compound: string | null;
    sectors: { s1: number | null; s2: number | null; s3: number | null };
  };
  telemetry: TelemetryRow[];
  position: { X: number; Y: number; Speed: number }[];
  stints: { Stint: number; Compound: string; Laps: number; StartLap: number; EndLap: number }[];
}

export interface SessionData {
  label: string;
  event: string;
  drivers: Record<string, DriverData>;
  weather: {
    airTemp: number; trackTemp: number; humidity: number; windSpeed: number; rain: boolean;
  } | null;
  model: {
    n_train: number; n_test: number;
    baseline_mae: number; baseline_rmse: number;
    model_mae: number; model_rmse: number;
    improvement_mae_pct: number | null;
    degradation: { compound: string; slope_s_per_lap: number; r_squared: number; n_laps: number }[];
    notes: string[];
  } | null;
}

export interface SessionRef { slug: string; label: string }

const cache = new Map<string, SessionData>();

export async function loadIndex(): Promise<SessionRef[]> {
  const res = await fetch('data/index.json');
  if (!res.ok) throw new Error(`failed to load session index (${res.status})`);
  return res.json();
}

export async function loadSession(slug: string): Promise<SessionData> {
  const hit = cache.get(slug);
  if (hit) return hit;
  const res = await fetch(`data/${slug}.json`);
  if (!res.ok) throw new Error(`failed to load session ${slug} (${res.status})`);
  const data: SessionData = await res.json();
  cache.set(slug, data);
  return data;
}
