import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  createProject,
  fetchHealth,
  fetchKnowledgePages,
  syncKnowledge,
  type Health,
  type KnowledgePage,
} from './api';
import { ReuseView } from './features/reuse/ReuseView';
import { ProvidersView } from './features/providers/ProvidersView';
import { ApprovalsView } from './features/approvals/ApprovalsView';
import { ActivityView } from './features/activity/ActivityView';
import { VoiceInboxView } from './features/voice/VoiceInboxView';
import { NodesView } from './features/nodes/NodesView';
import { ArchitectureView } from './features/architecture/ArchitectureView';
import { DigestView } from './features/digest/DigestView';
import { SchedulingView } from './features/scheduling/SchedulingView';
import { CouncilView } from './features/council/CouncilView';
import { ResearchInboxView } from './features/research/ResearchInboxView';
import { CommandDeck } from './features/command/CommandDeck';
import { Shell, type ViewId } from './shell/Shell';
import { useHashRoute } from './shell/useHashRoute';
import { ProjectProvider, useProjectContext } from './shell/ProjectContext';
import { RepositoryDataProvider } from './shell/RepositoryDataContext';
import { SelectProjectNotice } from './shell/SelectProjectNotice';
import { RepositoriesView } from './features/repositories/RepositoriesView';
import { errorMessage } from './shell/errorMessage';
import { WORKSPACE_MODES } from './shell/workspaces';
import './design/tokens.css';

