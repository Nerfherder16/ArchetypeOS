import { expect, test } from '@playwright/test';
import {
  ANGLE_OFFSET,
  MAX_RADIUS,
  MAX_RADIUS_FACTOR,
  MIN_RADIUS_FACTOR,
  candidateToPolar,
  polarToXZ,
} from '../src/features/reuse/radarLayout';

// AOS-UI-002 — unit assertions for the PURE radar mapping.
//
// The repo has no web unit runner (no vitest/jest in apps/web). Per the work
// package, rather than add a new toolchain we fold these pure-TS assertions into
// a Playwright spec that imports the module directly (Playwright transpiles TS
// and runs in node — no browser/DOM needed here).

test('radarLayout: distance grows monotonically as confidence falls (1 − confidence)', () => {
  const total = 6;
  const r = (confidence: number) => candidateToPolar({ confidence, index: 0, total }).radius;

  // High confidence sits nearer the center; low confidence drifts outward.
  expect(r(0.9)).toBeLessThan(r(0.5));
  expect(r(0.5)).toBeLessThan(r(0.1));
  expect(r(1)).toBeLessThan(r(0));

  // Strict monotonic decrease of radius with increasing confidence.
  const radii = [0, 0.2, 0.4, 0.6, 0.8, 1].map((c) => r(c));
  for (let i = 1; i < radii.length; i += 1) {
    expect(radii[i]).toBeLessThan(radii[i - 1]);
  }
});

test('radarLayout: radius band is clamped to [MIN..MAX] * MAX_RADIUS', () => {
  const total = 4;
  const rAt = (confidence: number) => candidateToPolar({ confidence, index: 1, total }).radius;

  // confidence = 1  → innermost band edge; confidence = 0 → outermost.
  expect(rAt(1)).toBeCloseTo(MIN_RADIUS_FACTOR * MAX_RADIUS, 6);
  expect(rAt(0)).toBeCloseTo(MAX_RADIUS_FACTOR * MAX_RADIUS, 6);

  // Out-of-range / non-finite confidence clamps into the same band.
  expect(rAt(5)).toBeCloseTo(MIN_RADIUS_FACTOR * MAX_RADIUS, 6);
  expect(rAt(-3)).toBeCloseTo(MAX_RADIUS_FACTOR * MAX_RADIUS, 6);
  expect(rAt(Number.NaN)).toBeCloseTo(MAX_RADIUS_FACTOR * MAX_RADIUS, 6);

  // Every radius stays within the outer ring.
  for (let c = 0; c <= 1; c += 0.1) {
    expect(rAt(c)).toBeLessThanOrEqual(MAX_RADIUS + 1e-9);
    expect(rAt(c)).toBeGreaterThanOrEqual(MIN_RADIUS_FACTOR * MAX_RADIUS - 1e-9);
  }
});

test('radarLayout: angle is a deterministic even spread by index', () => {
  const total = 4;
  const angle = (index: number) => candidateToPolar({ confidence: 0.5, index, total }).angle;

  // Deterministic: same inputs → identical angle.
  expect(angle(2)).toBe(angle(2));

  // Even spread: consecutive indices differ by exactly 2π / total.
  const step = (Math.PI * 2) / total;
  for (let i = 1; i < total; i += 1) {
    expect(angle(i) - angle(i - 1)).toBeCloseTo(step, 9);
  }

  // First blip carries the constant offset (not on the sweep origin).
  expect(angle(0)).toBeCloseTo(ANGLE_OFFSET, 9);

  // Angle is independent of confidence (layout is stable across strengths).
  expect(candidateToPolar({ confidence: 0.1, index: 3, total }).angle).toBeCloseTo(
    candidateToPolar({ confidence: 0.99, index: 3, total }).angle,
    9,
  );
});

test('radarLayout: total = 0 and total = 1 edges stay finite', () => {
  const zero = candidateToPolar({ confidence: 0.5, index: 0, total: 0 });
  expect(Number.isFinite(zero.radius)).toBe(true);
  expect(Number.isFinite(zero.angle)).toBe(true);
  expect(zero.angle).toBeCloseTo(ANGLE_OFFSET, 9);

  const one = candidateToPolar({ confidence: 0.5, index: 0, total: 1 });
  expect(Number.isFinite(one.radius)).toBe(true);
  expect(one.angle).toBeCloseTo(ANGLE_OFFSET, 9);
});

test('polarToXZ: projects polar onto the XZ plane', () => {
  // angle 0 → +x axis, z ≈ 0.
  const a = polarToXZ(2, 0);
  expect(a.x).toBeCloseTo(2, 9);
  expect(a.z).toBeCloseTo(0, 9);

  // angle π/2 → +z axis, x ≈ 0.
  const b = polarToXZ(2, Math.PI / 2);
  expect(b.x).toBeCloseTo(0, 9);
  expect(b.z).toBeCloseTo(2, 9);

  // radius preserved: x² + z² == radius².
  const c = polarToXZ(3.3, 1.234);
  expect(c.x * c.x + c.z * c.z).toBeCloseTo(3.3 * 3.3, 6);
});
