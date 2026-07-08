import { type Page } from '@playwright/test';
import { modeForView } from '../../src/shell/workspaces';

// AOS-UI-003 — the Control Tower is a rail shell with state-based view routing.
// AOS-UI-007 — views are now grouped under workspace modes: a view's nav button
// only renders when its mode is the active mode. `navTo` therefore selects the
// owning mode first (revealing that mode's surface list), then clicks the view's
// `data-testid="nav-<id>"` button. The `nav-<id>` contract is unchanged.
export type ViewId =
  | 'command'
  | 'overview'
  | 'repositories'
  | 'architecture'
  | 'council'
  | 'knowledge'
  | 'reuse'
  | 'digest'
  | 'scheduling'
  | 'providers'
  | 'approvals'
  | 'activity'
  | 'research'
  | 'voice-inbox'
  | 'nodes';

export async function navTo(page: Page, view: ViewId): Promise<void> {
  await page.getByTestId(`mode-${modeForView(view)}`).click();
  await page.getByTestId(`nav-${view}`).click();
}
