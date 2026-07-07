import React, { useEffect, useState } from 'react';
import {
  firstLiveView,
  modeForView,
  type WorkspaceMode,
  type WorkspaceModeId,
} from './workspaces';

// State-based view routing ids (no router dependency, no URL change). The rail
// nav swaps `activeView`; only the active view is mounted in the workspace.
export type ViewId =
  | 'command'
  | 'overview'
  | 'repositories'
  | 'architecture'
  | 'council'
  | 'knowledge'
  | 'reuse'
  | 'digest'
  | 'scheduling';

type Theme = 'dark' | 'light';

type ShellProps = {
  activeView: ViewId;
  onNav: (viewId: ViewId) => void;
  modes: WorkspaceMode[];
  projectSelector: React.ReactNode;
  health: React.ReactNode;
  children: React.ReactNode;
};

// The ops-deck chrome: left rail (brand + mode switcher + active mode's surface
// list + project selector foot), a topbar (breadcrumb + theme toggle + health
// pip), and a workspace that mounts the active view. Presentational only — all
// data/state lives in App(). Shell owns only the active-mode selection, derived
// from the incoming `activeView` (AOS-UI-007).
export function Shell({ activeView, onNav, modes, projectSelector, health, children }: ShellProps) {
  // The design tokens resolve themes via `:root[data-theme="…"]`; the toggle
  // stamps that attribute. Default the deck to dark (the ops-deck intent).
  const [theme, setTheme] = useState<Theme>('dark');

  // Active workspace mode. Initialised from the incoming view, then kept in sync
  // whenever the view changes (a nav click routes the view; the mode follows).
  // Selecting Builder (no live view) leaves `activeView` unchanged, so the effect
  // does not fire and the mode stays on Builder to show the coming-soon state.
  const [activeMode, setActiveMode] = useState<WorkspaceModeId>(() => modeForView(activeView));

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    setActiveMode(modeForView(activeView));
  }, [activeView]);

  const handleSelectMode = (mode: WorkspaceMode) => {
    setActiveMode(mode.id);
    const target = firstLiveView(mode.id);
    if (target) {
      onNav(target);
    }
  };

  const currentMode = modes.find((mode) => mode.id === activeMode) ?? modes[0];
  const liveViewsInMode = currentMode.surfaces
    .filter((surface) => surface.status === 'live')
    .map((surface) => surface.view);
  // The workspace shows the coming-soon empty state when the active mode has no
  // live surface for the current view (deterministic: true exactly for Builder).
  const showEmpty =
    firstLiveView(currentMode.id) === undefined || !liveViewsInMode.includes(activeView);

  const activeSurface = currentMode.surfaces.find(
    (surface) => surface.status === 'live' && surface.view === activeView,
  );
  const activeViewLabel = activeSurface?.label ?? '';

  return (
    <div className="aos-surface aos-shell">
      <nav className="aos-rail" aria-label="Primary">
        <div className="aos-rail-brand">
          <span className="aos-rail-mark" aria-hidden="true" />
          <span className="aos-rail-wordmark aos-display">ArchetypeOS</span>
        </div>

        <div className="aos-modebar" role="group" aria-label="Workspace mode">
          {modes.map((mode) => {
            const active = mode.id === activeMode;
            return (
              <button
                key={mode.id}
                type="button"
                className={active ? 'aos-mode active' : 'aos-mode'}
                data-testid={`mode-${mode.id}`}
                aria-pressed={active}
                title={mode.focus}
                onClick={() => handleSelectMode(mode)}
              >
                {mode.label}
              </button>
            );
          })}
        </div>

        <ul className="aos-nav" aria-label={`${currentMode.label} surfaces`}>
          {currentMode.surfaces.map((surface) => {
            if (surface.status === 'live' && surface.view) {
              const active = surface.view === activeView;
              return (
                <li key={surface.id}>
                  <button
                    type="button"
                    className={active ? 'aos-nav-item active' : 'aos-nav-item'}
                    data-testid={`nav-${surface.view}`}
                    aria-current={active ? 'page' : undefined}
                    onClick={() => surface.view && onNav(surface.view)}
                  >
                    {surface.label}
                  </button>
                </li>
              );
            }
            return (
              <li key={surface.id}>
                <button
                  type="button"
                  className="aos-nav-item aos-nav-disabled"
                  data-testid={`soon-${surface.id}`}
                  disabled
                  aria-disabled="true"
                >
                  <span>{surface.label}</span>
                  <span className="aos-nav-soon">soon</span>
                </button>
              </li>
            );
          })}
        </ul>

        <div className="aos-rail-foot">{projectSelector}</div>
      </nav>

      <div className="aos-main">
        <header className="aos-topbar">
          <div className="aos-topbar-crumb">
            <span className="aos-eyebrow">Engineering Control Tower</span>
            <span className="aos-crumb-sep" aria-hidden="true">
              /
            </span>
            <span className="aos-crumb-mode">{currentMode.label}</span>
            {activeViewLabel ? (
              <>
                <span className="aos-crumb-sep" aria-hidden="true">
                  /
                </span>
                <span className="aos-crumb-view">{activeViewLabel}</span>
              </>
            ) : null}
          </div>
          <div className="aos-topbar-actions">
            {health}
            <button
              type="button"
              className="aos-mchip"
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
              onClick={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
            >
              {theme === 'dark' ? 'Light' : 'Dark'}
            </button>
          </div>
        </header>

        <main className="aos-workspace">
          {showEmpty ? (
            <div className="aos-empty" data-testid="workspace-empty">
              <span className="aos-eyebrow">{currentMode.label}</span>
              <h2 className="aos-display">This workspace is coming soon</h2>
              <p className="aos-muted">{currentMode.focus}</p>
              <ul className="aos-empty-list">
                {currentMode.surfaces.map((surface) => (
                  <li key={surface.id}>{surface.label}</li>
                ))}
              </ul>
            </div>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  );
}
