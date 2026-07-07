import { expect, test } from '@playwright/test';
import * as THREE from 'three';
import { navTo } from './support/nav';
import { candidateToPolar, polarToXZ } from '../src/features/reuse/radarLayout';

// AOS-UI-002 — the WebGL reuse radar over route-mocked candidates.
//
// The live transfer endpoint is route-mocked so results are deterministic (the
// on-disk portfolio may be empty). We assert: (1) the radar container renders
// above the ranked cards when results exist, and (2) the blip→card wiring —
// clicking a blip expands and reveals the matching candidate's card. WebGL is
// available in the Playwright chromium build.
const uid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

const CANDIDATES = [
  {
    source_repository: 'portfolio/llm-router',
    source_project_id: null,
    reusable_asset: 'Provider abstraction with pluggable backends',
    reason: 'Directly matches the described routing need with a proven adapter layer.',
    matched_terms: ['llm', 'provider', 'router'],
    evidence: [{ type: 'distillation', ref: 'vault/llm-router/overview.md' }],
    required_changes: 'Swap the config loader for the local settings module.',
    risks: 'Rate-limit handling differs across backends.',
    confidence: 0.9,
  },
  {
    source_repository: 'portfolio/embeddings-cache',
    source_project_id: null,
    reusable_asset: 'On-disk embedding cache',
    reason: 'Semantic neighbor; useful if routing adds a similarity step.',
    matched_terms: [],
    evidence: [{ type: 'distillation', ref: 'vault/embeddings-cache/overview.md' }],
    required_changes: null,
    risks: null,
    confidence: 0.42,
  },
];

// Reproduce Radar.tsx's camera to project a blip's world position to a screen
// pixel: camera at [0,6.5,6.2], fov 42, aimed at the origin (onCreated lookAt).
function projectBlipToPixel(
  index: number,
  confidence: number,
  total: number,
  box: { x: number; y: number; width: number; height: number },
): { x: number; y: number } {
  const camera = new THREE.PerspectiveCamera(42, box.width / box.height, 0.1, 1000);
  camera.position.set(0, 6.5, 6.2);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);
  camera.updateProjectionMatrix();

  const { radius, angle } = candidateToPolar({ confidence, index, total });
  const { x, z } = polarToXZ(radius, angle);
  const ndc = new THREE.Vector3(x, 0.08, z).project(camera);

  return {
    x: box.x + (ndc.x * 0.5 + 0.5) * box.width,
    y: box.y + (-ndc.y * 0.5 + 0.5) * box.height,
  };
}

test('reuse radar: renders over route-mocked candidates and a blip click expands its card', async ({
  page,
}) => {
  await page.route('**/projects/*/transfer', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(CANDIDATES),
    });
  });

  const projectName = `Reuse Radar ${uid()}`;
  await page.goto('/');
  await expect(page.getByText('Engineering Control Tower')).toBeVisible();

  await page.getByPlaceholder('New project name').fill(projectName);
  await page.getByRole('button', { name: /create project/i }).click();
  await expect(page.getByRole('button', { name: projectName })).toBeVisible();

  await navTo(page, 'reuse');

  const reuseView = page.getByTestId('reuse-view');
  await expect(reuseView).toBeVisible();

  await page.getByTestId('reuse-need-input').fill('an llm provider abstraction');
  await page.getByTestId('reuse-run').click();

  // Both mocked candidates render as cards, and the radar sits above them.
  const rows = page.getByTestId('reuse-result-row');
  await expect(rows).toHaveCount(2);
  const radar = page.getByTestId('reuse-radar');
  await expect(radar).toBeVisible();

  // The radar mounts a real WebGL canvas (graceful-degradation placeholder has
  // no <canvas>). If WebGL were missing this would fail loudly — it is present
  // in the Playwright chromium build.
  const canvas = radar.locator('canvas');
  await expect(canvas).toBeVisible();

  // Card 0 starts collapsed.
  const firstExpand = rows.nth(0).getByTestId('reuse-expand');
  await expect(firstExpand).toHaveAttribute('aria-expanded', 'false');

  // Bring the radar fully into the viewport, then let the first frame settle,
  // so the projected blip pixel is on-screen and the raycaster has a rendered
  // frame to hit.
  await canvas.scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);

  // Project the index-0 (highest-confidence) blip to a screen pixel and click it.
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  if (!box) {
    throw new Error('radar canvas has no bounding box');
  }
  const pixel = projectBlipToPixel(0, CANDIDATES[0].confidence, CANDIDATES.length, box);
  await page.mouse.move(pixel.x, pixel.y);
  await page.mouse.click(pixel.x, pixel.y);

  // Blip→card: the matching card expands and reveals its detail.
  await expect(firstExpand).toHaveAttribute('aria-expanded', 'true');
  await expect(rows.nth(0).getByText('Reason')).toBeVisible();

  // No request error surfaced anywhere in the flow.
  await expect(page.getByTestId('reuse-error')).toHaveCount(0);
});
