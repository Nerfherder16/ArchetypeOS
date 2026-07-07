import React, { useEffect, useState } from 'react';

// State-based view routing ids (no router dependency, no URL change). The rail
// nav swaps `activeView`; only the active view is mounted in the workspace.
export type ViewId =
  | 'overview'
  | 'repositories'
  | 'architecture'
  | 'council'
  | 'knowledge'
  | 'reuse'
  | 'digest'
  | 'scheduling';

export type NavItem = { id: ViewId; label: string };

type Theme = 'dark' | 'light';

type ShellProps = {
  activeView: ViewId;
  onNav: (viewId: ViewId) => void;
  navItems: NavItem[];
  projectSelector: React.ReactNode;
  health: React.ReactNode;
  children: React.ReactNode;
};

// The ops-deck chrome: left rail (brand + nav + project selector foot), a
// topbar (breadcrumb + theme toggle + health pip), and a workspace that mounts
// the active view. Presentational only — all data/state lives in App().
export function Shell({ activeView, onNav, navItems, projectSelector, health, children }: ShellProps) {
  // The design tokens resolve themes via `:root[data-theme="…"]`; the toggle
  // stamps that attribute. Default the deck to dark (the ops-deck intent).
  const [theme, setTheme] = useState<Theme>('dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const activeLabel = navItems.find((item) => item.id === activeView)?.label ?? '';

  return (
    <div className="aos-surface aos-shell">
      <nav className="aos-rail" aria-label="Primary">
        <div className="aos-rail-brand">
          <span className="aos-rail-mark" aria-hidden="true" />
          <span className="aos-rail-wordmark aos-display">ArchetypeOS</span>
        </div>

        <ul className="aos-nav">
          {navItems.map((item) => {
            const active = item.id === activeView;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  className={active ? 'aos-nav-item active' : 'aos-nav-item'}
                  data-testid={`nav-${item.id}`}
                  aria-current={active ? 'page' : undefined}
                  onClick={() => onNav(item.id)}
                >
                  {item.label}
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
            <span className="aos-crumb-view">{activeLabel}</span>
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

        <main className="aos-workspace">{children}</main>
      </div>
    </div>
  );
}
