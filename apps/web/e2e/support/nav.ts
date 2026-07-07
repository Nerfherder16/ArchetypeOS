import { type Page } from '@playwright/test';

// AOS-UI-003 — the Control Tower is a rail shell with state-based view routing.
// Each section is now a routed view reached by clicking its rail nav button
// (`data-testid="nav-<id>"`). Specs navigate to a view before interacting.
export type ViewId =
  | 'overview'
  | 'repositories'
  | 'architecture'
  | 'council'
  | 'knowledge'
  | 'reuse'
  | 'digest'
  | 'scheduling';

export async function navTo(page: Page, view: ViewId): Promise<void> {
  await page.getByTestId(`nav-${view}`).click();
}