function App() {
  // AOS-WEB-SPINE-001: the active view is URL-hash routed (deep-linkable, honors
  // browser back/forward). `setActiveView` writes the hash; same call signature.
  const [activeView, setActiveView] = useHashRoute();

  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [knowledgePages, setKnowledgePages] = useState<KnowledgePage[]>([]);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);
  const [knowledgeFilter, setKnowledgeFilter] = useState<'all' | 'open'>('all');
  const [knowledgeSyncing, setKnowledgeSyncing] = useState(false);
  const [knowledgeSyncSummary, setKnowledgeSyncSummary] = useState<string | null>(null);

  // AOS-WEB-SPINE-001 (slice 2): project/repository selection + its two catalogs
  // and self-contained loaders live in ProjectProvider. Destructured here so the
  // project-scoped callbacks below keep their exact call signatures.
  const {
    projects,
    projectsError,
    setProjectsError,
    selectedProjectId,
    setSelectedProjectId,
    repositories,
    setRepositories,
    selectedRepositoryId,
    setSelectedRepositoryId,
    loadProjects,
    loadRepositories,
  } = useProjectContext();
  const [newProjectName, setNewProjectName] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);

  const loadHealth = useCallback(async () => {
    setHealthError(null);
    try {
      setHealth(await fetchHealth());
    } catch (err) {
      setHealth(null);
      setHealthError(errorMessage(err));
    }
  }, []);

  const loadKnowledge = useCallback(async (filter: 'all' | 'open') => {
    setKnowledgeError(null);
    try {
      const params = filter === 'open' ? { validation_state: 'open' } : undefined;
      setKnowledgePages(await fetchKnowledgePages(params));
    } catch (err) {
      setKnowledgePages([]);
      setKnowledgeError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void loadHealth();
    void loadProjects();
  }, [loadHealth, loadProjects]);

  // Knowledge is a GLOBAL surface (lessons have no project); it loads on mount
  // and refetches whenever the All/Open filter changes, never gated on a project.
  useEffect(() => {
    void loadKnowledge(knowledgeFilter);
  }, [loadKnowledge, knowledgeFilter]);

  useEffect(() => {
    setSelectedRepositoryId(null);
    setRepositories([]);
    // dna + architecture are cleared by RepositoryDataProvider's co-load effect
    // when selectedRepositoryId nulls above (slice 3a). Council/artifacts state
    // is owned by CouncilProvider, which loads on project change itself (3f).
    if (selectedProjectId) {
      void loadRepositories(selectedProjectId);
    }
  }, [selectedProjectId, loadRepositories]);

  const handleSyncKnowledge = useCallback(async () => {
    setKnowledgeSyncing(true);
    setKnowledgeError(null);
    try {
      const result = await syncKnowledge();
      setKnowledgeSyncSummary(`synced ${result.synced} · ${result.open_lessons} open`);
      await loadKnowledge(knowledgeFilter);
    } catch (err) {
      setKnowledgeError(errorMessage(err));
    } finally {
      setKnowledgeSyncing(false);
    }
  }, [loadKnowledge, knowledgeFilter]);

  const handleCreateProject = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      const name = newProjectName.trim();
      if (!name) {
        return;
      }
      setCreatingProject(true);
      setProjectsError(null);
      try {
        const created = await createProject(name);
        setNewProjectName('');
        await loadProjects();
        setSelectedProjectId(created.id);
      } catch (err) {
        setProjectsError(errorMessage(err));
      } finally {
        setCreatingProject(false);
      }
    },
    [newProjectName, loadProjects],
  );

  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null;

  // Compact runtime-health pip for the topbar (the full Runtime Health list lives
  // in the Overview view). Derives from the same health/healthError state.
  const healthPip = (
    <span
      className="aos-mono"
      style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontSize: 11, color: 'var(--ink-2)' }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: healthError ? 'var(--red)' : health ? 'var(--signal)' : 'var(--ink-3)',
          boxShadow: healthError ? undefined : 'var(--glow-soft)',
        }}
      />
      {healthError ? 'degraded' : health ? 'operational' : 'checking…'}
    </span>
  );

  // The active-project selector lives in the rail foot and persists across views.
  const projectSelector = (
    <div className="aos-rail-projects">
      <h2 className="aos-eyebrow" style={{ margin: '0 0 8px' }}>
        Projects
      </h2>
      {projectsError ? (
        <p role="alert" style={{ color: 'var(--red)', margin: '0 0 6px', fontSize: 12 }}>
          {projectsError}
        </p>
      ) : null}
      {projects.length === 0 ? (
        <p style={{ margin: '0 0 6px', color: 'var(--ink-3)', fontSize: 12 }}>
          No projects registered yet.
        </p>
      ) : null}
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {projects.map((project) => {
          const selected = project.id === selectedProjectId;
          return (
            <li key={project.id}>
              <button
                type="button"
                className={selected ? 'aos-nav-item active' : 'aos-nav-item'}
                aria-current={selected ? 'true' : undefined}
                onClick={() => setSelectedProjectId(project.id)}
                style={{ fontSize: 12 }}
              >
                {project.name} — {project.status}
              </button>
            </li>
          );
        })}
      </ul>
      <form onSubmit={handleCreateProject} style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
        <input
          className="aos-input"
          type="text"
          value={newProjectName}
          placeholder="New project name"
          onChange={(event) => setNewProjectName(event.target.value)}
          style={{ fontSize: 13, padding: '8px 10px' }}
        />
        <button type="submit" className="aos-btn-ghost" disabled={creatingProject}>
          {creatingProject ? 'Creating...' : 'Create project'}
        </button>
      </form>
    </div>
  );

  // Each view relocates the pre-existing section JSX verbatim, wrapped in a
  // light `.aos-legacy` panel so the un-restyled inline-styled markup stays
  // legible on the dark deck. The Reuse view renders native `.aos-*` bare.
  const renderView = (): React.ReactNode => {
    switch (activeView) {
      case 'command':
        return <CommandDeck projectId={selectedProjectId} projectName={selectedProject?.name ?? null} />;

      case 'overview':
        return (
          <div className="aos-view">
            <div className="aos-view-head">
              <span className="aos-eyebrow">Control Tower</span>
              <h2>Overview</h2>
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Runtime health</span>
              {healthError ? (
                <p role="alert" className="aos-error">
                  Health unavailable: {healthError}
                </p>
              ) : health ? (
                <div className="aos-pills">
                  <span className={`aos-pill ${health.api ? 'good' : 'risk'}`}>API {health.api ? 'ok' : 'down'}</span>
                  <span className={`aos-pill ${health.database ? 'good' : 'risk'}`}>Postgres {health.database ? 'ok' : 'down'}</span>
                  <span className={`aos-pill ${health.redis ? 'good' : 'risk'}`}>Redis {health.redis ? 'ok' : 'down'}</span>
                </div>
              ) : (
                <p className="aos-muted" style={{ margin: 0 }}>Loading health…</p>
              )}
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Active project</span>
              {selectedProject ? (
                <p style={{ margin: 0, color: 'var(--ink-2)' }}>
                  <span className="aos-strong">{selectedProject.name}</span> — {selectedProject.status}.
                  Use the rail to move between Repositories, Council &amp; Decisions, Digest and more.
                </p>
              ) : (
                <p style={{ margin: 0, color: 'var(--ink-2)' }}>
                  No project selected. Create or select one in the rail foot to begin.
                </p>
              )}
              <p className="aos-mono aos-muted" style={{ marginTop: 12, fontSize: 12 }}>
                Voice inbox text capture — planned (v0.1).
              </p>
            </div>
          </div>
        );

      case 'knowledge':
        return (
          <section className="aos-view">
            <div className="aos-view-head">
              <span className="aos-eyebrow">Engineering memory</span>
              <h2>Knowledge</h2>
            </div>
            <div className="aos-hud glass aos-card">
              <span className="aos-eyebrow">Lessons vault</span>
              {knowledgeError ? (
                <p role="alert" className="aos-error">
                  Knowledge unavailable: {knowledgeError}
                </p>
              ) : null}
              <div className="aos-form-row" style={{ marginTop: 0 }}>
                <button
                  type="button"
                  className="aos-btn aos-btn-sm"
                  disabled={knowledgeSyncing}
                  onClick={() => void handleSyncKnowledge()}
                >
                  {knowledgeSyncing ? 'Syncing...' : 'Sync from vault'}
                </button>
                {knowledgeSyncSummary ? (
                  <span className="aos-mono aos-muted">{knowledgeSyncSummary}</span>
                ) : null}
              </div>
              <div className="aos-form-row">
                <button
                  type="button"
                  className={knowledgeFilter === 'all' ? 'aos-mchip on' : 'aos-mchip'}
                  onClick={() => setKnowledgeFilter('all')}
                >
                  All
                </button>
                <button
                  type="button"
                  className={knowledgeFilter === 'open' ? 'aos-mchip on' : 'aos-mchip'}
                  onClick={() => setKnowledgeFilter('open')}
                >
                  Open
                </button>
              </div>
              {knowledgePages.length === 0 ? (
                <p className="aos-muted" style={{ margin: '12px 0 0' }}>
                  No knowledge pages yet. Sync from the vault to load lessons.
                </p>
              ) : (
                <ul className="aos-rows" style={{ marginTop: 12 }}>
                  {knowledgePages.map((page) => {
                    const isOpen = page.validation_state === 'open';
                    return (
                      <li key={page.id}>
                        {isOpen ? <span className="aos-pill risk">open</span> : null}
                        <span className={isOpen ? 'aos-strong' : undefined}>{page.title}</span>{' '}
                        <span className="aos-rowmeta">
                          ({page.page_type} · {page.validation_state})
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </section>
        );

      case 'reuse':
        return <ReuseView projectId={selectedProjectId} />;

      case 'providers':
        return <ProvidersView />;

      case 'approvals':
        return <ApprovalsView />;

      case 'activity':
        return <ActivityView />;

      case 'research':
        return <ResearchInboxView />;

      case 'voice-inbox':
        return <VoiceInboxView />;

      case 'nodes':
        return <NodesView />;

      case 'repositories':
        return <RepositoriesView />;

      case 'architecture':
        return <ArchitectureView />;

      case 'council':
        return <CouncilView />;


      case 'digest':
        return <DigestView />;

      case 'scheduling':
        return <SchedulingView />;

      default:
        return null;
    }
  };

  return (
    <Shell
      activeView={activeView}
      onNav={setActiveView}
      modes={WORKSPACE_MODES}
      projectSelector={projectSelector}
      health={healthPip}
    >
      {renderView()}
    </Shell>
  );
}

createRoot(document.getElementById('root')!).render(
  <ProjectProvider>
    <RepositoryDataProvider>
      <App />
    </RepositoryDataProvider>
  </ProjectProvider>,
);
