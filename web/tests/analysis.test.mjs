import test from 'node:test';
import assert from 'node:assert/strict';
import { interpolate, commonGrid, deltaTime } from '../src/analysis.ts';
import { compoundColor, compoundText, FAINT, PANEL } from '../src/theme.ts';

const rows = [
  { Distance: 0, Speed: 100, Throttle: 0, Brake: 0, nGear: 3 },
  { Distance: 10, Speed: 200, Throttle: 100, Brake: 1, nGear: 4 },
];

test('gear stays in the sampled state until the next sample', () => {
  assert.deepEqual(interpolate(rows, 'nGear', [0, 5, 9, 10]), [3, 3, 3, 4]);
});
test('brake remains binary between samples', () => {
  assert.deepEqual(interpolate(rows, 'Brake', [0, 5, 10]), [0, 0, 1]);
});
test('speed retains continuous interpolation', () => {
  assert.deepEqual(interpolate(rows, 'Speed', [0, 5, 10]), [100, 150, 200]);
});
test('interpolation clamps out-of-range positions to recorded values', () => {
  assert.deepEqual(interpolate(rows, 'Speed', [-5, 15]), [100, 200]);
});
test('insufficient telemetry has an actionable error', () => {
  assert.throws(() => commonGrid([], rows), /at least two/i);
});
test('non-overlapping laps cannot produce a misleading delta', () => {
  const other = rows.map(r => ({ ...r, Distance: r.Distance + 20 }));
  assert.throws(() => commonGrid(rows, other), /overlap/i);
});
test('identical laps produce zero delta throughout', () => {
  assert.deepEqual(deltaTime(rows, rows, 3).y, [0, 0, 0]);
});

function luminance(hex) {
  return hex.match(/[a-f\d]{2}/gi).map(v => parseInt(v, 16) / 255)
    .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
    .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
}
function contrast(a, b) {
  const x = luminance(a), y = luminance(b);
  return (Math.max(x, y) + .05) / (Math.min(x, y) + .05);
}
test('small chart labels have AA contrast on their panel', () => {
  assert.ok(contrast(FAINT, PANEL) >= 4.5);
});
for (const compound of ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']) {
  test(`${compound} stint labels have AA contrast`, () => {
    assert.ok(contrast(compoundText(compound), compoundColor(compound)) >= 4.5);
  });
}
